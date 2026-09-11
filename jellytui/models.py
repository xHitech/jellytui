from dataclasses import dataclass, field


@dataclass
class Item:
    id: str
    name: str
    kind: str
    artist: str = ""
    album: str = ""
    duration: float = 0
    favorite: bool = False
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "Item":
        return cls(
            data["Id"], data.get("Name", "Sem título"), data.get("Type", "Folder"),
            ", ".join(data.get("Artists") or []) or data.get("AlbumArtist", ""),
            data.get("Album", ""), (data.get("RunTimeTicks") or 0) / 10_000_000,
            data.get("UserData", {}).get("IsFavorite", False), data,
        )

    @property
    def is_track(self) -> bool:
        return self.kind == "Audio"


def time_label(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60:02}:{seconds % 60:02}"


class Queue:
    def __init__(self):
        self.items: list[Item] = []
        self.index = -1

    @property
    def current(self) -> Item | None:
        return self.items[self.index] if 0 <= self.index < len(self.items) else None

    def replace(self, items: list[Item], index: int):
        if not 0 <= index < len(items) or not all(i.is_track for i in items):
            raise ValueError("Fila inválida")
        self.items = list(items)
        self.index = index

    def play_from(self, items: list[Item], row: int):
        """A fila é o sufixo musical da lista visível, preservando repetições."""
        if not 0 <= row < len(items) or not items[row].is_track:
            raise ValueError("Selecione uma faixa")
        self.replace([item for item in items[row:] if item.is_track], 0)

    def move(self, offset: int) -> Item | None:
        new = self.index + offset
        if 0 <= new < len(self.items):
            self.index = new
            return self.current
        return None
