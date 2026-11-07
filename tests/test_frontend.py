"""Tests for serving and registering the bundled flower card."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.plant import frontend
from custom_components.plant.const import (
    DOMAIN,
    ISSUE_MISSING_FLOWER_CARD,
    ISSUE_OTHER_FLOWER_CARD,
)
from custom_components.plant.frontend import (
    async_setup_card,
    card_url,
    find_other_flower_cards,
    find_own_resources,
    read_card_version,
    resource_file,
    split_by_file,
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


def _missing_issue(hass: HomeAssistant):
    return ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_MISSING_FLOWER_CARD)


@pytest.fixture
def hacs_card_installed(hass: HomeAssistant):
    """Put the separately installed card's file where HACS_URL serves it from."""
    file = Path(hass.config.path("www", "community", "lovelace-flower-card"))
    file.mkdir(parents=True, exist_ok=True)
    (file / "flower-card.js").write_text("// card")
    yield
    shutil.rmtree(hass.config.path("www", "community"))


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


async def test_other_copy_blocks_own_resource(
    hass: HomeAssistant, hacs_card_installed
) -> None:
    resources = await _storage_resources(hass, [HACS_URL, OWN_URL])

    await async_setup_card(hass)

    assert [item["url"] for item in resources.async_items()] == [HACS_URL]
    issue = _issue(hass)
    assert issue is not None
    assert issue.translation_placeholders == {"urls": HACS_URL}


async def test_removing_other_copy_registers_own(
    hass: HomeAssistant, hacs_card_installed
) -> None:
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


async def test_yaml_mode_other_copy_raises_issue(
    hass: HomeAssistant, hacs_card_installed
) -> None:
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


async def test_nested_change_does_not_delete_twice(
    hass: HomeAssistant, hacs_card_installed
) -> None:
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


def test_fragments_are_ignored() -> None:
    items = [
        {"id": "1", "type": "module", "url": "/local/flower-card.js#v1"},
        {"id": "2", "type": "module", "url": "/plant/flower-card.js#v1"},
    ]

    assert find_other_flower_cards(items) == ["/local/flower-card.js#v1"]
    assert [item["id"] for item in find_own_resources(items)] == ["2"]


async def test_leftover_resource_does_not_block_own_card(hass: HomeAssistant) -> None:
    """The card was removed by hand, but its resource is still listed."""
    resources = await _storage_resources(hass, [HACS_URL])

    await async_setup_card(hass)

    assert sorted(item["url"] for item in resources.async_items()) == [
        HACS_URL,
        OWN_URL,
    ]
    assert _issue(hass) is None
    issue = _missing_issue(hass)
    assert issue is not None
    assert issue.translation_placeholders == {"urls": HACS_URL}


async def test_deleting_the_leftover_clears_its_issue(hass: HomeAssistant) -> None:
    resources = await _storage_resources(hass, [HACS_URL])
    await async_setup_card(hass)
    leftover = next(i for i in resources.async_items() if i["url"] == HACS_URL)

    await resources.async_delete_item(leftover["id"])
    await hass.async_block_till_done()

    assert [item["url"] for item in resources.async_items()] == [OWN_URL]
    assert _missing_issue(hass) is None


async def test_yaml_mode_leftover_still_loads_own_card(hass: HomeAssistant) -> None:
    await _setup_lovelace(
        hass,
        {"resource_mode": "yaml", "resources": [{"url": HACS_URL, "type": "module"}]},
    )

    with patch("custom_components.plant.frontend.add_extra_js_url") as add_js:
        await async_setup_card(hass)

    add_js.assert_called_once_with(hass, OWN_URL)
    assert _missing_issue(hass) is not None


def test_resource_file_maps_local_and_hacs_urls(hass: HomeAssistant) -> None:
    assert resource_file(hass, "/local/community/x/flower-card.js?v=1") == Path(
        hass.config.path("www", "community", "x", "flower-card.js")
    )
    assert resource_file(hass, "/hacsfiles/x/flower-card.js") == Path(
        hass.config.path("www", "community", "x", "flower-card.js")
    )


def test_a_remote_card_counts_as_installed(hass: HomeAssistant) -> None:
    url = "https://cdn.example.com/flower-card.js"
    assert resource_file(hass, url) is None
    assert split_by_file(hass, [url]) == ([url], [])


def test_resource_file_decodes_the_path(hass: HomeAssistant) -> None:
    assert resource_file(hass, "/local/old%20cards/flower-card.js") == Path(
        hass.config.path("www", "old cards", "flower-card.js")
    )


async def test_own_resource_deleted_during_the_file_check(hass: HomeAssistant) -> None:
    """Our entry disappears while the file check runs; the sync must not fail."""
    resources = await _storage_resources(hass, [OWN_URL])
    own_id = resources.async_items()[0]["id"]
    real_check = frontend.async_other_copies

    async def delete_own_meanwhile(hass, items):
        if own_id in resources.data:
            resources.data.pop(own_id)
        return await real_check(hass, items)

    with patch.object(frontend, "async_other_copies", delete_own_meanwhile):
        await async_setup_card(hass)

    assert [item["url"] for item in resources.async_items()] == [OWN_URL]
