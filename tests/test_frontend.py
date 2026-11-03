"""Tests for serving and registering the bundled flower card."""

from __future__ import annotations

from pathlib import Path

from custom_components.plant.frontend import (
    card_url,
    find_other_flower_cards,
    find_own_resources,
    read_card_version,
)

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
