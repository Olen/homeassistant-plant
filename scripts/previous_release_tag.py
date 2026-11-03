#!/usr/bin/env python3
"""Print the tag a release's notes start from.

A stable release starts from the previous stable release, so it lists
everything its betas brought. A beta starts from the tag just before it.
"""

from __future__ import annotations

import argparse
import re
import subprocess

TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-?beta\.?(\d+))?$")
STABLE = float("inf")


def version_key(version: str) -> tuple[int, int, int, float] | None:
    """Return a sort key for a version or tag, or None when it is not one."""
    match = TAG.match(version)
    if match is None:
        return None
    year, month, patch, beta = match.groups()
    beta_number = STABLE if beta is None else int(beta)
    return (int(year), int(month), int(patch), beta_number)


def previous_tag(tags: list[str], version: str) -> str:
    """Return the tag the notes for this version start from."""
    current = version_key(version)
    if current is None:
        raise ValueError(f"Not a release version: {version}")
    is_stable = current[3] == STABLE

    candidates = []
    for tag in tags:
        key = version_key(tag)
        if key is None or key >= current:
            continue
        if is_stable and key[3] != STABLE:
            continue
        candidates.append((key, tag))

    if not candidates:
        raise ValueError(f"No release before {version}")
    return max(candidates)[1]


def main() -> None:
    """Print the starting tag for the version given on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    args = parser.parse_args()
    tags = subprocess.run(
        ["git", "tag"], check=True, capture_output=True, text=True
    ).stdout.split()
    print(previous_tag(tags, args.version))


if __name__ == "__main__":
    main()
