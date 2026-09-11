"""API Jellyfin; rotas conferidas na especificação OpenAPI oficial."""
from dataclasses import dataclass, field
from urllib.parse import urlencode, urlsplit, urljoin, parse_qs
import httpx
from .config import Config
from .models import Item
from .lyrics import Lyrics


class JellyfinError(Exception):
    """Mensagem segura, sem URL de streaming nem resposta de autenticação."""


@dataclass
class Stream:
    url: str = field(repr=False)
    headers: dict = field(repr=False)
    quality: str = ""
    mode: str = "Direct Play · original"


class Jellyfin:
    def __init__(self, config: Config, transport=None):
        self.config = config
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(20, connect=8),
                                      transport=transport, trust_env=False)

    @property
    def authorization(self):
        value = ('MediaBrowser Client="jellytui", Device="Linux terminal", '
                 f'DeviceId="{self.config.device_id}", Version="0.1.0"')
        if self.config.token:
            value += f', Token="{self.config.token}"'
        return value

    async def request(self, method, path, *, missing_ok=False, **kwargs):
        try:
            response = await self.http.request(method, self.config.server + path,
                                               headers={"Authorization": self.authorization}, **kwargs)
            if missing_ok and response.status_code == 404:
                return {}
            if response.status_code in (401, 403):
                raise JellyfinError("Acesso negado. Verifique usuário/permissões ou execute jellytui --setup.")
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.TimeoutException:
            raise JellyfinError("Jellyfin demorou a responder. Verifique a conexão Tailscale e tente novamente.") from None
        except httpx.HTTPStatusError as error:
            raise JellyfinError(f"Jellyfin retornou HTTP {error.response.status_code}.") from None
        except httpx.HTTPError:
            raise JellyfinError("Não foi possível conectar ao Jellyfin. Verifique servidor e Tailscale.") from None
        except ValueError:
            raise JellyfinError("O servidor retornou uma resposta inválida.") from None

    async def authenticate(self, username, password):
        data = await self.request("POST", "/Users/AuthenticateByName", json={"Username": username, "Pw": password})
        try:
            self.config.user_id = data["User"]["Id"]
            self.config.token = data["AccessToken"]
        except KeyError:
            raise JellyfinError("Resposta de autenticação incompleta.") from None
        return self.config

    async def all_items(self, path="/Items", **params):
        params = {"userId": self.config.user_id, "enableImages": "false", "enableUserData": "true",
                  "fields": "MediaSources,MediaStreams", **params}
        result = []
        start = 0
        while True:
            data = await self.request("GET", path, params={**params, "startIndex": start, "limit": 200})
            page = data.get("Items", [])
            result.extend(Item.from_api(item) for item in page)
            start += len(page)
            if not page or start >= data.get("TotalRecordCount", start + (len(page) == 200)):
                break
        return result

    async def browse(self, context):
        if context == "Artistas":
            return await self.all_items("/Artists", sortBy="SortName")
        if context == "Álbuns":
            return await self.all_items(includeItemTypes="MusicAlbum", recursive="true", sortBy="SortName")
        if context == "Playlists":
            items = await self.all_items(includeItemTypes="Playlist", recursive="true", sortBy="SortName")
            return [i for i in items if i.raw.get("MediaType") == "Audio"]
        if context == "Favoritos":
            return await self.all_items(includeItemTypes="Audio,MusicAlbum,MusicArtist", recursive="true",
                                        filters="IsFavorite", sortBy="SortName")
        if context == "Pastas":
            data = await self.request("GET", "/UserViews", params={"userId": self.config.user_id})
            return [Item.from_api(i) for i in data.get("Items", []) if i.get("CollectionType") == "music"]
        if context.kind == "MusicArtist":
            return await self.all_items(includeItemTypes="MusicAlbum,Audio", artistIds=context.id,
                                        recursive="true", sortBy="Album,ParentIndexNumber,IndexNumber,SortName")
        if context.kind == "Playlist":
            return [i for i in await self.all_items(f"/Playlists/{context.id}/Items") if i.is_track]
        return await self.all_items(parentId=context.id, recursive="false",
                                    includeItemTypes="Audio,MusicAlbum,Folder,MusicArtist",
                                    sortBy="ParentIndexNumber,IndexNumber,SortName")

    async def search(self, term):
        if not term.strip():
            return []
        return await self.all_items(includeItemTypes="Audio,MusicAlbum,MusicArtist", recursive="true",
                                    searchTerm=term.strip(), sortBy="SortName")

    async def favorite(self, item):
        await self.request("DELETE" if item.favorite else "POST", f"/UserFavoriteItems/{item.id}",
                           params={"userId": self.config.user_id})
        item.favorite = not item.favorite

    async def lyrics(self, item):
        data = await self.request("GET", f"/Audio/{item.id}/Lyrics", missing_ok=True)
        return Lyrics.from_jellyfin(data)

    async def stream(self, item):
        info = await self.request("POST", f"/Items/{item.id}/PlaybackInfo", json={
            "UserId": self.config.user_id, "EnableDirectPlay": True, "EnableDirectStream": True,
            "EnableTranscoding": False, "DeviceProfile": {
                "Name": "jellytui mpv", "MaxStreamingBitrate": 2147483647,
                "DirectPlayProfiles": [{"Type": "Audio", "Container": ""}],
                "TranscodingProfiles": [], "CodecProfiles": [], "ContainerProfiles": [],
            }})
        sources = info.get("MediaSources", [])
        source = next((s for s in sources if s.get("SupportsDirectPlay")), None)
        if not source:
            raise JellyfinError("Jellyfin não disponibilizou Direct Play. Transcodificação está desativada para preservar o áudio.")
        # DirectStreamUrl é opcional no contrato: static=true serve os bytes originais.
        provided = source.get("DirectStreamUrl")
        # Uma URL de remux/transcode não deve ser rotulada como original.
        if provided and parse_qs(urlsplit(provided).query).get("static", [""])[0].lower() != "true":
            provided = None
        url = urljoin(self.config.server + "/", provided) if provided else (
            self.config.server + f"/Audio/{item.id}/stream?" + urlencode({
                "static": "true", "mediaSourceId": source["Id"], "deviceId": self.config.device_id,
                "playSessionId": info.get("PlaySessionId", ""),
            }))
        target, server = urlsplit(url), urlsplit(self.config.server)
        if (target.scheme, target.netloc) != (server.scheme, server.netloc):
            raise JellyfinError("O servidor forneceu um stream em outra origem; credenciais não foram enviadas.")
        audio = next((s for s in source.get("MediaStreams", []) if s.get("Type") == "Audio"), {})
        parts = [str(audio.get("Codec", "")).upper()]
        if audio.get("BitDepth"):
            parts.append(f"{audio['BitDepth']}-bit")
        if audio.get("SampleRate"):
            parts.append(f"{audio['SampleRate'] / 1000:g} kHz")
        if audio.get("Channels"):
            parts.append({1: "Mono", 2: "Stereo"}.get(audio["Channels"], f"{audio['Channels']} canais"))
        return Stream(url, {"Authorization": self.authorization}, " • ".join(p for p in parts if p))

    async def close(self):
        await self.http.aclose()
