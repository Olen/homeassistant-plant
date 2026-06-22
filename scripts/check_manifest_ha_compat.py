#!/usr/bin/env python3
"""Check manifest pins against Home Assistant core's pinned constraints.

For any manifest requirement whose package is also pinned by Home Assistant
core (``homeassistant/package_constraints.txt``), the manifest pin must be
satisfied by HA's version — otherwise HA would override or reject our pin at
runtime. Packages not present in HA core are ignored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# importlib.resources is the standard modern API; this project targets
# Python 3.12+, so the 3.7-backcompat warning does not apply.
from importlib.resources import (  # nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
    files,
)
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "plant"
    / "manifest.json"
)


@dataclass(frozen=True)
class Mismatch:
    """A manifest pin that conflicts with HA core's constraint."""

    requirement: str
    ha_version: str


def parse_constraints(text: str) -> dict[str, str]:
    """Parse ``name==version`` lines from an HA constraints file.

    Comments, blank lines, and any line that is not a single ``==`` pin are
    ignored. Names are canonicalised so lookups are normalisation-insensitive.
    """
    constraints: dict[str, str] = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            req = Requirement(line)
        except Exception:
            continue
        specs = list(req.specifier)
        if len(specs) == 1 and specs[0].operator == "==":
            constraints[canonicalize_name(req.name)] = specs[0].version
    return constraints


def find_constraint_mismatches(
    requirements: list[str],
    constraints: dict[str, str],
) -> list[Mismatch]:
    """Return manifest requirements whose pin conflicts with HA core.

    Only requirements whose canonical name appears in ``constraints`` are
    considered; a conflict is when HA's pinned version does not satisfy our
    specifier.
    """
    mismatches: list[Mismatch] = []
    for raw in requirements:
        req = Requirement(raw)
        ha_version = constraints.get(canonicalize_name(req.name))
        if ha_version is None:
            continue
        if not req.specifier.contains(ha_version, prereleases=True):
            mismatches.append(Mismatch(requirement=raw, ha_version=ha_version))
    return mismatches


def ha_core_constraints() -> dict[str, str] | None:
    """Return HA core's pinned constraints, or ``None`` if unavailable."""
    try:
        text = (
            files("homeassistant")
            .joinpath("package_constraints.txt")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return None
    return parse_constraints(text)


def manifest_requirements(manifest_path: Path = DEFAULT_MANIFEST) -> list[str]:
    """Return the raw requirement strings from the manifest."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return list(manifest.get("requirements", []))
