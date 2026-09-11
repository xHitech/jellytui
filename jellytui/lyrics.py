"""LRC e LyricDto Jellyfin normalizados em segundos; sem relógio próprio."""
import re
from bisect import bisect_right
from dataclasses import dataclass, field

TIMESTAMP = re.compile(r"\[(\d+):([0-5]\d)(?:[.:](\d{1,3}))?\]")
OFFSET = re.compile(r"\[offset:([+-]?\d+)\]", re.IGNORECASE)


@dataclass(frozen=True)
class LyricLine:
    start: float
    text: str


@dataclass
class Lyrics:
    lines: list[LyricLine] = field(default_factory=list)
    plain: list[str] = field(default_factory=list)
    starts: list[float] = field(init=False, repr=False)

    def __post_init__(self):
        # Linhas simultâneas (por exemplo tradução) ficam destacadas juntas.
        grouped = {}
        for line in sorted(self.lines, key=lambda line: line.start):
            grouped.setdefault(line.start, []).append(line.text)
        self.lines = [LyricLine(start, " / ".join(texts)) for start, texts in grouped.items()]
        self.starts = [line.start for line in self.lines]

    def index_at(self, position: float) -> int:
        return bisect_right(self.starts, position) - 1

    @classmethod
    def from_jellyfin(cls, data: dict) -> "Lyrics":
        lines, plain = [], []
        for entry in data.get("Lyrics") or []:
            text = entry.get("Text") or ""
            start = entry.get("Start")
            if isinstance(start, (int, float)):
                lines.append(LyricLine(start / 10_000_000, text))
            elif text:
                plain.append(text)
        # Start é o timestamp fornecido pelo parser do servidor, já normalizado.
        return cls(lines, plain)


def parse_lrc(content: str) -> Lyrics:
    lines, plain = [], []
    offsets = OFFSET.findall(content)
    offset = int(offsets[-1]) / 1000 if offsets else 0
    for raw in content.lstrip("\ufeff").splitlines():
        matches = list(TIMESTAMP.finditer(raw))
        if not matches:
            if raw.strip() and not raw.lstrip().startswith("["):
                plain.append(raw.strip())
            continue
        text = TIMESTAMP.sub("", raw).strip()
        for match in matches:
            minute, second, fraction = match.groups()
            start = int(minute) * 60 + int(second) + (float("0." + fraction) if fraction else 0)
            # LRC offset positivo adianta a letra em relação ao áudio.
            lines.append(LyricLine(start - offset, text))
    return Lyrics(lines, plain)
