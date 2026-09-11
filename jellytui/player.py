"""Processo mpv privado, controlado exclusivamente por JSON IPC Unix."""
import asyncio
import json
import tempfile
from pathlib import Path
from contextlib import suppress


class PlayerError(Exception):
    pass


class MpvPlayer:
    def __init__(self, *, audio_output=None):
        self.audio_output = audio_output
        self.process = None
        self.writer = None
        self.reader_task = None
        self.temp = None
        self.pending = {}
        self.sequence = 0
        self.events = asyncio.Queue()
        self.properties = {"time-pos": 0, "duration": 0, "pause": True, "volume": 70, "idle-active": True}
        self.closed = False
        self.entry_id = None

    async def start(self):
        if self.writer:
            return
        self.temp = tempfile.TemporaryDirectory(prefix="jellytui-")
        socket = str(Path(self.temp.name) / "mpv.sock")
        args = ["mpv", "--no-config", "--no-video", "--audio-display=no", "--idle=yes", "--pause=yes",
                "--no-terminal", "--really-quiet", "--volume=70", "--volume-max=100", "--ytdl=no",
                "--input-default-bindings=no", f"--input-ipc-server={socket}"]
        if self.audio_output:
            args.append(f"--ao={self.audio_output}")
        try:
            self.process = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.DEVNULL,
                                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            for _ in range(100):
                if self.process.returncode is not None:
                    raise PlayerError("mpv encerrou durante a inicialização.")
                try:
                    reader, self.writer = await asyncio.open_unix_connection(socket, limit=2**20)
                    break
                except (FileNotFoundError, ConnectionRefusedError):
                    await asyncio.sleep(0.05)
            else:
                raise PlayerError("mpv não abriu o socket IPC a tempo.")
            self.reader_task = asyncio.create_task(self._read(reader))
            for index, name in enumerate(self.properties):
                await self.command("observe_property", index, name)
        except (OSError, PlayerError):
            await self.close()
            raise PlayerError("Não foi possível iniciar mpv/IPC. Verifique se mpv está instalado.") from None

    async def _read(self, reader):
        try:
            while line := await reader.readline():
                message = json.loads(line)
                request_id = message.get("request_id")
                if request_id in self.pending:
                    future = self.pending[request_id]
                    if not future.done():
                        if message.get("error") == "success":
                            future.set_result(message.get("data"))
                        else:
                            future.set_exception(PlayerError("mpv não conseguiu executar o comando."))
                elif message.get("event") == "property-change":
                    self.properties[message["name"]] = message.get("data")
                elif message.get("event"):
                    await self.events.put(message)
        except (OSError, ValueError, asyncio.LimitOverrunError):
            pass
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(PlayerError("Conexão IPC com mpv encerrada."))
            if not self.closed:
                await self.events.put({"event": "ipc-disconnected"})

    async def command(self, *args):
        if not self.writer or self.writer.is_closing():
            raise PlayerError("mpv não está conectado.")
        self.sequence += 1
        request_id = self.sequence
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        try:
            self.writer.write((json.dumps({"command": args, "request_id": request_id}) + "\n").encode())
            await self.writer.drain()
            return await asyncio.wait_for(future, 5)
        except (OSError, asyncio.TimeoutError):
            raise PlayerError("mpv não respondeu ao comando IPC.") from None
        finally:
            self.pending.pop(request_id, None)

    async def play(self, url, headers=None):
        # Segredos trafegam só no socket privado, nunca em argv ou logs.
        await self.command("set_property", "http-header-fields", [f"{k}: {v}" for k, v in (headers or {}).items()])
        await self.command("loadfile", url, "replace")
        playlist = await self.command("get_property", "playlist")
        self.entry_id = playlist[0]["id"] if playlist else None
        await self.command("set_property", "pause", False)
        self.properties.update({"time-pos": 0, "duration": 0, "pause": False})

    async def pause(self):
        await self.command("cycle", "pause")

    async def seek(self, offset):
        await self.command("seek", offset, "relative+exact")
        self.properties["time-pos"] = await self.command("get_property", "time-pos")

    async def volume(self, offset):
        value = max(0, min(100, (self.properties.get("volume") or 0) + offset))
        await self.command("set_property", "volume", value)

    async def close(self):
        self.closed = True
        if self.writer:
            with suppress(PlayerError, OSError):
                await self.command("quit")
            self.writer.close()
            with suppress(OSError):
                await self.writer.wait_closed()
            self.writer = None
        if self.process:
            try:
                await asyncio.wait_for(self.process.wait(), 2)
            except asyncio.TimeoutError:
                with suppress(ProcessLookupError):
                    self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), 2)
                except asyncio.TimeoutError:
                    with suppress(ProcessLookupError):
                        self.process.kill()
                    await self.process.wait()
        if self.reader_task:
            self.reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.reader_task
        if self.temp:
            self.temp.cleanup()
