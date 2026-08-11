"""Source adapters registry.

The registry maps source names to adapter classes; enabled/disabled state is
decided by config/sources.yaml at pipeline time, never hardcoded here.
"""
from .base import AccessPolicy, ParsedPlayer, SourceError  # noqa: F401
from .cs2settings import CS2SettingsSource
from .proconfig import ProConfigSource
from .prosettings import ProSettingsSource

SOURCE_CLASSES = {
    "cs2settings": CS2SettingsSource,
    "prosettings": ProSettingsSource,
    "proconfig": ProConfigSource,
}


def get_source(name: str):
    cls = SOURCE_CLASSES.get(name)
    if cls is None:
        raise SourceError(f"unknown source: {name}")
    return cls()


def list_sources() -> list[str]:
    return sorted(SOURCE_CLASSES)
