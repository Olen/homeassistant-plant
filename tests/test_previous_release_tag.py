"""Tests for choosing the tag a release's notes start from."""

from __future__ import annotations

import pytest

from scripts.previous_release_tag import previous_tag

TAGS = [
    "v2026.8.0",
    "v2026.9.0-beta1",
    "v2026.9.0",
    "v2026.11.0-beta1",
    "v2026.11.0-beta2",
    "v2026.11.0-beta10",
]


def test_stable_starts_from_previous_stable() -> None:
    assert previous_tag(TAGS, "2026.11.0") == "v2026.9.0"


def test_beta_starts_from_previous_tag() -> None:
    assert previous_tag(TAGS, "2026.11.0-beta2") == "v2026.11.0-beta1"
    assert previous_tag(TAGS, "2026.11.0-beta11") == "v2026.11.0-beta10"


def test_first_beta_starts_from_previous_stable() -> None:
    assert previous_tag(TAGS, "2026.11.0-beta1") == "v2026.9.0"


def test_ignores_its_own_tag_and_tags_that_are_not_versions() -> None:
    tags = [*TAGS, "v2026.11.0", "latest", "v1"]
    assert previous_tag(tags, "2026.11.0") == "v2026.9.0"


def test_no_earlier_release_raises() -> None:
    with pytest.raises(ValueError):
        previous_tag(["v2026.11.0"], "2026.11.0")


def test_older_tag_shapes_are_understood() -> None:
    tags = ["2022.5.0", "v2023.1.0-beta.3", "v2023.1.0beta4", "2023.1.0-beta5", "v2023.1.0"]
    assert previous_tag(tags, "2023.2.0") == "v2023.1.0"
    assert previous_tag(tags, "2023.1.0-beta6") == "2023.1.0-beta5"
