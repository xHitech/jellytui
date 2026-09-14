import asyncio
import pytest
from textual.widgets import Input, Static
from jellytui.app import JellyTui
from jellytui.controls import SHORTCUTS, bindings_for
from jellytui.demo import DemoLibrary
from jellytui.jellyfin import Stream, JellyfinError
from jellytui.lyrics import parse_lrc, Lyrics
from jellytui.models import Item
from jellytui.widgets.track_list import TrackList
from jellytui.widgets.lyrics import LyricsPanel
from jellytui.widgets.now_playing import NowPlaying
from jellytui.widgets.help import HelpScreen, help_text


class Library(DemoLibrary):
    async def stream(self, item):
        return Stream("http://example/" + item.id, {}, "FLAC • 16-bit • 44.1 kHz • Stereo")

    async def lyrics(self, item):
        if item.id == "1":
            return Lyrics()
        return parse_lrc(f"[00:00]Intro {item.id}\n[00:05]Middle {item.id}\n[00:10]End {item.id}")


class Player:
    def __init__(self):
        self.events = asyncio.Queue()
        self.properties = {"time-pos": 0, "duration": 240, "pause": True, "volume": 70}
        self.calls = []
        self.entry_id = 1

    async def start(self): pass
    async def close(self): pass

    async def play(self, url, headers):
        self.calls.append(url)
        self.entry_id += 1
        self.properties.update({"time-pos": 0, "pause": False})

    async def pause(self):
        self.properties["pause"] = not self.properties["pause"]

    async def seek(self, offset):
        self.properties["time-pos"] = max(0, self.properties["time-pos"] + offset)

    async def volume(self, offset):
        self.properties["volume"] += offset


async def select_tracks(app, pilot, row=0):
    table = app.main_screen.query_one(TrackList)
    app.display(await app.library.browse("Favoritos"), "Faixas")
    table.move_cursor(row=row)
    table.focus()
    await pilot.press("enter")
    await app.workers.wait_for_complete()


async def test_levels_back_and_cursor_restore():
    app = JellyTui()
    async with app.run_test(size=(100, 32)) as pilot:
        table = app.query_one(TrackList)
        assert table.region.width == app.size.width
        assert not app.query("#browser")
        assert [i.name for i in table.items] == ["Artistas", "Álbuns", "Pastas", "Playlists", "Favoritos"]
        await pilot.press("enter", "enter", "enter")
        assert table.items[0].name == "Sun Killer"
        await pilot.press("backspace")
        assert table.selected.name == "Eternal Blue"
        await pilot.press("backspace")
        assert table.selected.name == "Spiritbox"
        await pilot.press("backspace")
        assert app.view_title == "Biblioteca"
        await pilot.press("j", "j", "enter")
        assert app.view_title == "Pastas"
        await pilot.press("backspace")
        assert table.cursor_row == 2 and table.selected.name == "Pastas"
        await pilot.press("backspace")
        assert app.view_title == "Biblioteca"


@pytest.mark.parametrize("category", range(5))
async def test_every_root_category_remains_reachable(category):
    app = JellyTui()
    async with app.run_test() as pilot:
        table = app.query_one(TrackList)
        table.move_cursor(row=category)
        name = table.selected.name
        await pilot.press("enter")
        assert app.view_title == name
        assert table.items
        await pilot.press("backspace")
        assert table.cursor_row == category


@pytest.mark.parametrize("context", ["Álbum", "Playlist", "Favoritos", "Busca", "Faixas do artista"])
async def test_context_suffix_and_auto_advance(context):
    app = JellyTui(Library(), Player())
    async with app.run_test() as pilot:
        items = [Item("a", "Álbum", "MusicAlbum")] + [Item(str(i), str(i), "Audio") for i in range(5)]
        app.display(items, context)
        table = app.query_one(TrackList)
        table.move_cursor(row=3)  # terceira faixa: há um álbum antes das faixas
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert [i.id for i in app.queue.items] == ["2", "3", "4"]
        assert app.queue.index == 0
        await app.player.events.put({"event": "end-file", "reason": "eof"})
        await pilot.pause(0.3)
        assert app.playing_item.id == "3"
        await app.player.events.put({"event": "end-file", "reason": "eof"})
        await pilot.pause(0.3)
        assert app.playing_item.id == "4"
        await app.player.events.put({"event": "end-file", "reason": "eof"})
        await pilot.pause(0.3)
        assert app.mode == "Fim da fila"


