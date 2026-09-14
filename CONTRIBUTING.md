# Contributing to jellytui

Thank you for your interest in contributing to **jellytui**! We welcome contributions of all kinds: bug reports, documentation improvements, architectural enhancements, and new features.

This document outlines guidelines and workflows to help you get started quickly.

---

## 🛠️ Development Environment Setup

### Prerequisites

Ensure the following tools are installed on your Linux system:
- **Python 3.11+**
- **[mpv](https://mpv.io)** (must be available in your `$PATH`)
- **Git**

### Step-by-Step Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/xHitech/jellytui.git
   cd jellytui
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the package in editable mode with test dependencies:**
   ```bash
   pip install -e '.[test]'
   ```

4. **Verify the installation:**
   ```bash
   jellytui --demo
   ```

---

## 🧪 Running Tests

jellytui includes a test suite covering unit logic, Textual UI pilot navigation, and mpv player IPC lifecycle.

### Running the Standard Test Suite

Run pytest inside your activated virtual environment:

```bash
pytest
```

Or for concise output:

```bash
pytest -q
```

> [!NOTE]
> Tests that interact with mpv use the silent audio sink (`--ao=null`), so they will run silently without interrupting your system's audio playback.

### Running Live Server Integration Tests (Optional)

An optional integration test checks live API responses against a configured, running Jellyfin server. This test is skipped by default.

To execute it with your active server credentials:

```bash
JELLYTUI_LIVE_TEST=1 pytest tests/test_live.py -q
```

---

## 📐 Architecture and Design Principles

When proposing changes, please keep these core design tenets in mind:

1. **Asynchronous Non-blocking UI:**
   - The Textual event loop must never be blocked by synchronous network calls or disk I/O.
   - Use `httpx.AsyncClient` for Jellyfin API queries and Textual's worker system for background operations.

2. **Security and Privacy by Default:**
   - Configuration files in `$XDG_CONFIG_HOME/jellytui/config.toml` must strictly enforce `0600` permissions.
   - User passwords must **never** be persisted to disk.
   - Session tokens must be passed to mpv via memory/IPC sockets, never through visible command-line arguments or environment variables.

3. **Direct Play Fidelity:**
   - Preserve native audio quality by requesting direct static streams whenever supported by the server, avoiding unnecessary transcoding.

4. **Process Lifecycle:**
   - Background mpv instances and temporary Unix domain sockets must always be cleanly terminated upon application exit or error.

---

## 📝 Conventional Commits

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification for clear, meaningful git history.

Format:
```text
<type>(<optional scope>): <short description in imperative mood>
```

### Commit Types

- **`feat:`** A new user-facing feature or capability.
- **`fix:`** A bug fix.
- **`docs:`** Documentation changes, guides, or README updates.
- **`style:`** Code style, formatting, or whitespace adjustments (no production code change).
- **`refactor:`** Code refactoring that neither fixes a bug nor adds a feature.
- **`perf:`** Performance optimization.
- **`test:`** Adding, updating, or correcting tests.
- **`chore:`** Maintenance tasks, packaging, dependencies, or tool configurations.

### Examples

- `feat(player): add replaygain volume adjustment support`
- `fix(lyrics): prevent crash on malformed timestamp tags`
- `docs: clarify Arch Linux installation steps`
- `test(app): add pilot test for search bar escape binding`
- `chore(packaging): update PKGBUILD checksum for v0.1.2`

---

## 🚀 Pull Request Guidelines

1. **Create a descriptive feature branch:**
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Keep changes focused:**
   Keep pull requests focused on a single topic or bug fix. Avoid bundling unrelated refactors with new features.

3. **Validate before submitting:**
   - Run the full test suite (`pytest`) and ensure all tests pass.
   - Verify code formatting and maintain clean code structure.
   - If introducing new functionality, include corresponding unit or pilot tests.

4. **Submit your Pull Request:**
   - Provide a clear title following semantic commit conventions.
   - Detail the motivation, what was changed, and how it was tested.
   - Reference any related issues (e.g., `Fixes #12`).
