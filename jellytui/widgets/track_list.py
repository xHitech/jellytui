from rich.cells import cell_len
from rich.text import Text
from textual.widgets import DataTable
from ..controls import bindings_for
from ..models import time_label


def column_widths(labels, rows, available, padding=1):
    """Larguras em células do terminal, sem distribuir sobra entre colunas."""
    limits = {"": (1, 1), "Nome": (20, 72), "Artista": (14, 40), "Tipo": (13, 40),
              "Artista / tipo": (13, 40), "Álbum": (5, 40), "Tempo": (6, 6)}
    widths = []
    for index, label in enumerate(labels):
        minimum, maximum = limits.get(label, (cell_len(label), 40))
        content = max((max((cell_len(line) for line in row[index].plain.splitlines()), default=0)
                       for row in rows), default=0)
        widths.append(min(maximum, max(minimum, cell_len(label), content)))
    budget = max(len(labels), available - 2 * padding * len(labels))
    # Primeiro comprime metadados; título e duração curta têm espaço reservado.
    for floors in ({"Nome": 20, "Artista": 13, "Tipo": 13, "Artista / tipo": 13, "Álbum": 10, "Tempo": 6},
                   {"Nome": 8, "Artista": 1, "Tipo": 1, "Artista / tipo": 1, "Álbum": 1, "Tempo": 5}, {}):
        for label in ("Álbum", "Artista", "Tipo", "Artista / tipo", "Nome", "Tempo", *labels):
            if label not in labels:
                continue
            index = labels.index(label)
            reduction = min(max(0, sum(widths) - budget), max(0, widths[index] - floors.get(label, 1)))
            widths[index] -= reduction
    return widths


class TrackList(DataTable, inherit_bindings=False):
    BINDINGS = bindings_for("table")
    COLUMN_LABELS = ("", "Nome", "Artista", "Álbum", "Tempo")

    def __init__(self):
        super().__init__(id="tracks", cursor_type="row", zebra_stripes=False)
        self.items = []
        self.playing_id = None
        self._display_rows = []
        self._layout_widths = None
        self._active_labels = self.COLUMN_LABELS

    @classmethod
    def resolve_columns(cls, context=None, items=None):
        ctx = str(context) if context is not None else ""
        if ctx == "Artistas":
            return ("Nome", "Tipo")
        if ctx == "Álbuns":
            return ("Nome", "Artista")
        if items is not None and len(items) > 0:
            if any(getattr(i, "is_track", False) for i in items):
                return ("", "Nome", "Artista", "Álbum", "Tempo")
            if any(getattr(i, "kind", "") == "MusicAlbum" for i in items):
                return ("Nome", "Artista")
            if any(getattr(i, "kind", "") in ("MusicArtist", "Category", "Folder", "Playlist") for i in items):
                return ("Nome", "Tipo")
        if ctx == "Artistas":
            return ("Nome", "Tipo")
        if ctx == "Álbuns":
            return ("Nome", "Artista")
        return ("", "Nome", "Artista", "Álbum", "Tempo")

    def on_mount(self):
        self._fit_columns()

    def show_items(self, items, playing_id=None, context=None):
        self.items = list(items)
        self.playing_id = playing_id
        if self.COLUMN_LABELS != TrackList.COLUMN_LABELS:
            self._active_labels = self.COLUMN_LABELS
        else:
            self._active_labels = self.resolve_columns(context, self.items)

        self._display_rows = []
        for item in self.items:
            cells = {
                "": "▶" if item.id == playing_id else "",
                "Nome": ("♥ " if item.favorite else "") + item.name,
                "Artista": item.artist or "—",
                "Tipo": {"Category": "Abrir", "MusicArtist": "Artista", "MusicAlbum": "Álbum",
                         "Folder": "Pasta", "Playlist": "Playlist"}.get(item.kind, item.kind),
                "Artista / tipo": item.artist or {"Category": "Abrir", "MusicArtist": "Artista",
                                                  "MusicAlbum": "Álbum", "Folder": "Pasta"}.get(item.kind, item.kind),
                "Álbum": item.album or "—",
                "Tempo": time_label(item.duration) if item.is_track else "",
            }
            self._display_rows.append(tuple(
                Text(cells.get(label, ""), no_wrap=True, overflow="ellipsis")
                for label in self._active_labels
            ))
        self._fit_columns(force=True)

    def on_resize(self):
        self._fit_columns()

    def _fit_columns(self, force=False):
        # Reservar a scrollbar evita uma segunda mudança de largura ao ela aparecer.
        available = max(1, self.size.width - self.styles.scrollbar_size_vertical)
        labels = self._active_labels
        widths = column_widths(labels, self._display_rows, available, self.cell_padding)
        if not force and widths == self._layout_widths:
            return
        row, scroll_y = self.cursor_row, self.scroll_y
        self._layout_widths = widths
        # A API pública não oferece set_column_width: recria somente as células,
        # preservando os Items, a seleção e a posição vertical.
        self.clear(columns=True)
        for label, width in zip(labels, widths):
            self.add_column(Text(label, no_wrap=True, overflow="ellipsis"), width=width)
        for index, values in enumerate(self._display_rows):
            self.add_row(*values, key=str(index))
        if self.items:
            self.move_cursor(row=min(row, len(self.items) - 1))
        self.scroll_to(x=0, y=scroll_y, animate=False)

    @property
    def selected(self):
        return self.items[self.cursor_row] if self.items else None

    def action_first_row(self):
        self.move_cursor(row=0)

    def action_last_row(self):
        if self.items:
            self.move_cursor(row=len(self.items) - 1)
