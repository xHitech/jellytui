import argparse
import asyncio
import getpass
import shutil
import sys
from .app import JellyTui
from .config import Config, ConfigError, DEFAULT_SERVER, normalize_server, config_path
from .jellyfin import Jellyfin, JellyfinError
from .player import MpvPlayer, PlayerError
from .i18n import t


async def setup():
    if not sys.stdin.isatty():
        raise ConfigError(t("Run --setup in an interactive terminal; the password is typed without echo."))
    print(t("jellytui — setup (the password will not be saved)"))
    server = normalize_server(input(t("Server URL [{default}]: ", default=DEFAULT_SERVER)).strip() or DEFAULT_SERVER)
    username = input(t("Username: ")).strip()
    password = getpass.getpass(t("Password: "))
    client = Jellyfin(Config(server, "", ""))
    try:
        config = await client.authenticate(username, password)
        password = ""
        config.save()
        print(t("Authentication complete. Private config saved to {path}", path=config_path()))
        return config
    finally:
        password = ""
        await client.close()


async def check(config, play=False):
    api = Jellyfin(config)
    try:
        artists = await api.browse("Artists")
        albums = await api.browse("Albums")
        tracks = await api.all_items(includeItemTypes="Audio", recursive="true")
        print(t("Authenticated connection: {artists} artists, {albums} albums, {tracks} tracks.",
                artists=len(artists), albums=len(albums), tracks=len(tracks)))
        if tracks:
            stream = await api.stream(tracks[0])
            print(t("Negotiated stream: {mode}; {quality}.",
                    mode=stream.mode, quality=stream.quality or t("metadata unavailable")))
            if play:
                player = MpvPlayer(audio_output="null")
                try:
                    await player.start()
                    await player.play(stream.url, stream.headers)
                    async with asyncio.timeout(25):
                        while True:
                            event = await player.events.get()
                            if event.get("event") == "file-loaded":
                                break
                            if event.get("event") in ("end-file", "ipc-disconnected"):
                                raise PlayerError(t("mpv could not open the Jellyfin track."))
                        await asyncio.sleep(2)
                        position = await player.command("get_property", "time-pos")
                        if not position or position <= 0:
                            raise PlayerError(t("mpv did not advance through the Jellyfin track."))
                        await player.pause()
                        await player.seek(5)
                        await player.volume(-5)
                        print(t("mpv played {position:.1f}s of the real stream; pause, seek, and volume responded. "
                                "Silent output (null).", position=position))
                except TimeoutError:
                    raise PlayerError(t("Timed out opening the real track in mpv.")) from None
                finally:
                    await player.close()
    finally:
        await api.close()


def main():
    parser = argparse.ArgumentParser(description=t("Jellytui — Jellyfin music in the terminal"))
    parser.add_argument("--demo", action="store_true", help=t("Fake library, no connection or playback"))
    parser.add_argument("--setup", action="store_true", help=t("Authenticate or change server/user"))
    parser.add_argument("--check", action="store_true", help=t("Check library and Direct Play negotiation"))
    parser.add_argument("--check-play", action="store_true",
                        help=t("Also validate real streaming in mpv with silent output"))
    args = parser.parse_args()
    try:
        if args.demo:
            JellyTui().run()
            return
        if args.setup:
            asyncio.run(setup())
            return
        config = Config.load() or asyncio.run(setup())
        if args.check or args.check_play:
            asyncio.run(check(config, play=args.check_play))
            return
        if not shutil.which("mpv"):
            raise ConfigError(t("mpv not found. On Arch, install it manually: sudo pacman -S mpv"))
        JellyTui(Jellyfin(config), MpvPlayer()).run()
    except (ConfigError, JellyfinError, PlayerError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print("\n" + t("Cancelled."), file=sys.stderr)
        raise SystemExit(130)


if __name__ == "__main__":
    main()
