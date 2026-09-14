import asyncio
from functools import wraps
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Static, Input, DataTable
from .jellyfin import JellyfinError
from .player import PlayerError
from .demo import DemoLibrary
from .widgets.browser import library_entries
from .models import Item, Queue
from .controls import bindings_for
from .widgets.help import HelpScreen
from .widgets.now_playing import NowPlaying
from .widgets.lyrics import LyricsPanel
from .widgets.track_list import TrackList


def guarded(method):
    """Erros externos são recuperáveis e não exibem URLs ou credenciais."""
    @wraps(method)
    async def wrapped(self, *args, **kwargs):
        try:
            return await method(self, *args, **kwargs)
        except (JellyfinError, PlayerError) as error:
            self.main_screen.query_one("#status", Static).update(str(error))
            self.notify(str(error), severity="error", timeout=8)
    return wrapped


class JellyTui(App, inherit_bindings=False):
    TITLE = "jellytui"
    CSS = """
    Screen { background: #101214; color: #d2d5d7; }
    #top { height: 9; }
    #lyrics { width: 45%; height: 9; border: solid #444b50; padding: 0 1; }
    #now-playing { width: 1fr; height: 9; border: solid #444b50; padding: 0 1; }
    #now-playing, #lyrics { text-wrap: nowrap; text-overflow: ellipsis; }
    #tracks { height: 1fr; border: solid #444b50; }
    #status { height: 1; color: #a1a9ad; }
    #search { display: none; }
    Footer { background: #252a2e; }
    """
    BINDINGS = bindings_for("app")
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, library=None, player=None):
        super().__init__()
        self.library = library or DemoLibrary()
        self.player = player
        self.queue = Queue()
        self.history = []
        self.context = "Biblioteca"
        self.view_title = "Biblioteca"
        self.play_lock = asyncio.Lock()
        self.playing_item = None
        self.lyric_generation = 0
        self.quality = ""
        self.mode = "DEMO — sem reprodução" if player is None else ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield NowPlaying()
            yield LyricsPanel()
        yield TrackList()
        yield Input(placeholder="Buscar músicas, artistas e álbuns… Enter confirma; Escape fecha", id="search")
        yield Static("jellytui", id="status", markup=False)
        yield Footer()

    async def on_mount(self):
        self.main_screen = self.screen
        self.main_screen.query_one(NowPlaying).show()
        self.set_interval(0.25, self.tick)
        if self.player:
            try:
                await self.player.start()
            except PlayerError as error:
                self.notify(str(error), severity="error")
        self.initial_load()
        self.main_screen.query_one(TrackList).focus()

    @work(group="navigation", exclusive=True)
    @guarded
    async def initial_load(self):
        await self.load("Biblioteca", remember=False)

    async def on_unmount(self):
        if self.player:
            await self.player.close()
        await self.library.close()

    def check_action(self, action, parameters):
        # Prioridade dos atalhos globais não pode consumir texto da busca.
        if isinstance(self.focused, Input):
            return action == "close_overlay"
        if isinstance(self.screen, HelpScreen):
            return action in {"help", "close_overlay", "quit", "pause", "next_track",
                              "previous_track", "seek", "volume", "toggle_lyrics"}
        return True

    @guarded
    async def tick(self):
        if not self.main_screen.query(NowPlaying):
            return  # Os widgets já podem ter sido desmontados ao sair.
        self.update_now_playing()
        if not self.player:
            return
        while not self.player.events.empty():
            event = self.player.events.get_nowait()
            if event.get("event") == "end-file":
                if "playlist_entry_id" in event and event["playlist_entry_id"] != getattr(self.player, "entry_id", None):
                    continue  # Evento atrasado de uma faixa já substituída.
                if event.get("reason") == "eof":
                    if self.queue.move(1):
                        await self.play_current()
                    else:
                        self.mode = "Fim da fila"
                        self.player.properties["pause"] = True
                elif event.get("reason") == "error":
                    self.mode = "Falha na reprodução"
                    raise PlayerError("mpv não conseguiu reproduzir a faixa. Verifique conexão, acesso e saída de áudio; n tenta a próxima.")
            elif event.get("event") == "ipc-disconnected":
                self.mode = "mpv desconectado"
                raise PlayerError("mpv encerrou inesperadamente. Reinicie jellytui para reconectar o player.")

    def update_now_playing(self):
        state = self.player.properties if self.player else {}
        self.main_screen.query_one(NowPlaying).show(
            self.playing_item, state.get("time-pos") or 0, state.get("duration") or 0,
            state.get("pause", True), state.get("volume") or 0, self.quality, self.mode)
        self.main_screen.query_one(LyricsPanel).sync(state.get("time-pos") or 0)


    async def load(self, context, remember=True):
        self.main_screen.query_one("#status", Static).update("Carregando biblioteca…")
        items = (library_entries()
                 if context == "Biblioteca" else await self.library.browse(context))
        if remember:
            self.remember_view()
        self.context = context
        self.display(items, context.name if isinstance(context, Item) else context)
        self.main_screen.query_one(TrackList).move_cursor(row=0)
        return items

    def remember_view(self):
        table = self.main_screen.query_one(TrackList)
        self.history.append((self.context, self.view_title, list(table.items), table.cursor_row))

    def display(self, items, title):
        table = self.main_screen.query_one(TrackList)
        self.view_title = str(title)
        table.border_title = str(title)
        table.show_items(items, self.playing_item.id if self.playing_item else None, context=title)
        path = " › ".join([view[1] for view in self.history] + [str(title)])
        self.main_screen.query_one("#status", Static).update(f"{path} · {len(items)} itens")

    @work(group="navigation", exclusive=True)
    @guarded
    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        table = self.main_screen.query_one(TrackList)
        item = table.selected
        if item is None:
            return
        if item.is_track:
            self.queue.play_from(table.items, table.cursor_row)
            await self.play_current()
        else:
            await self.load(item.name if item.kind == "Category" else item)

    async def play_current(self):
        async with self.play_lock:
            item = self.queue.current
            if item is None:
                return
            if self.player:
                stream = await self.library.stream(item)
                await self.player.play(stream.url, stream.headers)
                self.quality, self.mode = stream.quality, stream.mode
            self.playing_item = item
            self.lyric_generation += 1
            self.main_screen.query_one(LyricsPanel).set_lyrics(message="Carregando letra…")
            self.load_lyrics(item, self.lyric_generation)
            self.refresh_playing()

    @work(group="lyrics", exclusive=True)
    async def load_lyrics(self, item, generation):
        try:
            lyrics = await self.library.lyrics(item)
            message = "Letra não disponível"
        except JellyfinError:
            lyrics = None
            message = "Não foi possível carregar a letra"
        if generation == self.lyric_generation:
            panel = self.main_screen.query_one(LyricsPanel)
            panel.set_lyrics(lyrics, message)
            panel.sync((self.player.properties.get("time-pos") or 0) if self.player else 0)

    def action_toggle_lyrics(self):
        panel = self.main_screen.query_one(LyricsPanel)
        panel.display = not panel.display
        panel.last_render = None
        self.update_now_playing()

    def refresh_playing(self):
        table = self.main_screen.query_one(TrackList)
        table.show_items(table.items, self.playing_item.id if self.playing_item else None, context=self.view_title)
        self.update_now_playing()

    def action_back(self):
        self.workers.cancel_group(self, "navigation")
        if self.history:
            self.context, title, items, row = self.history.pop()
            self.display(items, title)
            self.main_screen.query_one(TrackList).move_cursor(row=row)

    def action_search(self):
        search = self.main_screen.query_one(Input)
        search.display = True
        search.focus()

    def action_help(self):
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            self.push_screen(HelpScreen())

    def action_close_overlay(self):
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        elif self.main_screen.query_one(Input).display:
            self.workers.cancel_group(self, "navigation")
            self.main_screen.query_one(Input).display = False
            self.main_screen.query_one(TrackList).focus()

    @work(group="navigation", exclusive=True)
    @guarded
    async def on_input_submitted(self, event: Input.Submitted):
        items = await self.library.search(event.value)
        self.remember_view()
        self.display(items, f"Busca: {event.value}")
        event.input.display = False
        self.main_screen.query_one(TrackList).focus()

    @guarded
    async def action_favorite(self):
        item = self.main_screen.query_one(TrackList).selected
        if isinstance(item, Item) and item.kind != "Category":
            await self.library.favorite(item)
            for other in self.main_screen.query_one(TrackList).items + self.queue.items:
                if other.id == item.id:
                    other.favorite = item.favorite
            self.refresh_playing()

    def action_show_queue(self):
        self.remember_view()
        self.display(self.queue.items, "Fila local")
        self.main_screen.query_one(TrackList).focus()

    @guarded
    async def action_pause(self):
        if self.player and self.playing_item:
            await self.player.pause()

    @guarded
    async def action_next_track(self):
        if self.queue.move(1):
            await self.play_current()

    @guarded
    async def action_previous_track(self):
        if self.queue.move(-1):
            await self.play_current()

    @guarded
    async def action_seek(self, offset):
        if self.player and self.playing_item:
            await self.player.seek(offset)
            self.update_now_playing()

    @guarded
    async def action_volume(self, offset):
        if self.player:
            await self.player.volume(offset)
