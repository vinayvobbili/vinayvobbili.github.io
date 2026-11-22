#!/usr/bin/env python3
"""Write a before/after list of post descriptions: what is committed (HEAD) against the working tree.

    python tools/descriptions_report.py > descriptions-before-after.md
"""
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def description(text: str) -> str | None:
    fm = yaml.safe_load(text.split("---", 2)[1])
    if fm.get("published", True) is False:
        return None
    return " ".join(str(fm["description"]).split())


def committed(path: Path) -> str:
    return subprocess.run(["git", "show", f"HEAD:{path.relative_to(ROOT)}"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout


def report() -> str:
    out = ["# Post descriptions, before and after", "",
           "Target: 110 to 150 characters, readable as a LinkedIn or Google snippet, same facts as the post.", ""]
    for post in sorted((ROOT / "_posts").glob("*.md")):
        before, after = description(committed(post)), description(post.read_text())
        if before is None:
            continue
        title = yaml.safe_load(post.read_text().split("---", 2)[1])["title"]
        out += [f"## {title}", f"File: {post.name}", "",
                f"Before ({len(before)} characters):", before, "",
                f"After ({len(after)} characters):", after, ""]
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout.write(report())
