"""Fonte única dos atalhos da aplicação/tabela, rodapé e ajuda."""
from dataclasses import dataclass
from textual.binding import Binding
from .i18n import t


@dataclass(frozen=True)
class Shortcut:
    group: str
    key: str
    label: str
    action: str
    description: str
    target: str = "app"
    footer: bool = False
    priority: bool = False

    def binding(self):
        return Binding(self.key, self.action, self.description, show=self.footer,
                       key_display=self.label, priority=self.priority)


NAVIGATION, PLAYBACK, LIBRARY, DISPLAY, GENERAL = (
    t("NAVIGATION"), t("PLAYBACK"), t("LIBRARY"), t("DISPLAY"), t("GENERAL"))

SHORTCUTS = (
    Shortcut(NAVIGATION, "up,k", "↑ / k", "cursor_up", t("Up"), "table"),
    Shortcut(NAVIGATION, "down,j", "↓ / j", "cursor_down", t("Down"), "table"),
    Shortcut(NAVIGATION, "enter", "Enter", "select_cursor", t("Open / play from selection"), "table"),
    Shortcut(NAVIGATION, "backspace", "Backspace", "back", t("Go back one level")),
    Shortcut(NAVIGATION, "pageup", "PageUp", "page_up", t("Previous page"), "table"),
    Shortcut(NAVIGATION, "pagedown", "PageDown", "page_down", t("Next page"), "table"),
    Shortcut(NAVIGATION, "home", "Home", "first_row", t("First item"), "table"),
    Shortcut(NAVIGATION, "end", "End", "last_row", t("Last item"), "table"),
    Shortcut(NAVIGATION, "tab", "Tab", "focus_next", t("Next focus")),
    Shortcut(NAVIGATION, "shift+tab", "Shift+Tab", "focus_previous", t("Previous focus")),
    Shortcut(NAVIGATION, "slash", "/", "search", t("Search"), footer=True),
    Shortcut(PLAYBACK, "space", "Space", "pause", "Play/Pause", footer=True, priority=True),
    Shortcut(PLAYBACK, "n", "n", "next_track", t("Next"), footer=True),
    Shortcut(PLAYBACK, "p", "p", "previous_track", t("Previous"), footer=True),
    Shortcut(PLAYBACK, "left", "←", "seek(-5)", t("Back 5 seconds"), priority=True),
    Shortcut(PLAYBACK, "right", "→", "seek(5)", t("Forward 5 seconds"), priority=True),
    Shortcut(PLAYBACK, "plus,equal,equals_sign,add", "+ / Numpad +", "volume(5)", t("Volume up")),
    Shortcut(PLAYBACK, "minus,subtract", "- / Numpad -", "volume(-5)", t("Volume down")),
    Shortcut(LIBRARY, "f", "f", "favorite", t("Add / remove favorite")),
    Shortcut(LIBRARY, "Q", "Q", "show_queue", t("Show local queue")),
    Shortcut(DISPLAY, "l", "l", "toggle_lyrics", t("Lyrics"), footer=True),
    Shortcut(DISPLAY, "h", "h", "help", t("Help"), footer=True, priority=True),
    Shortcut(DISPLAY, "escape", "Escape", "close_overlay", t("Close help / search"), priority=True),
    Shortcut(GENERAL, "q", "q", "quit", t("Quit"), footer=True),
)


def bindings_for(target):
    shortcuts = [shortcut for shortcut in SHORTCUTS if shortcut.target == target]
    footer_order = ["pause", "next_track", "previous_track", "search", "toggle_lyrics", "help", "quit"]
    if target == "app":
        shortcuts = [s for s in shortcuts if not s.footer] + sorted(
            [s for s in shortcuts if s.footer], key=lambda s: footer_order.index(s.action))
    return [shortcut.binding() for shortcut in shortcuts]
