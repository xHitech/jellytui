**[ English | [Português](README.pt-BR.md) ]**

# jellytui

[![Latest Release](https://img.shields.io/github/v/release/xHitech/jellytui?logo=github&color=brightgreen)](https://github.com/xHitech/jellytui/releases)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&logoColor=white)](https://www.python.org)
[![UI: Textual](https://img.shields.io/badge/UI-Textual-teal.svg)](https://textual.textualize.io)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-lightgrey.svg?logo=linux&logoColor=white)](https://www.kernel.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A terminal music client for Jellyfin, powered by Textual and mpv.

- Direct Play high-fidelity audio
- Synchronized lyrics (LRC)
- Fast, keyboard-driven terminal user interface (TUI)
- Browse Artists, Albums, Folders, Playlists, and Favorites
- Instant search and contextual playback queue
- Native Arch Linux packaging

## Screenshot

<p align="center">
  <img src="assets/screenshot.png" alt="jellytui terminal user interface" width="100%">
</p>

> [!NOTE]
> You can also explore the interface interactively in offline demo mode without a Jellyfin server by running `jellytui --demo`.

## Features

- **Hierarchical and paginated music browsing:** Browse Artists, Albums, Folders, Playlists, and Favorites efficiently without memory overhead.
- **High-fidelity mpv playback:** Audio managed by a dedicated background mpv process, controlled asynchronously via JSON IPC over a private Unix domain socket.
- **Original Direct Play:** Prioritizes the original static stream without arbitrary transcoding, natively preserving formats such as FLAC, MP3, AAC, and Opus.
- **Synchronized lyrics (LRC):** Full support for Jellyfin's official lyrics API (`/Audio/{itemId}/Lyrics`) and standard `.lrc` parsing, with real-time sync locked to mpv's playback clock.
- **Contextual playback queue:** Selecting any track dynamically generates a queue based on the current context (album, artist, playlist, or search results), automatically advancing track by track.
- **Responsive Textual UI:** Flexible layout adapting smoothly to different terminal dimensions, category-aware columns, and a compact Now Playing dashboard.
- **Credential security:** XDG-compliant storage with strict `0600` permissions. Passwords are never saved to disk, and authentication tokens are kept in memory without exposure in process tables (`ps`).

## Installation

### Requirements

- Linux
- Python 3.11+
- [mpv](https://mpv.io) installed and available in your system (`mpv` in `$PATH`)

### Arch Linux (PKGBUILD)

Recommended on Arch Linux to manage dependencies natively via `pacman`:

```bash
git clone https://github.com/xHitech/jellytui
cd jellytui/packaging/arch
makepkg -si
```

### Python / venv (Alternative)

```bash
git clone https://github.com/xHitech/jellytui
cd jellytui
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

To install in development mode with test suite dependencies:

```bash
pip install -e '.[test]'
```

## First Setup

On your first run, configure the server connection using the interactive setup wizard:

```bash
jellytui --setup
```

The wizard will prompt you for:
1. **Server URL** (default: `http://127.0.0.1:8096`)
2. **Username**
3. **Password** (hidden input, used solely for API authentication and never persisted to disk)

After successful authentication, the interface opens automatically. On subsequent runs, simply start:

```bash
jellytui
```

### Utilities and Diagnostics

```bash
jellytui --setup      # Reconfigure server/user credentials and exit
jellytui --check      # Validate authentication, connectivity, and library counts
jellytui --check-play # Test the complete pipeline with mpv using silent null audio
jellytui --demo       # Launch the TUI in offline demo mode (no network required)
```

## Controls

Navigation is entirely keyboard-driven:

| Key | Action |
| --- | --- |
| `↑` / `k`, `↓` / `j` | Move up / down in item list |
| `Enter` | Open folder/category or start playback from selected track |
| `Backspace` | Navigate back one level (preserves previous selection) |
| `PageUp` / `PageDown` | Scroll one page up / down |
| `Home` / `End` | Jump to first / last item |
| `Tab` / `Shift+Tab` | Switch focus between interactive components |
| `Space` | Toggle audio play / pause |
| `n` / `p` | Next / previous track in queue |
| `←` / `→` | Seek backward / forward 5 seconds |
| `+` or `=` / `-` | Increase / decrease volume by 5% (also accepts Numpad `+` and `-`) |
| `/` | Start search across tracks, albums, or artists |
| `Enter` / `Escape` in search | Confirm search / cancel and dismiss search bar |
| `f` | Toggle favorite on selected item |
| `Q` (uppercase) | Display current local playback queue |
| `l` | Toggle synchronized lyrics panel |
| `h` | Open / close help modal with full shortcut reference |
| `Escape` | Close help modal or search bar |
| `q` | Quit application and terminate mpv |

Press `h` at any time to display the in-app help modal with detailed descriptions.

**Queue behavior:** Pressing `Enter` on the third track of a five-item list generates the queue `[track 3, track 4, track 5]`. When a song finishes, it automatically advances to the next track until the queue is exhausted. Browsing other sections of the library does not disrupt active playback until a new item is explicitly triggered.

## Synchronized Lyrics

The client integrates directly with Jellyfin's official lyrics endpoint (`GET /Audio/{itemId}/Lyrics`):

- **Real-time synchronization:** The lyric line cursor tracks mpv's actual playback time (`time-pos`) polled via IPC, avoiding clock drift.
- **Clean display:** Displays the current lyric line highlighted, surrounded by preceding and upcoming lines for context. The widget only redraws when the line or state changes.
- **LRC parser:** Supports server-structured lyrics as well as standard LRC files with fractional seconds and multiple timestamps per line.
- Tracks without cataloged lyrics or timestamps display an informative status without disrupting playback or raising intrusive errors.

## Playback / Direct Play

- **Direct Play:** The client negotiates `POST /Items/{itemId}/PlaybackInfo` requesting direct audio. When Jellyfin allows Direct Play, it streams the original static file (`/Audio/{itemId}/stream?static=true`), preserving native bit depth and sample rate without unnecessary re-encoding.
- If the server requires transcoding, an explanatory notice is displayed in the UI.
- **Decoupled mpv process:** mpv runs in the background with `--no-config --no-video --audio-display=no --idle=yes`. Communication uses JSON IPC over a private temporary Unix socket, cleanly torn down on exit.
- Does not download local audio files permanently or alter server metadata.

## Configuration and Security

Configuration is stored in `$XDG_CONFIG_HOME/jellytui/config.toml` (default: `~/.config/jellytui/config.toml`):

- **Strict permissions:** The configuration file is generated atomically with `0600` permissions (read/write restricted to owner). Existing files with permissive access are rejected at startup.
- **Password privacy:** Passwords entered during `--setup` are used strictly during the login handshake and are never written to disk.
- **Secure tokens:** Session tokens are passed to mpv via in-memory Unix IPC, never exposed in command-line arguments or `ps` output.

## Packaging

The repository provides ready-to-use packaging recipes for Linux distributions in the `packaging/` directory:

- [packaging/arch/PKGBUILD](packaging/arch/PKGBUILD): Official PKGBUILD for stable releases with SHA-256 checksum verification.
- [packaging/arch/.SRCINFO](packaging/arch/.SRCINFO): Synchronized package metadata for Arch Linux.
- [packaging/arch-git/PKGBUILD](packaging/arch-git/PKGBUILD): Development PKGBUILD tracking the latest git `main` branch.

For build and installation instructions, refer to the [Installation](#arch-linux-pkgbuild) section.

## Development and Testing

### Code Architecture

```text
jellytui/
  __init__.py
  __main__.py           CLI entry point and interactive configuration
  app.py                Textual TUI, lifecycle, and navigation
  config.py             Secure TOML configuration management
  jellyfin.py           Asynchronous HTTP client for Jellyfin API
  player.py             mpv process management and Unix IPC control
  models.py             Data models for tracks, albums, and queues
  lyrics.py             LRC synchronized lyrics parser and time search
  controls.py           Central keybinding and action mapping
  demo.py               Mock dataset for offline demonstration mode
  widgets/
    browser.py          Library category navigation
    now_playing.py      Now Playing metadata, progress bar, and status
    track_list.py       Responsive list and table navigation
    lyrics.py           Synchronized lyrics display panel
    help.py             Help modal and shortcut reference
tests/                  Automated test suite (unit, TUI pilot, and mpv)
packaging/              Packaging recipes for Linux distributions (Arch)
assets/                 Visual assets and screenshots
```

### Running Tests

```bash
# Run the complete automated test suite
pytest -q

# Optional live test against an active Jellyfin server
JELLYTUI_LIVE_TEST=1 pytest tests/test_live.py -q
```

- Current status: **59 passed**, **1 skipped** (opt-in live server test).
- Unit tests involving mpv use silent `null` audio output without interfering with system audio devices.

## Limitations

- **Strict music focus:** Does not handle video streams, high-resolution graphic cover art, or traditional desktop GUI elements.
- **In-memory queue:** The playback queue lives within the current active session and does not persist across application restarts.
- **No offline caching:** All tracks are streamed on demand from the Jellyfin server.
- **Existing lyrics only:** Displays lyrics already indexed by Jellyfin; does not query or upload to third-party lyric providers.
- **System mixer:** Volume and audio device routing depend on your Linux sound subsystem (PipeWire / PulseAudio / ALSA).

## License

Distributed under the [MIT](LICENSE) license. See [LICENSE](LICENSE) for details.
