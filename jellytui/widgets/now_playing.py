from rich.text import Text
from textual.widgets import Static
from ..models import time_label


class NowPlaying(Static):
    def __init__(self):
        super().__init__(id="now-playing", markup=False)
        self.border_title = "TOCANDO AGORA"

    def show(self, item=None, position=0, duration=0, paused=True, volume=70, quality="", mode=""):
        if item is None:
            self.update("Nenhuma música selecionada\n\nEnter abre um item ou reproduz uma faixa.")
            return
        duration = duration or item.duration
        width = max(10, min(50, self.size.width - 20))
        done = int(width * min(1, max(0, position / duration))) if duration else 0
        self.update(Text(f"{item.artist} — {item.name}\n{item.album}\n"
                    f"{time_label(position)} {'━' * done}{'─' * (width - done)} {time_label(duration)}\n"
                    f"{'Ⅱ Pausado' if paused else '▶ Tocando'}  ·  Volume {volume:.0f}%\n{mode}\n{quality}", no_wrap=True, overflow="ellipsis"))
