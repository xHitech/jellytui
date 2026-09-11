"""Entradas da navegação principal; não existe mais widget lateral."""
from ..models import Item

CATEGORIES = ["Artistas", "Álbuns", "Pastas", "Playlists", "Favoritos"]


def library_entries():
    return [Item(category, category, "Category") for category in CATEGORIES]
