"""The reranker post must not read MRR as an average rank.

MRR@10 averages 1/rank of the first right case (0 when it is not in the top 10). 1/0.598 is about 1.7
and 1/0.846 is about 1.18, but those are reciprocals of the mean, not average ranks: the metric hides a
tail of right cases at rank 3 or lower and misses, so "the first right case lands near rank 1.7" is false.

Run: python -m pytest tools/test_rerank_mrr_post.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POST = ROOT / "_posts" / "2026-05-09-three-phases-of-rag-quality.md"
FLOW = ROOT / "assets" / "img" / "posts" / "reranker-mined-pairs-flow.svg"
DRAW = ROOT / "tools" / "hero_draw.py"
SCENES = ROOT / "tools" / "hero_scenes.py"

# The reciprocal-of-MRR readings, as an average rank or a typical rank.
BAD = re.compile(r"rank\s*~\s*1\.\d|near rank 1\.\d|rank 1\.(7|18)\b|1\.18\b|almost always at the top", re.I)


def test_no_file_reads_mrr_as_an_average_rank():
    for path in (POST, FLOW, DRAW, SCENES):
        hit = BAD.search(path.read_text())
        assert hit is None, f"{path.name}: {hit.group(0)!r}"


def test_the_scores_stay_and_the_tail_is_named():
    text = POST.read_text()
    for score in ("0.598", "0.846", "0.626", "0.811", "+41%", "+30%"):
        assert score in text
    prose = " ".join(text.split())
    assert "not an average rank" in prose
    assert "rank 3 or lower" in prose and "missing from the top 10" in prose
