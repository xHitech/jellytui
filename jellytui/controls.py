"""Fonte única dos atalhos da aplicação/tabela, rodapé e ajuda."""
from dataclasses import dataclass
from textual.binding import Binding


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


SHORTCUTS = (
    Shortcut("NAVEGAÇÃO", "up,k", "↑ / k", "cursor_up", "Subir", "table"),
    Shortcut("NAVEGAÇÃO", "down,j", "↓ / j", "cursor_down", "Descer", "table"),
    Shortcut("NAVEGAÇÃO", "enter", "Enter", "select_cursor", "Abrir / tocar a partir da seleção", "table"),
    Shortcut("NAVEGAÇÃO", "backspace", "Backspace", "back", "Voltar um nível"),
    Shortcut("NAVEGAÇÃO", "pageup", "PageUp", "page_up", "Página anterior", "table"),
    Shortcut("NAVEGAÇÃO", "pagedown", "PageDown", "page_down", "Próxima página", "table"),
    Shortcut("NAVEGAÇÃO", "home", "Home", "first_row", "Primeiro item", "table"),
    Shortcut("NAVEGAÇÃO", "end", "End", "last_row", "Último item", "table"),
    Shortcut("NAVEGAÇÃO", "tab", "Tab", "focus_next", "Próximo foco"),
    Shortcut("NAVEGAÇÃO", "shift+tab", "Shift+Tab", "focus_previous", "Foco anterior"),
    Shortcut("NAVEGAÇÃO", "slash", "/", "search", "Buscar", footer=True),
    Shortcut("REPRODUÇÃO", "space", "Space", "pause", "Play/Pause", footer=True, priority=True),
    Shortcut("REPRODUÇÃO", "n", "n", "next_track", "Próxima", footer=True),
    Shortcut("REPRODUÇÃO", "p", "p", "previous_track", "Anterior", footer=True),
    Shortcut("REPRODUÇÃO", "left", "←", "seek(-5)", "Voltar 5 segundos", priority=True),
    Shortcut("REPRODUÇÃO", "right", "→", "seek(5)", "Avançar 5 segundos", priority=True),
    Shortcut("REPRODUÇÃO", "plus,equal,equals_sign,add", "+ / Numpad +", "volume(5)", "Aumentar volume"),
    Shortcut("REPRODUÇÃO", "minus,subtract", "- / Numpad -", "volume(-5)", "Diminuir volume"),
    Shortcut("BIBLIOTECA", "f", "f", "favorite", "Adicionar / remover favorito"),
    Shortcut("BIBLIOTECA", "Q", "Q", "show_queue", "Mostrar fila local"),
    Shortcut("EXIBIÇÃO", "l", "l", "toggle_lyrics", "Letra", footer=True),
    Shortcut("EXIBIÇÃO", "h", "h", "help", "Ajuda", footer=True, priority=True),
    Shortcut("EXIBIÇÃO", "escape", "Escape", "close_overlay", "Fechar ajuda / busca", priority=True),
    Shortcut("GERAL", "q", "q", "quit", "Sair", footer=True),
)


def bindings_for(target):
    shortcuts = [shortcut for shortcut in SHORTCUTS if shortcut.target == target]
    footer_order = ["pause", "next_track", "previous_track", "search", "toggle_lyrics", "help", "quit"]
    if target == "app":
        shortcuts = [s for s in shortcuts if not s.footer] + sorted(
            [s for s in shortcuts if s.footer], key=lambda s: footer_order.index(s.action))
    return [shortcut.binding() for shortcut in shortcuts]
