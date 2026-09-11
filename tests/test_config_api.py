import stat
import httpx
import pytest
from jellytui.config import Config, ConfigError
from jellytui.jellyfin import Jellyfin, JellyfinError


def test_private_config(tmp_path):
    path = tmp_path / "config.toml"
    config = Config("http://localhost:8096", "user", "secret")
    config.save(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert Config.load(path) == config
    assert "secret" not in repr(config)
    assert "password" not in path.read_text()
    path.chmod(0o644)
    with pytest.raises(ConfigError):
        Config.load(path)


async def test_authentication_and_safe_error():
    def handler(request):
        assert request.url.path == "/Users/AuthenticateByName"
        return httpx.Response(200, json={"User": {"Id": "u"}, "AccessToken": "token"})
    api = Jellyfin(Config("http://localhost", "", ""), httpx.MockTransport(handler))
    assert (await api.authenticate("name", "password")).token == "token"
    await api.close()
    api = Jellyfin(Config("http://localhost", "", ""), httpx.MockTransport(lambda r: httpx.Response(401, text="secret")))
    with pytest.raises(JellyfinError, match="Acesso negado") as exc:
        await api.authenticate("name", "secret")
    assert "secret" not in str(exc.value)
    await api.close()


async def test_library_pagination_and_playlist_order():
    from jellytui.models import Item
    calls = []
    def handler(request):
        calls.append(request)
        start = int(request.url.params.get("startIndex", 0))
        if start == 0:
            return httpx.Response(200, json={"Items": [{"Id": str(i), "Name": str(i), "Type": "Audio"} for i in range(200)], "TotalRecordCount": 201})
        return httpx.Response(200, json={"Items": [{"Id": "last", "Name": "last", "Type": "Audio"}], "TotalRecordCount": 201})
    api = Jellyfin(Config("http://localhost", "u", "secret"), httpx.MockTransport(handler))
    items = await api.browse(Item("pl", "Playlist", "Playlist"))
    assert len(items) == 201 and items[-1].id == "last"
    assert calls[0].url.path == "/Playlists/pl/Items"
    assert "sortBy" not in calls[0].url.params
    await api.close()


async def test_stream_preserves_original_and_favorite():
    import json
    from jellytui.models import Item
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("PlaybackInfo"):
            assert json.loads(request.content)["EnableTranscoding"] is False
            return httpx.Response(200, json={"MediaSources": [{"Id": "s", "SupportsDirectPlay": True,
                "MediaStreams": [{"Type": "Audio", "Codec": "flac", "BitDepth": 24, "SampleRate": 96000, "Channels": 2}]}]})
        return httpx.Response(204)
    api = Jellyfin(Config("http://localhost/jellyfin", "u", "secret"), httpx.MockTransport(handler))
    item = Item("a", "Track", "Audio")
    stream = await api.stream(item)
    assert "static=true" in stream.url and "secret" not in stream.url
    assert "FLAC • 24-bit • 96 kHz • Stereo" == stream.quality
    await api.favorite(item)
    assert item.favorite and calls[-1].method == "POST"
    await api.favorite(item)
    assert not item.favorite and calls[-1].method == "DELETE"
    await api.close()


async def test_no_direct_play_has_clear_error():
    from jellytui.models import Item
    api = Jellyfin(Config("http://localhost", "u", "secret"), httpx.MockTransport(
        lambda r: httpx.Response(200, json={"MediaSources": [{"Id": "a", "SupportsDirectPlay": False}]})))
    with pytest.raises(JellyfinError, match="Transcodificação está desativada"):
        await api.stream(Item("a", "A", "Audio"))
    await api.close()


async def test_music_only_folders_and_playlists():
    def handler(request):
        if request.url.path == "/UserViews":
            items = [{"Id": "music", "Name": "Music", "CollectionType": "music"},
                     {"Id": "movies", "Name": "Movies", "CollectionType": "movies"}]
        else:
            items = [{"Id": "audio", "Name": "Audio", "Type": "Playlist", "MediaType": "Audio"},
                     {"Id": "video", "Name": "Video", "Type": "Playlist", "MediaType": "Video"}]
        return httpx.Response(200, json={"Items": items, "TotalRecordCount": len(items)})
    api = Jellyfin(Config("http://localhost", "u", "secret"), httpx.MockTransport(handler))
    assert [i.id for i in await api.browse("Pastas")] == ["music"]
    assert [i.id for i in await api.browse("Playlists")] == ["audio"]
    await api.close()


async def test_lyrics_official_dto_and_404_without_writes():
    from jellytui.models import Item
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        if request.url.path == "/Audio/has/Lyrics":
            return httpx.Response(200, json={"Metadata": {}, "Lyrics": [{"Start": 123400000, "Text": "Test"}]})
        return httpx.Response(404)
    api = Jellyfin(Config("http://localhost", "u", "secret"), httpx.MockTransport(handler))
    assert (await api.lyrics(Item("has", "A", "Audio"))).starts == [12.34]
    assert not (await api.lyrics(Item("missing", "B", "Audio"))).lines
    with pytest.raises(JellyfinError, match="404"):
        await api.request("GET", "/Items/missing")
    await api.close()
