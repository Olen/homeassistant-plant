"""Tests for the manifest <-> HA-core compatibility guard."""

from __future__ import annotations

import pytest

from scripts.check_manifest_ha_compat import (
    Mismatch,
    find_constraint_mismatches,
    ha_core_constraints,
    manifest_requirements,
    parse_constraints,
)


def test_parse_constraints_extracts_exact_pins():
    """Only single == pins are parsed; comments and blanks are ignored."""
    text = (
        "# generated, do not edit\n"
        "aiohttp==3.13.5\n"
        "\n"
        "async-timeout==4.0.3\n"
        "voluptuous>=0.12\n"  # not an exact pin -> skipped
    )
    assert parse_constraints(text) == {
        "aiohttp": "3.13.5",
        "async-timeout": "4.0.3",
    }


def test_no_mismatch_when_package_absent_from_ha():
    """Packages HA core does not pin are ignored."""
    mismatches = find_constraint_mismatches(
        ["some-private-pkg==0.6.1"],
        {"aiohttp": "3.13.5"},
    )
    assert mismatches == []


def test_no_mismatch_when_ha_version_satisfies_specifier():
    """A range that contains HA's pinned version is fine (the async-timeout case)."""
    mismatches = find_constraint_mismatches(
        ["async-timeout>=4.0.2"],
        {"async-timeout": "4.0.3"},
    )
    assert mismatches == []


def test_mismatch_detected_when_pin_conflicts_with_ha():
    """An exact pin that differs from HA's pinned version is flagged."""
    mismatches = find_constraint_mismatches(
        ["async-timeout==4.0.2"],
        {"async-timeout": "4.0.3"},
    )
    assert mismatches == [Mismatch("async-timeout==4.0.2", "4.0.3")]


def test_mismatch_when_range_excludes_ha_version():
    """A range that excludes HA's pinned version is flagged."""
    mismatches = find_constraint_mismatches(
        ["async-timeout<4.0.0"],
        {"async-timeout": "4.0.3"},
    )
    assert mismatches == [Mismatch("async-timeout<4.0.0", "4.0.3")]


def test_mismatch_uses_canonicalized_names():
    """Name normalisation (underscore/case) does not hide a conflict."""
    mismatches = find_constraint_mismatches(
        ["Foo_Bar==1.0"],
        {"foo-bar": "2.0"},
    )
    assert mismatches == [Mismatch("Foo_Bar==1.0", "2.0")]


def test_real_manifest_pins_are_compatible_with_installed_ha():
    """The actual manifest must not conflict with the installed HA core.

    Runs against whatever HA the test matrix installed (the 'latest' leg checks
    the latest HA release). Skips if the constraints file is unavailable.
    """
    constraints = ha_core_constraints()
    if constraints is None:
        pytest.skip("Home Assistant package_constraints.txt not available")
    mismatches = find_constraint_mismatches(manifest_requirements(), constraints)
    assert not mismatches, (
        "manifest.json pins conflict with Home Assistant core constraints: "
        + ", ".join(f"{m.requirement} (HA pins {m.ha_version})" for m in mismatches)
    )
