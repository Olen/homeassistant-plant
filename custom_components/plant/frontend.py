"""Serve the bundled flower card and register it as a dashboard resource."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import (
    ResourceStorageCollection,
    ResourceYAMLCollection,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    CARD_VERSION_FILENAME,
    DOMAIN,
    ISSUE_OTHER_FLOWER_CARD,
)

_LOGGER = logging.getLogger(__name__)

WWW = Path(__file__).parent / "www"


def read_card_version(www: Path) -> str:
    """Return the version of the bundled card build."""
    return (www / CARD_VERSION_FILENAME).read_text(encoding="utf-8").strip()


def card_url(version: str) -> str:
    """Return the resource URL for this card version."""
    return f"{CARD_URL_PATH}?v={version}"


def url_path(url: str) -> str:
    """Return a URL without its query string and fragment."""
    return url.split("#", 1)[0].split("?", 1)[0]


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


def update_other_card_issue(hass: HomeAssistant, others: list[str]) -> None:
    """Ask the user to remove other copies of the card, or clear that request."""
    if others:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_OTHER_FLOWER_CARD,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_OTHER_FLOWER_CARD,
            translation_placeholders={"urls": ", ".join(others)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_OTHER_FLOWER_CARD)


async def async_sync_storage_resource(
    hass: HomeAssistant, resources: ResourceStorageCollection, version: str
) -> None:
    """Keep exactly one plant resource, or none while another copy is loaded."""
    await resources.async_get_info()
    items = resources.async_items()
    others = find_other_flower_cards(items)
    update_other_card_issue(hass, others)
    own = find_own_resources(items)

    if others:
        for item in own:
            await resources.async_delete_item(item["id"])
        return

    wanted = {"res_type": "module", "url": card_url(version)}
    if not own:
        await resources.async_create_item(wanted)
        return

    first, *extra = own
    if first["url"] != wanted["url"] or first["type"] != wanted["res_type"]:
        await resources.async_update_item(first["id"], wanted)
    for item in extra:
        await resources.async_delete_item(item["id"])


# The collection awaits listeners inside each write, plant's own included, so passes nest
class StorageResourceSync:
    """Run the storage sync one pass at a time, repeating it for changes made meanwhile."""

    def __init__(
        self, hass: HomeAssistant, resources: ResourceStorageCollection, version: str
    ) -> None:
        """Store what each pass needs."""
        self._hass = hass
        self._resources = resources
        self._version = version
        self._running = False
        self._changed_meanwhile = False

    async def async_run(self, *_args: object) -> None:
        """Sync now, or mark that the running pass must go round again."""
        if self._running:
            self._changed_meanwhile = True
            return

        self._running = True
        try:
            self._changed_meanwhile = True
            while self._changed_meanwhile:
                self._changed_meanwhile = False
                await async_sync_storage_resource(
                    self._hass, self._resources, self._version
                )
        finally:
            self._running = False


def sync_yaml_resource(
    hass: HomeAssistant, resources: ResourceYAMLCollection, version: str
) -> None:
    """Load the card as an extra module unless a copy is already listed."""
    items = resources.async_items()
    others = find_other_flower_cards(items)
    update_other_card_issue(hass, others)
    if not others and not find_own_resources(items):
        add_extra_js_url(hass, card_url(version))


async def async_setup_card(hass: HomeAssistant) -> None:
    """Serve the bundled card and make dashboards load it."""
    version = await async_serve_card(hass)

    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        _LOGGER.warning(
            "Dashboards are not loaded, so the flower card is not registered"
        )
        return

    resources = lovelace.resources
    if isinstance(resources, ResourceStorageCollection):
        sync = StorageResourceSync(hass, resources, version)
        await sync.async_run()
        resources.async_add_listener(sync.async_run)
    elif isinstance(resources, ResourceYAMLCollection):
        sync_yaml_resource(hass, resources, version)
    else:
        raise TypeError(f"Unknown dashboard resource collection: {type(resources)}")
