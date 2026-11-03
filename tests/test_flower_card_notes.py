"""Tests for collecting bundled flower card notes into plant releases."""

from __future__ import annotations

import pytest

from scripts.flower_card_notes import card_section, extract_notes, pr_numbers_in_log

BODY = (
    "Bundles flower card 2026.11.1.\n\n"
    "<!-- flower-card-notes:start -->\n"
    "* Fix A by @Olen in https://github.com/Olen/lovelace-flower-card/pull/390\n"
    "<!-- flower-card-notes:end -->\n"
)


def test_extract_notes() -> None:
    assert extract_notes(BODY) == (
        "* Fix A by @Olen in https://github.com/Olen/lovelace-flower-card/pull/390"
    )


def test_extract_notes_without_markers_raises() -> None:
    with pytest.raises(ValueError):
        extract_notes("no markers here")


def test_card_section_empty() -> None:
    assert card_section([]) == ""


def test_card_section_keeps_order() -> None:
    second = BODY.replace("Fix A", "Fix B").replace("390", "391")

    section = card_section([BODY, second])

    assert section.startswith("## 🌸 Flower card\n\n* Fix A")
    assert section.index("Fix A") < section.index("Fix B")


def test_pr_numbers_in_log() -> None:
    log = (
        "Merge pull request #563 from Olen/flower-card/update\n"
        "Flower card 2026.11.1\n"
        "Fix sensor rename (#561)\n"
        "docs: tweak wording\n"
        "Merge pull request #560 from Olen/feat/bundle-flower-card\n"
    )

    assert pr_numbers_in_log(log) == [560, 561, 563]
