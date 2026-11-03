"""Print the flower card section for a plant release.

Reads the card notes from the bodies of `flower-card` PRs merged since a tag.
"""

from __future__ import annotations

import argparse
import json
import subprocess

NOTES_START = "<!-- flower-card-notes:start -->"
NOTES_END = "<!-- flower-card-notes:end -->"
SECTION_HEADING = "## 🌸 Flower card"


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


def merged_card_pr_bodies(since_tag: str) -> list[str]:
    """Return the bodies of card PRs merged after the tag's commit, oldest first."""
    since = run(["git", "log", "-1", "--format=%cI", since_tag]).strip()
    output = run(
        [
            "gh",
            "pr",
            "list",
            "--label",
            "flower-card",
            "--state",
            "merged",
            "--search",
            f"merged:>{since}",
            "--json",
            "body,mergedAt",
        ]
    )
    prs = sorted(json.loads(output), key=lambda pr: pr["mergedAt"])
    return [pr["body"] for pr in prs]


def main() -> None:
    """Print the section for PRs merged since --since-tag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since-tag", required=True)
    args = parser.parse_args()
    print(card_section(merged_card_pr_bodies(args.since_tag)), end="")


if __name__ == "__main__":
    main()
