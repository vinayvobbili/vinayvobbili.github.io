"""Tests for tools/hero_gate.py, the animated confidence-gate flowchart. Run: python -m pytest tools/test_hero_gate.py"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero_gate as hg  # noqa: E402
from test_hero_scenes import EMPLOYER_ISH, FORBIDDEN  # noqa: E402

NS = {"s": "http://www.w3.org/2000/svg"}
POST = next((hg.ROOT / "_posts").glob("*attestq-evidence-grounded-questionnaires.md"))

# The wording of the original mermaid nodes and edges, one string per rendered line.
LABELS = (
    "question", "embed question", "retrieve top-k", "from evidence store", "best score above", "min_confidence?",
    "insufficient evidence", "NO LLM call", "rerank", "wide window", "LLM drafts a", "cited answer",
    "determination +", "citations + confidence", "yes", "no",
)


def svg_text() -> str:
    return hg.flow_svg()


def visible(text: str) -> str:
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,", text)


def texts(root: ET.Element, group: str | None = None) -> list[str]:
    scope = root if group is None else root.find(f".//s:g[@class='{group}']", NS)
    return ["".join(t.itertext()) for t in scope.findall(".//s:text", NS)]


def test_valid_xml_with_title_desc_and_viewbox():
    root = ET.fromstring(svg_text())
    assert root.attrib["viewBox"] == f"0 0 {hg.W} {hg.H}" and root.attrib["role"] == "img"
    assert root.find("s:title", NS).text == hg.TITLE
    assert len(root.find("s:desc", NS).text) > 100


@pytest.mark.parametrize("group", ["motion", "still"])
def test_every_node_label_of_the_original_is_drawn(group):
    drawn = texts(ET.fromstring(svg_text()), group)
    for label in LABELS:
        assert label in drawn, f"{group}: {label!r} missing from {drawn}"


def test_the_original_logic_is_kept_edge_by_edge():
    """Seven numbered stages, one gate, a yes path and a no path that never reaches the LLM."""
    root = ET.fromstring(svg_text())
    motion = texts(root, "motion")
    assert [t for t in motion if t.isdigit()] == ["1", "2", "3", "4", "5", "6", "7"]
    assert motion.count("yes") == 1 and motion.count("no") == 1
    svg = svg_text()
    # the no path is amber and lands on the insufficient-evidence card; the yes path is green
    assert svg.count('marker-end="url(#ar-amber)"') >= 1 and svg.count('marker-end="url(#ar-green)"') >= 3


def test_no_forbidden_words_or_dashes_or_library_name():
    text = visible(svg_text()).lower()
    for word in FORBIDDEN + ("attestq",):
        assert word not in text, word
    assert "—" not in text and "–" not in text
    for w in EMPLOYER_ISH:
        assert w not in text
    for field in (hg.TITLE, hg.DESC, hg.ALT, hg.CAPTION, *hg.STORY_PRE, *hg.STORY_YES, *hg.STORY_NO, *hg.STORY_STILL):
        low = field.lower()
        assert not any(w in low for w in FORBIDDEN + ("attestq",)), field
        assert "—" not in field and "–" not in field, field


def test_self_contained_smil_no_scripts_no_external_requests():
    svg = svg_text()
    assert "<script" not in svg and "onload" not in svg and "href" not in svg
    assert "https://" not in svg and "file://" not in svg
    assert "http://" not in svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert svg.count("data:font/woff2;base64,") == 2
    assert len(svg) < 250_000


def test_animations_loop_and_keytimes_are_valid():
    root = ET.fromstring(svg_text())
    animates = root.findall(".//s:animate", NS) + root.findall(".//s:animateMotion", NS)
    assert len(animates) > 20
    for a in animates:
        assert a.attrib["repeatCount"] == "indefinite"
        if a.attrib.get("attributeName") == "stroke-dashoffset":
            continue  # the marching dashes on the idle connectors: a 1 s linear loop, no keyTimes
        assert a.attrib["dur"] == f"{hg.CYCLE:g}s"
        times = [float(t) for t in a.attrib["keyTimes"].split(";")]
        assert times[0] == 0 and times[-1] == 1 and times == sorted(times), a.attrib
        if a.tag.endswith("}animate"):
            assert len(a.attrib["values"].split(";")) == len(times), a.attrib
        else:
            assert len(a.attrib["keyPoints"].split(";")) == len(times)


def test_both_outcomes_light_up_once_per_loop_green_first_then_amber():
    a, n = hg.tl(0.0), hg.tl(hg.SCENARIO)
    assert a["decide"] < a["end"] <= hg.SCENARIO <= n["q"] and n["end"] <= hg.CYCLE
    # the yes chain runs in order, and the no card lights in the second half only
    assert a["d_yes"] < a["rerank"] < a["d_rl"] < a["llm"] < a["d_la"] < a["ans"] < a["end"]
    assert n["decide"] < n["ins"] < n["end"]
    assert all(t < hg.SCENARIO for t in a.values()) and all(hg.SCENARIO <= t <= hg.CYCLE for t in n.values())


def test_frame_times_land_on_the_stages_they_are_meant_to_show():
    pre, green, amber = hg.FRAME_TIMES
    a, n = hg.tl(0.0), hg.tl(hg.SCENARIO)
    assert a["q"] < pre < a["score"]
    assert a["ans"] < green < a["end"]
    assert n["ins"] < amber < n["end"]


def test_reduced_motion_still_is_fully_lit_and_has_no_animation():
    root = ET.fromstring(svg_text())
    svg = svg_text()
    assert "prefers-reduced-motion: reduce" in svg and 'class="motion"' in svg and 'class="still"' in svg
    still = root.find(".//s:g[@class='still']", NS)
    assert not still.findall(".//s:animate", NS) and not still.findall(".//s:animateMotion", NS)
    still_markup = ET.tostring(still, encoding="unicode")
    assert 'opacity="0.38"' not in still_markup, "nothing in the still is dimmed"


def test_text_is_never_smaller_than_twelve_and_a_half_pixels():
    for m in re.finditer(r'font-size="([\d.]+)"', visible(svg_text())):
        assert float(m.group(1)) >= 12.5, m.group(0)


def test_caption_and_alt_for_the_post():
    assert hg.CAPTION.startswith("_") and hg.CAPTION.endswith("_") and "\n" not in hg.CAPTION
    assert len(hg.ALT) > 100 and hg.ALT.startswith("Animated flowchart")
    assert "min_confidence" in hg.ALT and '"' not in hg.ALT and "]" not in hg.ALT


def test_post_uses_the_svg_with_alt_and_italic_caption_and_no_mermaid_flowchart_left():
    lines = POST.read_text().splitlines()
    idx = [i for i, ln in enumerate(lines) if f"]({hg.IMG_PATH})" in ln]
    assert len(idx) == 1
    i = idx[0]
    assert lines[i] == f"![{hg.ALT}]({hg.IMG_PATH})"
    assert lines[i + 1] == hg.CAPTION
    # it sits in the confidence-gate section, before the paragraph on the retrieval score
    heading = max(n for n, ln in enumerate(lines[:i]) if ln.startswith("### "))
    assert "confidence gate that runs" in lines[heading]
    assert "GATE{" not in POST.read_text(), "the plain mermaid flowchart is gone"


def test_committed_svg_matches_the_generator():
    assert hg.SVG_OUT.read_text() == hg.flow_svg(), "run: python tools/hero_gate.py"


def test_main_writes_the_svg_without_a_browser(tmp_path):
    out = tmp_path / "flow.svg"
    assert hg.main(["--svg", str(out)]) == 0
    assert out.read_text() == hg.flow_svg()


# --- rendering (needs Playwright and a browser) -----------------------------------

def _need_browser():
    pytest.importorskip("playwright")


def test_no_label_overflows_its_box():
    _need_browser()
    try:
        bad = hg.find_overflow(hg.SVG_OUT)
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert bad == []


def test_reduced_motion_swaps_the_animation_for_the_still():
    _need_browser()
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            shown = {}
            for mode in ("reduce", "no-preference"):
                page = browser.new_page(viewport={"width": hg.W, "height": hg.H}, reduced_motion=mode)
                page.goto(hg.SVG_OUT.resolve().as_uri())
                shown[mode] = page.evaluate(
                    "['.motion', '.still'].map(s => getComputedStyle(document.querySelector(s)).display)")
                page.close()
            browser.close()
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert shown["reduce"] == ["none", "inline"]
    assert shown["no-preference"] == ["inline", "none"]


def test_frames_are_rendered_on_a_dark_and_a_light_page(tmp_path):
    _need_browser()
    try:
        shots = hg.render_frames(hg.SVG_OUT, tmp_path)
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert len(shots) == 2 * len(hg.FRAME_TIMES)
    assert {p.name.split("-")[1] for p in shots} == {"dark", "light"}
    for p in shots:
        assert p.exists() and p.stat().st_size > 20_000
    # frames of different moments differ
    dark = [p.read_bytes() for p in shots if "dark" in p.name]
    assert len(set(dark)) == len(dark)
