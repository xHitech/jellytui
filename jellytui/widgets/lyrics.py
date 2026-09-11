from rich.text import Text
from textual.widgets import Static
from ..lyrics import Lyrics


class LyricsPanel(Static):
    def __init__(self):
        super().__init__(id="lyrics", markup=False)
        self.border_title = "LETRA (LRC)"
        self.lyrics = Lyrics()
        self.current_index = -1
        self.message = "Letra não disponível"
        self.last_render = None
        self.position = 0

    def set_lyrics(self, lyrics=None, message="Letra não disponível"):
        self.lyrics = lyrics or Lyrics()
        self.current_index = -1
        self.message = message
        self.last_render = None
        self.sync(0)

    def on_resize(self):
        self.last_render = None
        self.sync(self.position)

    def sync(self, position):
        self.position = position
        index = self.lyrics.index_at(position)
        self.current_index = index
        signature = (index, self.size.width, self.size.height, self.message)
        if signature == self.last_render or not self.display:
            return
        self.last_render = signature
        if not self.lyrics.lines:
            if self.lyrics.plain:
                self.update(Text("Letra sem sincronização\n" + "\n".join(self.lyrics.plain[:5]), style="dim"))
            else:
                self.update(Text(self.message, style="dim"))
            return
        # Janela de cinco linhas centrada na posição real do mpv.
        output = Text(no_wrap=True, overflow="ellipsis")
        for line_index in range(index - 2, index + 3):
            if 0 <= line_index < len(self.lyrics.lines):
                active = line_index == index
                output.append(("> " if active else "  ") + self.lyrics.lines[line_index].text,
                              style="bold cyan" if active else "dim")
            output.append("\n")
        self.update(output)
