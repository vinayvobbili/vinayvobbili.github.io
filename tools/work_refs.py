#!/usr/bin/env python3
"""List every place a post or page talks about the day job.

Posts here describe tools by their features. Lines that tie a tool to an
employer's systems ("runs in production", "our SOC", ticket counts, named
internal platforms) are worth a second look before publishing. This prints
each hit with its file, line and surrounding words; it doesn't change files.

    python tools/work_refs.py                      # every post and page
    python tools/work_refs.py _posts/2026-10-10-*.md
    python tools/work_refs.py --summary            # counts per file only
    python tools/work_refs.py --repo ../attestq --ref origin/main   # another repo, as pushed

Exit status is 1 when anything matched, so it can gate a pre-publish check.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each pattern is one kind of reference; the label says why it matched.
PATTERNS: list[tuple[str, str]] = [
    ("production", r"\bproduction\b|\bin prod\b"),
    ("day job", r"\bat work\b|\bmy (?:day )?job\b|\bemployer\b|\bmy (?:team|org|company)\b|\bcolleague"),
    ("our ...", r"\bour (?:soc|team|analysts|tenant|internal|org|company|environment|analysts)\b"),
    ("internal", r"\binternal (?:tools?|platforms?|gateway|corpus|systems?|policy|policies|ai)\b"),
    ("work systems", r"\b(?:xsoar|webex|servicenow|lab[ -]?vm|reverse tunnel|ssh tunnel)\b"),
    ("ticket data", r"\btickets?\b|\bhistorical cases\b|\b\d[\d,.]*K?\+? (?:real )?(?:cases|tickets|alerts|incidents)\b"),
    ("real data", r"\breal (?:alerts|cases|tickets|incidents|questionnaires|analysts|load|traffic)\b"),
    ("org type", r"\bcorporate\b|\bfortune \d+\b|\binsurer\b|\bfinancial services\b"),
    # Says the published code was taken out of a work system.
    ("origin", r"\bextract(?:ed|ing)? (?:it|that|the|them|from)\b|\bpulled (?:them|it|the \w+) out\b"
               r"|\bcame (?:directly )?out of\b|\bdistilled (?:from|kernel)\b|\blifted (?:from|out)\b"),
    ("internal names", r"\bpokedex\b|\bleadership\b|\bregional team\b|\bcase #?\d{4,}\b|\bhosted-to-local\b"),
]
COMPILED = [(label, re.compile(rx, re.IGNORECASE)) for label, rx in PATTERNS]

DEFAULT_GLOBS = ["_posts/*.md", "_tabs/*.md", "*/index.html"]

# What --repo reads: prose, code, config and web files. Binaries and lockfiles are skipped.
TEXT_SUFFIXES = {
    ".md", ".markdown", ".rst", ".txt", ".html", ".htm", ".py", ".js", ".ts", ".json",
    ".toml", ".yaml", ".yml", ".cfg", ".ini", ".sh", ".css", ".xml", ".csv",
}
SKIP_NAMES = {"package-lock.json", "uv.lock", "poetry.lock", "Gemfile.lock"}


def repo_files(repo: Path, ref: str = "HEAD") -> list[tuple[str, str]]:
    """(path, text) for every tracked text file at `ref`, exactly as committed."""
    names = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", ref],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    out = []
    for name in names:
        p = Path(name)
        if p.suffix.lower() not in TEXT_SUFFIXES or p.name in SKIP_NAMES:
            continue
        blob = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{name}"], check=True, capture_output=True,
        ).stdout
        out.append((name, blob.decode("utf-8", errors="replace")))
    return out


def default_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for pattern in DEFAULT_GLOBS:
        files.extend(p for p in sorted(root.glob(pattern)) if not p.parts[len(root.parts)].startswith((".", "_site")))
    return files


def scan(text: str) -> list[tuple[int, str, str]]:
    """(line number, label, snippet) for every match, in file order."""
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for label, rx in COMPILED:
            for m in rx.finditer(line):
                start, end = max(0, m.start() - 70), min(len(line), m.end() + 70)
                snippet = line[start:end].strip()
                hits.append((n, label, ("…" if start else "") + snippet + ("…" if end < len(line) else "")))
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--summary", action="store_true", help="only print hit counts per file")
    ap.add_argument("--repo", type=Path, help="scan another git repo's tracked text files instead")
    ap.add_argument("--ref", default="HEAD", help="with --repo: the commit or branch to read (default HEAD)")
    args = ap.parse_args(argv)

    if args.repo:
        sources = repo_files(args.repo, args.ref)
    else:
        sources = []
        for path in args.files or default_files():
            rel = path.resolve().relative_to(ROOT) if path.resolve().is_relative_to(ROOT) else path
            sources.append((str(rel), path.read_text(errors="replace")))

    total = 0
    for rel, text in sources:
        hits = scan(text)
        if not hits:
            continue
        total += len(hits)
        if args.summary:
            print(f"{len(hits):4d}  {rel}")
            continue
        print(f"\n== {rel} ({len(hits)})")
        for n, label, snippet in hits:
            print(f"  {n:4d}  [{label}]  {snippet}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