async def test_lyrics_follow_real_position_seek_pause_and_toggle():
    player = Player()
    app = JellyTui(Library(), player)
    async with app.run_test(size=(110, 32)) as pilot:
        await select_tracks(app, pilot)
        panel = app.query_one(LyricsPanel)
        assert panel.current_index == 0
        player.properties["time-pos"] = 7
        await pilot.pause(0.3)
        assert panel.current_index == 1
        await pilot.press("space")
        await pilot.pause(0.4)
        assert panel.current_index == 1 and player.properties["pause"]
        await pilot.press("left")
        assert panel.current_index == 0
        await pilot.press("right", "right")
        assert panel.current_index == 2
        before_width = app.query_one(NowPlaying).size.width
        await pilot.press("l")
        assert not panel.display
        assert app.query_one(NowPlaying).size.width > before_width
        player.properties["time-pos"] = 6
        await pilot.press("l")
        assert panel.display and panel.current_index == 1


async def test_track_change_clears_and_reloads_lyrics():
    app = JellyTui(Library(), Player())
    async with app.run_test() as pilot:
        await select_tracks(app, pilot)
        panel = app.query_one(LyricsPanel)
        assert panel.lyrics.lines
        await pilot.press("n")
        await app.workers.wait_for_complete()
        assert not panel.lyrics.lines
        assert "Letra não disponível" in str(panel.render())
        await pilot.press("n")
        await app.workers.wait_for_complete()
        assert panel.lyrics.lines[0].text == "Intro 2"
        assert panel.current_index == 0


async def test_slow_lyrics_do_not_block_or_replace_new_track():
    gate = asyncio.Event()
    class Slow(Library):
        async def lyrics(self, item):
            if item.id == "0":
                await gate.wait()
            return await super().lyrics(item)
    app = JellyTui(Slow(), Player())
    async with app.run_test() as pilot:
        app.display(await app.library.browse("Favoritos"), "Faixas")
        await pilot.press("enter")
        assert app.playing_item.id == "0"
        panel = app.query_one(LyricsPanel)
        assert not panel.lyrics.lines and panel.message == "Carregando letra…"
        await pilot.press("n", "n")
        gate.set()
        await app.workers.wait_for_complete()
        assert app.playing_item.id == "2"
        assert panel.lyrics.lines[0].text == "Intro 2"


async def test_lyric_network_error_does_not_stop_music():
    class Broken(Library):
        async def lyrics(self, item):
            raise JellyfinError("Conexão indisponível")
    app = JellyTui(Broken(), Player())
    async with app.run_test() as pilot:
        await select_tracks(app, pilot)
        assert app.playing_item and not app.player.properties["pause"]
        assert app.query_one(LyricsPanel).message == "Não foi possível carregar a letra"


async def test_help_closes_both_keys_and_playback_continues():
    app = JellyTui(Library(), Player())
    async with app.run_test(size=(110, 32)) as pilot:
        await select_tracks(app, pilot)
        await pilot.press("h")
        assert isinstance(app.screen, HelpScreen)
        app.player.properties["time-pos"] = 7
        await pilot.pause(0.3)
        assert app.main_screen.query_one(LyricsPanel).current_index == 1
        assert not app.player.properties["pause"]
        await app.player.events.put({"event": "end-file", "reason": "eof"})
        await pilot.pause(0.3)
        assert app.playing_item.id == "1"
        await pilot.press("h")
        assert not isinstance(app.screen, HelpScreen)
        await pilot.press("h", "escape")
        assert not isinstance(app.screen, HelpScreen)
        assert app.query_one(TrackList).has_focus


