"""A stable plant release must not bundle a beta flower card."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.plant.frontend import read_card_version

COMPONENT = Path(__file__).parent.parent / "custom_components" / "plant"


def test_stable_plant_does_not_ship_beta_card() -> None:
    plant = json.loads((COMPONENT / "manifest.json").read_text())["version"]
    card = read_card_version(COMPONENT / "www")

    if "beta" not in plant:
        assert "beta" not in card, f"stable plant {plant} bundles beta card {card}"
