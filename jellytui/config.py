"""Configuração local: nunca persiste a senha."""
import json
import os
import tempfile
import tomllib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from .i18n import t

DEFAULT_SERVER = "http://127.0.0.1:8096"


class ConfigError(Exception):
    pass


def config_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "jellytui" / "config.toml"


def read_language(path: Path | None = None) -> str | None:
    """Optional `language` key from config.toml; readable even without a login."""
    try:
        value = tomllib.loads((path or config_path()).read_text()).get("language")
    except (OSError, ValueError):
        return None
    return value if isinstance(value, str) and value.strip() else None


def normalize_server(server: str) -> str:
    server = server.strip().rstrip("/")
    parts = urlsplit(server)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ConfigError(t("Use an HTTP(S) URL without credentials, query, or fragment."))
    return server


@dataclass
class Config:
    server: str
    user_id: str
    token: str = field(repr=False)
    device_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def load(cls, path: Path | None = None):
        path = path or config_path()
        if not path.exists():
            return None
        try:
            if path.is_symlink() or path.stat().st_mode & 0o077:
                raise ConfigError(t("Config must be a private regular file (chmod 600 {path}).", path=path))
            data = tomllib.loads(path.read_text())
            result = cls(**{key: data[key] for key in ("server", "user_id", "token", "device_id")})
            result.server = normalize_server(result.server)
            if not all(isinstance(v, str) and v for v in (result.user_id, result.token, result.device_id)):
                raise ValueError
            if any(c in result.token + result.device_id for c in '\r\n"'):
                raise ValueError
            return result
        except (OSError, ValueError, KeyError, TypeError):
            raise ConfigError(t("Invalid or unreadable config. Run jellytui --setup.")) from None

    def save(self, path: Path | None = None):
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.server = normalize_server(self.server)
        content = "".join(f"{key} = {json.dumps(getattr(self, key), ensure_ascii=False)}\n"
                          for key in ("server", "user_id", "token", "device_id"))
        # The language is not part of the login; keep it when --setup rewrites the file.
        if language := read_language(path):
            content += f"language = {json.dumps(language, ensure_ascii=False)}\n"
        fd, temp = tempfile.mkstemp(prefix=".config-", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as file:
                os.fchmod(file.fileno(), 0o600)
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
