from rich.text import Text
from textual.widgets import Static
from ..models import time_label
from ..i18n import t


class NowPlaying(Static):
    def __init__(self):
        super().__init__(id="now-playing", markup=False)
        self.border_title = t("NOW PLAYING")

    def show(self, item=None, position=0, duration=0, paused=True, volume=70, quality="", mode=""):
        if item is None:
            self.update(t("No track selected\n\nEnter opens an item or plays a track."))
            return
        duration = duration or item.duration
        width = max(10, min(50, self.size.width - 20))
        done = int(width * min(1, max(0, position / duration))) if duration else 0
        self.update(Text(f"{item.artist} — {item.name}\n{item.album}\n"
                    f"{time_label(position)} {'━' * done}{'─' * (width - done)} {time_label(duration)}\n"
                    f"{t('Ⅱ Paused') if paused else t('▶ Playing')}  ·  Volume {volume:.0f}%\n{mode}\n{quality}", no_wrap=True, overflow="ellipsis"))
