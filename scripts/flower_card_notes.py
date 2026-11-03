#!/usr/bin/env python3
"""Print the flower card section for a plant release.

Reads the card notes from the bodies of `flower-card` PRs merged in a commit range.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess

NOTES_START = "<!-- flower-card-notes:start -->"
NOTES_END = "<!-- flower-card-notes:end -->"
SECTION_HEADING = "## 🌸 Flower card"
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
    return f"{SECTION_HEADING}\n\n" + "\n\n".join(notes) + "\n"


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
    """Print the section for card PRs between --since-tag and --release-ref."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-tag", required=True)
    parser.add_argument("--release-ref", required=True)
    args = parser.parse_args()
    bodies = released_card_pr_bodies(args.since_tag, args.release_ref)
    print(card_section(bodies), end="")


if __name__ == "__main__":
    main()
