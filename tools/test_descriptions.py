"""Post descriptions are what LinkedIn and Google show under the title, and both cut near 150 characters.

Run: python -m pytest tools/test_descriptions.py
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

POSTS = sorted((Path(__file__).resolve().parent.parent / "_posts").glob("*.md"))
MIN_LEN, MAX_LEN = 110, 150


def front_matter(post: Path) -> dict:
    return yaml.safe_load(post.read_text().split("---", 2)[1])


PUBLISHED = [p for p in POSTS if front_matter(p).get("published", True)]


def test_there_are_published_posts():
    assert len(PUBLISHED) >= 16


def test_before_after_report_lists_every_published_post_once():
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import descriptions_report

    text = descriptions_report.report()
    assert text.count("\nBefore (") == len(PUBLISHED)
    assert text.count("\nAfter (") == len(PUBLISHED)


@pytest.mark.parametrize("post", PUBLISHED, ids=lambda p: p.name)
def test_description_fits_a_search_and_share_snippet(post):
    description = front_matter(post)["description"]
    assert MIN_LEN <= len(description) <= MAX_LEN, f"{len(description)} characters"


@pytest.mark.parametrize("post", PUBLISHED, ids=lambda p: p.name)
def test_description_is_one_clean_sentence_run(post):
    description = front_matter(post)["description"]
    assert "\n" not in description
    assert not re.search("[–—]", description), "no em or en dashes"
    assert description.endswith((".", ")")), "ends like a sentence"
    assert not re.search(r"open[- ]source", description, re.I)
