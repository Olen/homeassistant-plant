"""Serve the bundled flower card and register it as a dashboard resource."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL_PATH, CARD_VERSION_FILENAME

WWW = Path(__file__).parent / "www"


def read_card_version(www: Path) -> str:
    """Return the version of the bundled card build."""
    return (www / CARD_VERSION_FILENAME).read_text(encoding="utf-8").strip()


def card_url(version: str) -> str:
    """Return the resource URL for this card version."""
    return f"{CARD_URL_PATH}?v={version}"


def url_path(url: str) -> str:
    """Return a URL without its query string."""
    return url.split("?", 1)[0]


def find_other_flower_cards(items: Iterable[dict]) -> list[str]:
    """Return the URLs of flower card resources that plant does not own."""
    others = []
    for item in items:
        path = url_path(item["url"])
        filename = path.rsplit("/", 1)[-1]
        if filename == CARD_FILENAME and path != CARD_URL_PATH:
            others.append(item["url"])
    return others


def find_own_resources(items: Iterable[dict]) -> list[dict]:
    """Return the resources that point at plant's bundled card."""
    return [item for item in items if url_path(item["url"]) == CARD_URL_PATH]


async def async_serve_card(hass: HomeAssistant) -> str:
    """Serve the bundled card and return its version."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(WWW / CARD_FILENAME), cache_headers=False)]
    )
    return await hass.async_add_executor_job(read_card_version, WWW)
