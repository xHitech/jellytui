import asyncio
import shutil
import wave
import pytest
from jellytui.player import MpvPlayer


async def wait_mpv_event(player, name):
    async with asyncio.timeout(5):
        while (await player.events.get()).get("event") != name:
            pass


@pytest.mark.skipif(not shutil.which("mpv"), reason="mpv ausente")
async def test_real_mpv_ipc(tmp_path):
    wav = tmp_path / "test.wav"
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b"\0" * 8000 * 4 * 3)
    player = MpvPlayer(audio_output="null")
    try:
        await player.start()
        # ao=null simula um dispositivo com buffer. No mpv 0.41, time-pos
        # pausado após seek inclui esse atraso: buffers de 0.05/0.2/0.4 s
        # produziram desvios de ~0.032/0.192/0.384 s em WAV PCM 8 kHz.
        # O mesmo ocorre via IPC direto e em 44.1/48 kHz; não é erro do wrapper.
        # Fixamos o buffer só neste teste; a tolerância é limitada a esse buffer
        # mais uma amostra, menor que os 100 ms anteriores. Não usar untimed:
        # precisamos manter pausa e avanço até EOF sob um relógio real.
        # Referência: https://mpv.io/manual/stable/#audio-output-drivers
        null_buffer = 0.05
        await player.command("set_property", "options/ao-null-buffer", null_buffer)
        await player.play(str(wav))
        await wait_mpv_event(player, "file-loaded")
        await wait_mpv_event(player, "playback-restart")
        assert await player.command("get_property", "duration") == pytest.approx(3)
        await player.pause()
        assert await player.command("get_property", "pause") is True
        await player.volume(-5)
        assert await player.command("get_property", "volume") <= 70
        for offset in (1, -0.5):
            before_seek = await player.command("get_property", "time-pos")
            await player.seek(offset)
            # A resposta do comando confirma aceitação, não término do seek.
            # Consumir seek antes de playback-restart evita aceitar evento antigo.
            await wait_mpv_event(player, "seek")
            await wait_mpv_event(player, "playback-restart")
            position = await player.command("get_property", "time-pos")
            assert position == pytest.approx(before_seek + offset, abs=null_buffer + 1 / 8000)
            assert await player.command("get_property", "pause") is True
        await player.pause()
        async with asyncio.timeout(6):
            while True:
                event = await player.events.get()
                if event.get("event") == "end-file":
                    assert event["reason"] == "eof"
                    break
    finally:
        await player.close()
    assert player.process.returncode is not None
    assert not __import__('pathlib').Path(player.temp.name).exists()


@pytest.mark.skipif(not shutil.which("mpv"), reason="mpv ausente")
async def test_http_stream_authentication(tmp_path):
    """mpv real lê bytes por HTTP com autenticação recebida pelo socket."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    import io
    import pathlib
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b"\0" * 8000 * 4)
    payload = buffer.getvalue()
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(self.headers.get("Authorization"))
            if self.headers.get("Authorization") != "MediaBrowser Token=integration-test":
                self.send_error(401)
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    player = MpvPlayer(audio_output="null")
    try:
        await player.start()
        await player.play(f"http://127.0.0.1:{server.server_port}/stream?static=true",
                          {"Authorization": "MediaBrowser Token=integration-test"})
        argv = pathlib.Path(f"/proc/{player.process.pid}/cmdline").read_bytes()
        assert b"integration-test" not in argv
        async with asyncio.timeout(6):
            while True:
                event = await player.events.get()
                if event.get("event") == "end-file":
                    assert event["reason"] == "eof"
                    break
        assert received and all(h == "MediaBrowser Token=integration-test" for h in received)
    finally:
        await player.close()
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        thread.join(timeout=2)
