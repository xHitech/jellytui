"""Interface text is written in English; other languages map English text to translations.

The language comes from JELLYTUI_LANG or `language = "pt"` in config.toml; default English.
"""
import os
from functools import cache

PT = {
    # Library categories and views
    "Library": "Biblioteca",
    "Artists": "Artistas",
    "Albums": "Álbuns",
    "Folders": "Pastas",
    "Playlists": "Playlists",
    "Favorites": "Favoritos",
    "Local queue": "Fila local",
    "Search: {term}": "Busca: {term}",
    "{path} · {count} items": "{path} · {count} itens",
    "Loading library…": "Carregando biblioteca…",
    "Search tracks, artists, and albums… Enter confirms; Escape closes":
        "Buscar músicas, artistas e álbuns… Enter confirma; Escape fecha",
    "Untitled": "Sem título",
    # Track list
    "Name": "Nome",
    "Artist": "Artista",
    "Album": "Álbum",
    "Time": "Tempo",
    "Type": "Tipo",
    "Artist / type": "Artista / tipo",
    "Open": "Abrir",
    "Folder": "Pasta",
    "Playlist": "Playlist",
    # Now playing
    "NOW PLAYING": "TOCANDO AGORA",
    "No track selected\n\nEnter opens an item or plays a track.":
        "Nenhuma música selecionada\n\nEnter abre um item ou reproduz uma faixa.",
    "Ⅱ Paused": "Ⅱ Pausado",
    "▶ Playing": "▶ Tocando",
    "DEMO — no playback": "DEMO — sem reprodução",
    "End of queue": "Fim da fila",
    "Playback failed": "Falha na reprodução",
    "mpv disconnected": "mpv desconectado",
    "{count} channels": "{count} canais",
    # Lyrics
    "LYRICS (LRC)": "LETRA (LRC)",
    "Loading lyrics…": "Carregando letra…",
    "Lyrics not available": "Letra não disponível",
    "Could not load lyrics": "Não foi possível carregar a letra",
    "Unsynced lyrics": "Letra sem sincronização",
    # Help and shortcuts
    "JELLYTUI · HELP": "JELLYTUI · AJUDA",
    "h or Escape closes · ↑/↓ or PageUp/PageDown scrolls help":
        "h ou Escape fecha · ↑/↓ ou PageUp/PageDown rola a ajuda",
    "NAVIGATION": "NAVEGAÇÃO",
    "PLAYBACK": "REPRODUÇÃO",
    "LIBRARY": "BIBLIOTECA",
    "DISPLAY": "EXIBIÇÃO",
    "GENERAL": "GERAL",
    "Up": "Subir",
    "Down": "Descer",
    "Open / play from selection": "Abrir / tocar a partir da seleção",
    "Go back one level": "Voltar um nível",
    "Previous page": "Página anterior",
    "Next page": "Próxima página",
    "First item": "Primeiro item",
    "Last item": "Último item",
    "Next focus": "Próximo foco",
    "Previous focus": "Foco anterior",
    "Search": "Buscar",
    "Next": "Próxima",
    "Previous": "Anterior",
    "Back 5 seconds": "Voltar 5 segundos",
    "Forward 5 seconds": "Avançar 5 segundos",
    "Volume up": "Aumentar volume",
    "Volume down": "Diminuir volume",
    "Add / remove favorite": "Adicionar / remover favorito",
    "Show local queue": "Mostrar fila local",
    "Lyrics": "Letra",
    "Help": "Ajuda",
    "Close help / search": "Fechar ajuda / busca",
    "Quit": "Sair",
    # Errors
    "Use an HTTP(S) URL without credentials, query, or fragment.":
        "Use uma URL HTTP(S) sem credenciais, query ou fragmento.",
    "Config must be a private regular file (chmod 600 {path}).":
        "Configuração exige arquivo regular privado (chmod 600 {path}).",
    "Invalid or unreadable config. Run jellytui --setup.":
        "Configuração inválida ou ilegível. Execute jellytui --setup.",
    "Access denied. Check user/permissions or run jellytui --setup.":
        "Acesso negado. Verifique usuário/permissões ou execute jellytui --setup.",
    "Jellyfin took too long to respond. Check the Tailscale connection and try again.":
        "Jellyfin demorou a responder. Verifique a conexão Tailscale e tente novamente.",
    "Jellyfin returned HTTP {status}.": "Jellyfin retornou HTTP {status}.",
    "Could not connect to Jellyfin. Check the server and Tailscale.":
        "Não foi possível conectar ao Jellyfin. Verifique servidor e Tailscale.",
    "The server returned an invalid response.": "O servidor retornou uma resposta inválida.",
    "Incomplete authentication response.": "Resposta de autenticação incompleta.",
    "Jellyfin did not offer Direct Play. Transcoding is disabled to preserve audio quality.":
        "Jellyfin não disponibilizou Direct Play. Transcodificação está desativada para preservar o áudio.",
    "The server provided a stream from another origin; credentials were not sent.":
        "O servidor forneceu um stream em outra origem; credenciais não foram enviadas.",
    "mpv could not play the track. Check the connection, access, and audio output; n tries the next one.":
        "mpv não conseguiu reproduzir a faixa. Verifique conexão, acesso e saída de áudio; n tenta a próxima.",
    "mpv exited unexpectedly. Restart jellytui to reconnect the player.":
        "mpv encerrou inesperadamente. Reinicie jellytui para reconectar o player.",
    "mpv exited during startup.": "mpv encerrou durante a inicialização.",
    "mpv did not open the IPC socket in time.": "mpv não abriu o socket IPC a tempo.",
    "Could not start mpv/IPC. Check that mpv is installed.":
        "Não foi possível iniciar mpv/IPC. Verifique se mpv está instalado.",
    "mpv could not execute the command.": "mpv não conseguiu executar o comando.",
    "IPC connection to mpv closed.": "Conexão IPC com mpv encerrada.",
    "mpv is not connected.": "mpv não está conectado.",
    "mpv did not respond to the IPC command.": "mpv não respondeu ao comando IPC.",
    # Command line
    "Jellytui — Jellyfin music in the terminal": "Jellytui — música Jellyfin no terminal",
    "Fake library, no connection or playback": "Biblioteca fictícia, sem conexão ou reprodução",
    "Authenticate or change server/user": "Autenticar ou alterar servidor/usuário",
    "Check library and Direct Play negotiation": "Verificar biblioteca e negociação de Direct Play",
    "Also validate real streaming in mpv with silent output":
        "Validar também streaming real no mpv com saída silenciosa",
    "Run --setup in an interactive terminal; the password is typed without echo.":
        "Execute --setup em um terminal interativo; a senha será digitada sem eco.",
    "jellytui — setup (the password will not be saved)": "jellytui — configuração (a senha não será salva)",
    "Server URL [{default}]: ": "URL do servidor [{default}]: ",
    "Username: ": "Usuário: ",
    "Password: ": "Senha: ",
    "Authentication complete. Private config saved to {path}":
        "Autenticação concluída. Configuração privada salva em {path}",
    "Authenticated connection: {artists} artists, {albums} albums, {tracks} tracks.":
        "Conexão autenticada: {artists} artistas, {albums} álbuns, {tracks} faixas.",
    "Negotiated stream: {mode}; {quality}.": "Stream negociado: {mode}; {quality}.",
    "metadata unavailable": "metadados indisponíveis",
    "mpv could not open the Jellyfin track.": "mpv não conseguiu abrir a faixa do Jellyfin.",
    "mpv did not advance through the Jellyfin track.": "mpv não avançou na faixa do Jellyfin.",
    "mpv played {position:.1f}s of the real stream; pause, seek, and volume responded. Silent output (null).":
        "mpv reproduziu {position:.1f}s do stream real; pausa, seek e volume responderam. Saída silenciosa (null).",
    "Timed out opening the real track in mpv.": "Tempo esgotado ao abrir a faixa real no mpv.",
    "mpv not found. On Arch, install it manually: sudo pacman -S mpv":
        "mpv não encontrado. No Arch, instale manualmente: sudo pacman -S mpv",
    "Cancelled.": "Cancelado.",
}

TRANSLATIONS = {"pt": PT}


@cache
def language() -> str:
    """Primary language code, e.g. "pt" for "pt-BR"; resolved once per process."""
    from .config import read_language  # Lazy: config.py itself uses t().
    value = os.environ.get("JELLYTUI_LANG") or read_language() or "en"
    return value.strip().lower().replace("_", "-").split("-")[0]


def t(text: str, **values) -> str:
    """Translate English `text` to the configured language, then fill `{placeholders}`."""
    text = TRANSLATIONS.get(language(), {}).get(text, text)
    return text.format(**values) if values else text
