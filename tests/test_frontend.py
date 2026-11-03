"""Tests for serving and registering the bundled flower card."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.plant.const import DOMAIN, ISSUE_OTHER_FLOWER_CARD
from custom_components.plant.frontend import (
    async_setup_card,
    card_url,
    find_other_flower_cards,
    find_own_resources,
    read_card_version,
)

VERSION = "2026.11.0"
OWN_URL = "/plant/flower-card.js?v=2026.11.0"
HACS_URL = "/hacsfiles/lovelace-flower-card/flower-card.js?hacstag=123"

WWW = Path(__file__).parent.parent / "custom_components" / "plant" / "www"


def test_card_url_carries_version() -> None:
    assert card_url("2026.11.0") == "/plant/flower-card.js?v=2026.11.0"


def test_find_other_flower_cards() -> None:
    items = [
        {
            "id": "1",
            "type": "module",
            "url": "/hacsfiles/lovelace-flower-card/flower-card.js?hacstag=123",
        },
        {"id": "2", "type": "module", "url": "/local/flower-card.js"},
        {"id": "3", "type": "module", "url": "/plant/flower-card.js?v=2026.11.0"},
        {
            "id": "4",
            "type": "module",
            "url": "/hacsfiles/mini-graph-card/mini-graph-card-bundle.js",
        },
        {"id": "5", "type": "module", "url": "/local/my-flower-card.js"},
    ]

    assert find_other_flower_cards(items) == [
        "/hacsfiles/lovelace-flower-card/flower-card.js?hacstag=123",
        "/local/flower-card.js",
    ]
    assert [item["id"] for item in find_own_resources(items)] == ["3"]


def test_read_card_version(tmp_path: Path) -> None:
    (tmp_path / "flower-card.version").write_text("2026.11.0\n")

    assert read_card_version(tmp_path) == "2026.11.0"


def test_bundled_files_exist() -> None:
    assert (WWW / "flower-card.js").stat().st_size > 0
    assert read_card_version(WWW)


@pytest.fixture(autouse=True)
def pin_card_version():
    """Keep the tests independent of the bundled card's version."""
    with patch(
        "custom_components.plant.frontend.read_card_version", return_value=VERSION
    ):
        yield


async def _setup_lovelace(hass: HomeAssistant, lovelace_config: dict) -> None:
    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "lovelace", {"lovelace": lovelace_config})


async def _storage_resources(hass: HomeAssistant, urls: list[str]):
    await _setup_lovelace(hass, {})
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    for url in urls:
        await resources.async_create_item({"res_type": "module", "url": url})
    return resources


def _issue(hass: HomeAssistant):
    return ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_OTHER_FLOWER_CARD)


async def test_creates_own_resource(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, [])

    await async_setup_card(hass)

    items = resources.async_items()
    assert [(item["type"], item["url"]) for item in items] == [("module", OWN_URL)]
    assert _issue(hass) is None


async def test_version_change_updates_in_place(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, ["/plant/flower-card.js?v=2026.10.1"])
    old_id = resources.async_items()[0]["id"]

    await async_setup_card(hass)

    items = resources.async_items()
    assert [(item["id"], item["url"]) for item in items] == [(old_id, OWN_URL)]


async def test_duplicate_own_resources_collapse_to_one(hass: HomeAssistant) -> None:
    resources = await _storage_resources(
        hass, ["/plant/flower-card.js?v=2026.10.1", "/plant/flower-card.js?v=2026.10.0"]
    )

    await async_setup_card(hass)

    assert [item["url"] for item in resources.async_items()] == [OWN_URL]


async def test_other_copy_blocks_own_resource(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, [HACS_URL, OWN_URL])

    await async_setup_card(hass)

    assert [item["url"] for item in resources.async_items()] == [HACS_URL]
    issue = _issue(hass)
    assert issue is not None
    assert issue.translation_placeholders == {"urls": HACS_URL}


async def test_removing_other_copy_registers_own(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, [HACS_URL])
    await async_setup_card(hass)
    hacs_id = resources.async_items()[0]["id"]

    await resources.async_delete_item(hacs_id)
    await hass.async_block_till_done()

    assert [item["url"] for item in resources.async_items()] == [OWN_URL]
    assert _issue(hass) is None


async def test_yaml_mode_adds_extra_module(hass: HomeAssistant) -> None:
    await _setup_lovelace(hass, {"resource_mode": "yaml", "resources": []})

    with patch("custom_components.plant.frontend.add_extra_js_url") as add_js:
        await async_setup_card(hass)

    add_js.assert_called_once_with(hass, OWN_URL)
    assert _issue(hass) is None


async def test_yaml_mode_other_copy_raises_issue(hass: HomeAssistant) -> None:
    await _setup_lovelace(
        hass,
        {
            "resource_mode": "yaml",
            "resources": [{"url": HACS_URL, "type": "module"}],
        },
    )

    with patch("custom_components.plant.frontend.add_extra_js_url") as add_js:
        await async_setup_card(hass)

    add_js.assert_not_called()
    assert _issue(hass) is not None


async def test_unknown_resource_collection_raises(hass: HomeAssistant) -> None:
    await _setup_lovelace(hass, {})
    hass.data[LOVELACE_DATA].resources = object()

    with pytest.raises(TypeError):
        await async_setup_card(hass)


async def test_wrong_type_is_restored(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, [])
    await async_setup_card(hass)
    own_id = resources.async_items()[0]["id"]

    await resources.async_update_item(own_id, {"res_type": "css"})
    await hass.async_block_till_done()

    assert [(item["type"], item["url"]) for item in resources.async_items()] == [
        ("module", OWN_URL)
    ]


async def test_nested_change_does_not_delete_twice(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, [HACS_URL])
    await async_setup_card(hass)
    # Two own resources appear at once, without a change notification
    for item_id in ("own1", "own2"):
        resources.data[item_id] = {"id": item_id, "type": "module", "url": OWN_URL}

    await resources.async_create_item({"res_type": "css", "url": "/local/theme.css"})
    await hass.async_block_till_done()

    assert sorted(item["url"] for item in resources.async_items()) == [
        HACS_URL,
        "/local/theme.css",
    ]


async def test_yaml_mode_own_url_listed_is_not_injected(hass: HomeAssistant) -> None:
    await _setup_lovelace(
        hass,
        {"resource_mode": "yaml", "resources": [{"url": OWN_URL, "type": "module"}]},
    )

    with patch("custom_components.plant.frontend.add_extra_js_url") as add_js:
        await async_setup_card(hass)

    add_js.assert_not_called()
    assert _issue(hass) is None