def test_help_matches_actual_bindings_and_actions():
    assert JellyTui.BINDINGS == bindings_for("app")
    assert TrackList.BINDINGS == bindings_for("table")
    text = help_text().plain
    for shortcut in SHORTCUTS:
        cls = JellyTui if shortcut.target == "app" else TrackList
        assert hasattr(cls, "action_" + shortcut.action.split("(")[0])
        assert shortcut.description in text and shortcut.label in text
    assert {s.action for s in SHORTCUTS if s.footer} == {"pause", "next_track", "previous_track", "search", "toggle_lyrics", "help", "quit"}


async def test_help_and_lyrics_keys_remain_text_in_search():
    app = JellyTui()
    async with app.run_test() as pilot:
        await pilot.press("slash", "h", "l", "space", "q")
        assert app.query_one(Input).value == "hl q"
        assert not isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        assert app.query_one(TrackList).has_focus


async def test_loading_replacement_clears_previous_lines_and_redraw_is_cached():
    gate = asyncio.Event()
    class DelayedSecond(Library):
        async def lyrics(self, item):
            if item.id == "1":
                await gate.wait()
            return await super().lyrics(item)
    app = JellyTui(DelayedSecond(), Player())
    async with app.run_test() as pilot:
        await select_tracks(app, pilot)
        panel = app.query_one(LyricsPanel)
        assert panel.lyrics.lines
        signature = panel.last_render
        panel.sync(0.5)
        assert panel.last_render == signature  # mesma linha: nenhum novo render
        await pilot.press("n")
        assert not panel.lyrics.lines
        assert panel.message == "Carregando letra…"
        gate.set()
        await app.workers.wait_for_complete()
        assert panel.message == "Letra não disponível"


async def test_stale_mpv_eof_does_not_skip_current_track():
    app = JellyTui(Library(), Player())
    async with app.run_test() as pilot:
        await select_tracks(app, pilot)
        await app.player.events.put({"event": "end-file", "reason": "eof", "playlist_entry_id": -1})
        await pilot.pause(0.3)
        assert app.queue.index == 0 and app.playing_item.id == "0"


async def test_lyrics_plain_text_and_no_song_message():
    app = JellyTui()
    async with app.run_test() as pilot:
        panel = app.query_one(LyricsPanel)
        panel.sync(0)
        assert "Letra não disponível" in str(panel.render())
        panel.set_lyrics(Lyrics(plain=["Plain line"]))
        assert "Letra sem sincronização" in str(panel.render())
        assert panel.current_index == -1


async def test_compact_terminal_keeps_metadata_and_footer_visible():
    app = JellyTui(Library(), Player())
    async with app.run_test(size=(80, 24)) as pilot:
        await select_tracks(app, pilot)
        app.playing_item.name = "Um título muito longo " * 10
        await pilot.pause(0.3)
        rows = [strip.text for strip in app.screen._compositor.render_strips()]
        assert any("FLAC" in row and "Stereo" in row for row in rows[:9])
        assert any("Direct Play" in row for row in rows[:9])
        assert "Play/Pause" in rows[-1] and "Ajuda" in rows[-1] and "Sair" in rows[-1]


async def test_context_line_has_no_duplicated_help_and_footer_retains_h():
    app = JellyTui()
    async with app.run_test(size=(110, 32)) as pilot:
        status_text = str(app.query_one("#status", Static).render())
        assert "Biblioteca · 5 itens" in status_text
        assert "h ajuda" not in status_text.lower()
        await pilot.press("enter")
        status_sub = str(app.query_one("#status", Static).render())
        assert "Biblioteca › Artistas" in status_sub
        assert "itens" in status_sub
        assert "h ajuda" not in status_sub.lower()

        rows = [strip.text for strip in app.screen._compositor.render_strips()]
        footer_row = rows[-1]
        assert "h" in footer_row and "Ajuda" in footer_row


