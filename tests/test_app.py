from jellytui.app import JellyTui
from jellytui.widgets.track_list import TrackList


async def test_demo_navigation():
    app = JellyTui()
    async with app.run_test(size=(110, 32)) as pilot:
        table = app.query_one(TrackList)
        assert table.items[0].name == "Artistas"
        assert not app.query("#browser")
        table.focus()
        await pilot.press("enter")
        assert table.items[0].name == "Spiritbox"
        await pilot.press("enter")
        assert table.items[0].name == "Eternal Blue"
        await pilot.press("enter")
        assert len(table.items) == 3
        await pilot.press("enter")
        assert app.queue.current.name == "Sun Killer"
        await pilot.press("n")
        assert app.queue.current.name == "Hurt You"
        await pilot.press("backspace")
        assert table.items[0].name == "Eternal Blue"


async def test_search_keys_are_text_and_favorite():
    from textual.widgets import Input
    app = JellyTui()
    async with app.run_test(size=(100, 30)) as pilot:
        table = app.query_one(TrackList)
        table.focus()
        await pilot.press("slash")
        search = app.query_one(Input)
        assert search.has_focus
        await pilot.press("h", "u", "r", "t", "space", "q", "n", "p", "f", "left", "backspace")
        assert search.value == "hurt qnf"
        search.value = "Hurt"
        await pilot.press("enter")
        assert len(table.items) == 1 and table.selected.name == "Hurt You"
        await pilot.press("f")
        assert table.selected.favorite
        await pilot.press("backspace")
        assert table.selected.name == "Artistas"


async def test_errors_keep_app_running():
    from jellytui.demo import DemoLibrary
    from jellytui.jellyfin import JellyfinError
    from textual.widgets import Static
    class Offline(DemoLibrary):
        async def browse(self, context):
            raise JellyfinError("Servidor indisponível")
    app = JellyTui(Offline())
    async with app.run_test() as pilot:
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert "Servidor indisponível" in str(app.query_one("#status", Static).render())
        assert app.is_running


async def test_player_controls_and_auto_advance():
    import asyncio
    from jellytui.demo import DemoLibrary
    from jellytui.jellyfin import Stream
    class Library(DemoLibrary):
        async def stream(self, item):
            return Stream("http://example/" + item.id, {})
    class Player:
        def __init__(self):
            self.events = asyncio.Queue()
            self.properties = {}
            self.calls = []
        async def start(self): pass
        async def close(self): pass
        async def play(self, url, headers): self.calls.append(("play", url))
        async def pause(self): self.calls.append(("pause",))
        async def seek(self, offset): self.calls.append(("seek", offset))
        async def volume(self, offset): self.calls.append(("volume", offset))
    player = Player()
    app = JellyTui(Library(), player)
    async with app.run_test(size=(110, 32)) as pilot:
        table = app.query_one(TrackList)
        table.focus()
        await pilot.press("enter", "enter", "enter", "enter", "space", "right", "left", "plus", "minus", "add", "subtract")
        assert ("pause",) in player.calls
        assert ("seek", 5) in player.calls and ("seek", -5) in player.calls
        assert player.calls.count(("volume", 5)) == 2 and player.calls.count(("volume", -5)) == 2
        await player.events.put({"event": "end-file", "reason": "eof"})
        await pilot.pause(0.4)
        assert app.playing_item.name == "Hurt You"
        await player.events.put({"event": "end-file", "reason": "stop"})
        await pilot.pause(0.4)
        assert app.playing_item.name == "Hurt You"


async def test_duplicate_playlist_selection_and_late_eof():
    from jellytui.models import Item
    app = JellyTui()
    async with app.run_test() as pilot:
        table = app.query_one(TrackList)
        table.show_items([Item("a", "A", "Audio"), Item("a", "A", "Audio"), Item("b", "B", "Audio")])
        table.focus()
        table.move_cursor(row=1)
        await pilot.press("enter")
        assert app.queue.index == 0
        assert len(app.queue.items) == 2
        await pilot.press("n")
        assert app.playing_item.name == "B"
