"""Validação opt-in, somente leitura, contra o Jellyfin configurado pelo usuário."""
import asyncio
import os
import pytest
from jellytui.app import JellyTui
from jellytui.config import Config
from jellytui.jellyfin import Jellyfin
from jellytui.player import MpvPlayer
from jellytui.widgets.track_list import TrackList
from jellytui.widgets.lyrics import LyricsPanel
from jellytui.widgets.help import HelpScreen
from textual.widgets import Input


@pytest.mark.skipif(os.environ.get("JELLYTUI_LIVE_TEST") != "1", reason="teste real opt-in")
async def test_live_library_and_tui_playback():
    config = Config.load()
    assert config is not None, "Execute jellytui --setup antes do teste real"
    api = Jellyfin(config)
    player = MpvPlayer(audio_output="null")
    app = JellyTui(api, player)
    async with app.run_test(size=(120, 35)) as pilot:
        await app.workers.wait_for_complete()
        table = app.query_one(TrackList)
        assert table.items[0].name == "Artistas"
        assert not app.query("#browser")
        for category in ("Pastas", "Playlists", "Favoritos"):
            await api.browse(category)
        table.move_cursor(row=1)
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert table.items and table.items[0].kind == "MusicAlbum"
        table.focus()
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert table.items and table.items[0].is_track
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause(3)
        assert app.playing_item is not None
        assert (player.properties.get("time-pos") or 0) > 0
        assert app.mode.startswith("Direct Play")
        await pilot.press("space")
        assert await player.command("get_property", "pause") is True
        await pilot.press("right", "minus")
        assert await player.command("get_property", "time-pos") >= 5
        assert await player.command("get_property", "volume") < 70
        await pilot.press("n")
        assert app.queue.index == 1
        await pilot.press("p")
        assert app.queue.index == 0
        # Leitura de letra já indexada, sem upload, download remoto ou favoritos.
        await pilot.press("slash")
        app.main_screen.query_one(Input).value = "Duvet"
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        track_row = next(i for i, item in enumerate(table.items) if item.is_track)
        table.move_cursor(row=track_row)
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        panel = app.main_screen.query_one(LyricsPanel)
        async with asyncio.timeout(20):
            while panel.message == "Carregando letra…":
                await pilot.pause(0.1)
        assert app.playing_item.id == table.selected.id
        assert len(panel.lyrics.lines) > 1, panel.message
        # Carregar letras e terminar loadfile são operações independentes.
        async with asyncio.timeout(20):
            while not (player.properties.get("duration") and (player.properties.get("time-pos") or 0) > 0):
                await pilot.pause(0.1)
        target = panel.lyrics.lines[1].start + 0.2
        await app.action_seek(target - (player.properties.get("time-pos") or 0))
        await pilot.pause(0.3)
        assert panel.current_index == panel.lyrics.index_at(player.properties.get("time-pos") or 0)
        assert panel.current_index >= 1, (target, player.properties, app.mode)
        await pilot.press("space")
        await pilot.pause(0.3)
        index = panel.current_index
        await pilot.press("h")
        assert isinstance(app.screen, HelpScreen)
        await pilot.pause(0.3)
        assert panel.current_index == index
        await pilot.press("h", "l")
        assert not panel.display
        await pilot.press("l")
        assert panel.display
        print(f"Servidor real: Duvet retornou {len(panel.lyrics.lines)} linhas sincronizadas; seek e Help validados.")
    assert player.process.returncode is not None
