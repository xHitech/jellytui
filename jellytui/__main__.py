import argparse
import asyncio
import getpass
import shutil
import sys
from .app import JellyTui
from .config import Config, ConfigError, DEFAULT_SERVER, normalize_server, config_path
from .jellyfin import Jellyfin, JellyfinError
from .player import MpvPlayer, PlayerError


async def setup():
    if not sys.stdin.isatty():
        raise ConfigError("Execute --setup em um terminal interativo; a senha será digitada sem eco.")
    print("jellytui — configuração (a senha não será salva)")
    server = normalize_server(input(f"URL do servidor [{DEFAULT_SERVER}]: ").strip() or DEFAULT_SERVER)
    username = input("Usuário: ").strip()
    password = getpass.getpass("Senha: ")
    client = Jellyfin(Config(server, "", ""))
    try:
        config = await client.authenticate(username, password)
        password = ""
        config.save()
        print(f"Autenticação concluída. Configuração privada salva em {config_path()}")
        return config
    finally:
        password = ""
        await client.close()


async def check(config, play=False):
    api = Jellyfin(config)
    try:
        artists = await api.browse("Artistas")
        albums = await api.browse("Álbuns")
        tracks = await api.all_items(includeItemTypes="Audio", recursive="true")
        print(f"Conexão autenticada: {len(artists)} artistas, {len(albums)} álbuns, {len(tracks)} faixas.")
        if tracks:
            stream = await api.stream(tracks[0])
            print(f"Stream negociado: {stream.mode}; {stream.quality or 'metadados indisponíveis'}.")
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
                                raise PlayerError("mpv não conseguiu abrir a faixa do Jellyfin.")
                        await asyncio.sleep(2)
                        position = await player.command("get_property", "time-pos")
                        if not position or position <= 0:
                            raise PlayerError("mpv não avançou na faixa do Jellyfin.")
                        await player.pause()
                        await player.seek(5)
                        await player.volume(-5)
                        print(f"mpv reproduziu {position:.1f}s do stream real; pausa, seek e volume responderam. Saída silenciosa (null).")
                except TimeoutError:
                    raise PlayerError("Tempo esgotado ao abrir a faixa real no mpv.") from None
                finally:
                    await player.close()
    finally:
        await api.close()


def main():
    parser = argparse.ArgumentParser(description="Jellytui — música Jellyfin no terminal")
    parser.add_argument("--demo", action="store_true", help="Biblioteca fictícia, sem conexão ou reprodução")
    parser.add_argument("--setup", action="store_true", help="Autenticar ou alterar servidor/usuário")
    parser.add_argument("--check", action="store_true", help="Verificar biblioteca e negociação de Direct Play")
    parser.add_argument("--check-play", action="store_true", help="Validar também streaming real no mpv com saída silenciosa")
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
            raise ConfigError("mpv não encontrado. No Arch, instale manualmente: sudo pacman -S mpv")
        JellyTui(Jellyfin(config), MpvPlayer()).run()
    except (ConfigError, JellyfinError, PlayerError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.", file=sys.stderr)
        raise SystemExit(130)


if __name__ == "__main__":
    main()
