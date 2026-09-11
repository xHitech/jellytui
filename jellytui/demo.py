from .models import Item


class DemoLibrary:
    """Biblioteca offline explícita; nunca usada como fallback para erros reais."""
    async def browse(self, item):
        if item == "Artistas":
            return [Item("artist", "Spiritbox", "MusicArtist")]
        if item in ("Álbuns", "Pastas", "Playlists") or isinstance(item, Item) and item.kind == "MusicArtist":
            return [Item("album", "Eternal Blue", "MusicAlbum", "Spiritbox")]
        return [Item(str(n), title, "Audio", "Spiritbox", "Eternal Blue", 240 + n)
                for n, title in enumerate(["Sun Killer", "Hurt You", "Yellowjacket"])]

    async def search(self, term):
        return [i for i in await self.browse("Favoritos") if term.casefold() in i.name.casefold()]

    async def favorite(self, item):
        item.favorite = not item.favorite

    async def lyrics(self, item):
        from .lyrics import Lyrics
        return Lyrics()

    async def close(self):
        pass
