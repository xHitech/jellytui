from rich.text import Text
from textual.screen import ModalScreen
from textual.containers import VerticalScroll
from textual.widgets import Static
from ..controls import SHORTCUTS


def help_text():
    text = Text()
    previous_group = None
    for shortcut in SHORTCUTS:
        if shortcut.group != previous_group:
            if previous_group:
                text.append("\n")
            text.append(shortcut.group + "\n", style="bold cyan")
            previous_group = shortcut.group
        text.append(f"{shortcut.label:15} {shortcut.description}\n")
    text.append("\nh ou Escape fecha · ↑/↓ ou PageUp/PageDown rola a ajuda", style="dim")
    return text


class HelpScreen(ModalScreen):
    DEFAULT_CSS = """
    HelpScreen { align: center middle; background: #000000 65%; }
    #help-scroll { width: 76; max-width: 95%; height: 90%; border: solid #75848d;
                   background: #181c20; padding: 1 2; }
    #help-content { height: auto; }
    """

    def compose(self):
        with VerticalScroll(id="help-scroll"):
            yield Static(help_text(), id="help-content")

    def on_mount(self):
        scroll = self.query_one(VerticalScroll)
        scroll.border_title = "JELLYTUI · AJUDA"
        scroll.focus()
