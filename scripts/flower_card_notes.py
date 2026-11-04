#!/usr/bin/env python3
"""Print plant release notes with the flower card section added.

Reads the card notes from the bodies of `flower-card` PRs merged in a commit range.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

NOTES_START = "<!-- flower-card-notes:start -->"
NOTES_END = "<!-- flower-card-notes:end -->"
SECTION_HEADING = "## 🌸 Flower card"
# GitHub's generated notes end with these, in this order; the card section goes above them
TRAILING_PARTS = ("## New Contributors", "**Full Changelog**")
CARD_LABEL = "flower-card"
MERGE_SUBJECT = re.compile(r"^Merge pull request #(\d+) ")
SQUASH_SUBJECT = re.compile(r"\(#(\d+)\)$")


def extract_notes(pr_body: str) -> str:
    """Return the card notes between the markers in a PR body."""
    start = pr_body.find(NOTES_START)
    end = pr_body.find(NOTES_END)
    if start == -1 or end == -1:
        raise ValueError("PR body has no flower card notes markers")
    return pr_body[start + len(NOTES_START) : end].strip()


def card_section(pr_bodies: list[str]) -> str:
    """Return the release-notes section for these card PRs, oldest first."""
    if not pr_bodies:
        return ""
    notes = [extract_notes(body) for body in pr_bodies]
    return f"{SECTION_HEADING}\n\n" + "\n".join(notes) + "\n"


def add_card_section(release_notes: str, section: str) -> str:
    """Return the release notes with the card section above their trailing parts."""
    if not section:
        return release_notes
    for part in TRAILING_PARTS:
        match = re.search(rf"^{re.escape(part)}", release_notes, re.MULTILINE)
        if match:
            position = match.start()
            return release_notes[:position] + section + "\n" + release_notes[position:]
    return release_notes.rstrip("\n") + "\n\n" + section


def run(command: list[str]) -> str:
    """Run a command and return its stdout."""
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def pr_numbers_in_log(log: str) -> list[int]:
    """Return the PR or issue numbers named by merge or squash commit subjects, ascending."""
    numbers = set()
    for subject in log.splitlines():
        merge = MERGE_SUBJECT.match(subject)
        squash = SQUASH_SUBJECT.search(subject)
        if merge:
            numbers.add(int(merge.group(1)))
        elif squash:
            numbers.add(int(squash.group(1)))
    return sorted(numbers)


def released_card_pr_bodies(since_tag: str, release_ref: str) -> list[str]:
    """Return the bodies of card PRs merged between the tag and the release, oldest first."""
    log = run(["git", "log", "--format=%s", f"{since_tag}..{release_ref}"])
    bodies = []
    for number in pr_numbers_in_log(log):
        # The issues API also answers for issue numbers that a commit subject names
        item = json.loads(
            run(["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}"])
        )
        labels = [label["name"] for label in item["labels"]]
        if "pull_request" in item and CARD_LABEL in labels:
            bodies.append(item["body"])
    return bodies


def main() -> None:
    """Print --release-notes with the card PRs between --since-tag and --release-ref."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-tag", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--release-notes", required=True, help="generated notes file")
    args = parser.parse_args()
    release_notes = Path(args.release_notes).read_text(encoding="utf-8")
    bodies = released_card_pr_bodies(args.since_tag, args.release_ref)
    print(add_card_section(release_notes, card_section(bodies)), end="")


if __name__ == "__main__":
    main()
