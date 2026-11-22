"""The billing-header post must not call merged upstream work pending, and its update boxes sit under the TL;DR.

The facts come from `gh pr view 541 -R waybarrios/vllm-mlx` (merged 2026-05-28 US Eastern),
`gh pr view 548 ...` (merged 2026-06-11) and `gh issue view 546 ...` (closed, fixed by #548).

Run: python -m pytest tools/test_billing_post.py
"""
import re
from pathlib import Path

POST = (Path(__file__).resolve().parent.parent / "_posts" / "2026-05-09-billing-header-kv-cache.md").read_text()
REPO = "https://github.com/waybarrios/vllm-mlx"


def test_multi_slot_follow_up_is_not_called_pending():
    assert "upstream PR pending" not in POST
    assert "local for now" not in POST


def test_it_links_the_merged_follow_up_pr():
    assert f"{REPO}/pull/541" in POST
    assert "merged 2026-05-28" in POST


def test_it_says_the_json_schema_issue_is_closed_and_why():
    assert f"{REPO}/issues/546" in POST
    assert f"{REPO}/pull/548" in POST
    assert re.search(r"now\s+closed", POST.replace(">", " "))


def test_update_boxes_come_after_the_tldr():
    tldr = POST.index("## TL;DR")
    assert POST.index("**Update (2026-05-14).**") > tldr
    assert POST.index("**Update (2026-05-18)") > tldr
    # and still before the first section after it
    assert POST.index("**Update (2026-05-18)") < POST.index("## The setup")
