from rich.cells import cell_len
from rich.text import Text
from textual.widgets import DataTable
from ..controls import bindings_for
from ..models import time_label
from ..i18n import t

KIND_LABELS = {"Category": "Open", "MusicArtist": "Artist", "MusicAlbum": "Album",
               "Folder": "Folder", "Playlist": "Playlist"}


def column_widths(labels, rows, available, padding=1):
    """Larguras em células do terminal, sem distribuir sobra entre colunas.

    `labels` são ids de coluna em inglês; o cabeçalho exibido é t(label)."""
    limits = {"": (1, 1), "Name": (20, 72), "Artist": (14, 40), "Type": (13, 40),
              "Artist / type": (13, 40), "Album": (5, 40), "Time": (6, 6)}
    widths = []
    for index, label in enumerate(labels):
        header = cell_len(t(label)) if label else 0
        minimum, maximum = limits.get(label, (header, 40))
        content = max((max((cell_len(line) for line in row[index].plain.splitlines()), default=0)
                       for row in rows), default=0)
        widths.append(min(maximum, max(minimum, header, content)))
    budget = max(len(labels), available - 2 * padding * len(labels))
    # Primeiro comprime metadados; título e duração curta têm espaço reservado.
    for floors in ({"Name": 20, "Artist": 13, "Type": 13, "Artist / type": 13, "Album": 10, "Time": 6},
                   {"Name": 8, "Artist": 1, "Type": 1, "Artist / type": 1, "Album": 1, "Time": 5}, {}):
        for label in ("Album", "Artist", "Type", "Artist / type", "Name", "Time", *labels):
            if label not in labels:
                continue
            index = labels.index(label)
            reduction = min(max(0, sum(widths) - budget), max(0, widths[index] - floors.get(label, 1)))
            widths[index] -= reduction
    return widths


class TrackList(DataTable, inherit_bindings=False):
    BINDINGS = bindings_for("table")
    COLUMN_LABELS = ("", "Name", "Artist", "Album", "Time")

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
        if ctx == t("Artists"):
            return ("Name", "Type")
        if ctx == t("Albums"):
            return ("Name", "Artist")
        if items is not None and len(items) > 0:
            if any(getattr(i, "is_track", False) for i in items):
                return ("", "Name", "Artist", "Album", "Time")
            if any(getattr(i, "kind", "") == "MusicAlbum" for i in items):
                return ("Name", "Artist")
            if any(getattr(i, "kind", "") in ("MusicArtist", "Category", "Folder", "Playlist") for i in items):
                return ("Name", "Type")
        return ("", "Name", "Artist", "Album", "Time")

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
            kind = t(KIND_LABELS.get(item.kind, item.kind))
            cells = {
                "": "▶" if item.id == playing_id else "",
                "Name": ("♥ " if item.favorite else "") + item.name,
                "Artist": item.artist or "—",
                "Type": kind,
                "Artist / type": item.artist or kind,
                "Album": item.album or "—",
                "Time": time_label(item.duration) if item.is_track else "",
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
            self.add_column(Text(t(label) if label else "", no_wrap=True, overflow="ellipsis"), width=width)
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
