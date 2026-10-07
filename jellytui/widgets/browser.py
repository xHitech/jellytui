"""Entradas da navegação principal; não existe mais widget lateral."""
from ..i18n import t
from ..models import Item

# Stable ids passed to library.browse(); only the displayed name is translated.
CATEGORIES = ["Artists", "Albums", "Folders", "Playlists", "Favorites"]


def library_entries():
    return [Item(category, t(category), "Category") for category in CATEGORIES]