async def test_volume_controls_main_keyboard_and_numpad():
    player = Player()
    app = JellyTui(Library(), player)
    async with app.run_test(size=(110, 32)) as pilot:
        await select_tracks(app, pilot)
        assert player.properties["volume"] == 70

        # tecla + continuar aumentando volume
        await pilot.press("plus")
        assert player.properties["volume"] == 75
        await pilot.press("+")
        assert player.properties["volume"] == 80

        # tecla - continuar diminuindo volume
        await pilot.press("minus")
        assert player.properties["volume"] == 75
        await pilot.press("-")
        assert player.properties["volume"] == 70

        # Numpad + (add) aumentar volume
        await pilot.press("add")
        assert player.properties["volume"] == 75

        # Numpad - (subtract) diminuir volume
        await pilot.press("subtract")
        assert player.properties["volume"] == 70


def test_help_reflects_volume_and_numpad_shortcuts():
    text = help_text().plain
    assert "+ / Numpad +    Aumentar volume" in text
    assert "- / Numpad -    Diminuir volume" in text
    assert "h ou Escape fecha" in text


def test_album_artist_metadata_extraction():
    # 1. Álbum com AlbumArtist
    item_album_artist = Item.from_api({
        "Id": "a1",
        "Name": "Asylum",
        "Type": "MusicAlbum",
        "AlbumArtist": "Disturbed",
        "Artists": [],
    })
    assert item_album_artist.artist == "Disturbed"

    # 2. Álbum com Artists
    item_artists = Item.from_api({
        "Id": "a2",
        "Name": "Take Me Back to Eden",
        "Type": "MusicAlbum",
        "AlbumArtist": None,
        "Artists": ["Sleep Token"],
    })
    assert item_artists.artist == "Sleep Token"

    # 3. Álbum sem artista
    item_no_artist = Item.from_api({
        "Id": "a3",
        "Name": "Avenged Sevenfold",
        "Type": "MusicAlbum",
        "AlbumArtist": None,
        "Artists": [],
    })
    assert item_no_artist.artist == ""


async def test_album_without_artist_shows_dash_not_album():
    app = JellyTui()
    async with app.run_test() as pilot:
        table = app.query_one(TrackList)
        item = Item.from_api({
            "Id": "a_no_art",
            "Name": "Álbum Sem Artista",
            "Type": "MusicAlbum",
            "AlbumArtist": None,
            "Artists": [],
        })
        table.show_items([item], context="Álbuns")
        cell_text = table.get_cell_at((0, 1)).plain
        assert cell_text in ("—", "")
        assert cell_text != "Álbum"


async def test_correct_columns_in_artists_albums_and_tracks():
    app = JellyTui()
    async with app.run_test(size=(110, 32)) as pilot:
        table = app.query_one(TrackList)

        # 1. Artistas: Nome | Tipo
        table.move_cursor(row=0)
        await pilot.press("enter")
        await pilot.pause()
        assert [c.label.plain for c in table.ordered_columns] == ["Nome", "Tipo"]
        assert table.get_cell_at((0, 0)).plain == "Spiritbox"
        assert table.get_cell_at((0, 1)).plain == "Artista"

        # 2. Voltar à raiz e navegar para Álbuns: Nome | Artista
        await pilot.press("backspace")
        table.move_cursor(row=1)
        await pilot.press("enter")
        await pilot.pause()
        assert [c.label.plain for c in table.ordered_columns] == ["Nome", "Artista"]
        assert table.get_cell_at((0, 0)).plain == "Eternal Blue"
        assert table.get_cell_at((0, 1)).plain == "Spiritbox"

        # 3. Entrar no álbum para Faixas: Nome | Artista | Álbum | Tempo
        await pilot.press("enter")
        await pilot.pause()
        assert [c.label.plain for c in table.ordered_columns if c.label.plain] == [
            "Nome", "Artista", "Álbum", "Tempo"
        ]
        assert [c.label.plain for c in table.ordered_columns] == [
            "", "Nome", "Artista", "Álbum", "Tempo"
        ]
        assert table.get_cell_at((0, 1)).plain == "Sun Killer"
        assert table.get_cell_at((0, 2)).plain == "Spiritbox"
        assert table.get_cell_at((0, 3)).plain == "Eternal Blue"
        assert table.get_cell_at((0, 4)).plain == "04:00"
