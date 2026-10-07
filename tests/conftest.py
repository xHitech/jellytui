import os

# The interface language is resolved once on import; keep tests independent of the user's config.toml.
os.environ["JELLYTUI_LANG"] = "en"
