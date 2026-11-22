"""Tests for tools/hero_diagram.py. Run: python -m pytest tools/test_hero_diagram.py"""
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402
import hero_diagram as hd  # noqa: E402

NS = {"s": "http://www.w3.org/2000/svg"}
# The card must stay free of any library name, install hint or release talk.
FORBIDDEN = ("attest", "pypi", "pip install", "open-source", "open source", "github.com/")


def test_flow_svg_is_well_formed_and_self_contained():
    svg = hd.flow_svg()
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.attrib["viewBox"] == "0 0 1200 470"
    assert "<script" not in svg and "onload" not in svg
    assert "http://" not in svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "https://" not in svg and "file://" not in svg and "href" not in svg
    assert svg.count("data:font/woff2;base64,") == 2


def test_flow_svg_animates_with_valid_smil():
    root = ET.fromstring(hd.flow_svg())
    animates = root.findall(".//s:animate", NS)
    assert animates and root.findall(".//s:animateMotion", NS)
    for a in animates + root.findall(".//s:animateMotion", NS):
        assert a.attrib["dur"] == f"{hd.CYCLE}s"
        assert a.attrib["repeatCount"] == "indefinite"
        times = [float(t) for t in a.attrib["keyTimes"].split(";")]
        assert times[0] == 0 and times[-1] == 1, a.attrib
        assert times == sorted(times), a.attrib
        if a.tag.endswith("}animate"):
            assert len(a.attrib["values"].split(";")) == len(times), a.attrib
        else:
            assert len(a.attrib["keyPoints"].split(";")) == len(times)


def test_static_diagram_has_no_animation_and_both_outcomes():
    markup = hd.diagram(False)
    assert "<animate" not in markup
    for text in ("Answer + cited source", "Insufficient evidence", "Confidence gate",
                 "SOC 2 report", "Policy", "Audit report", "Retrieve", "SOC 2 Type II, p. 14"):
        assert text in markup


def test_keyframes_pad_to_the_whole_cycle():
    times, values = hd.keyframes([(0.2, 0), (0.4, 1)])
    assert times == "0.0000;0.2000;0.4000;1.0000"
    assert values == "0;0;1;1"


def test_every_scenario_has_its_own_question_and_caption():
    svg = hd.flow_svg()
    for s in hd.SCENARIOS:
        assert s["question"] in svg and s["caption"] in svg


def test_card_has_headline_subtitle_and_only_the_site_in_the_footer():
    markup = hd.card_html()
    assert hd.HEADLINE == "Evidence-grounded questionnaires"
    assert "Answers cited from your own evidence" in markup
    assert markup.count(hero.SITE) == 1
    assert markup.count("data:font/woff2;base64,") == 2
    assert "fonts.googleapis" not in markup and "file://" not in markup and "<script" not in markup


@pytest.mark.parametrize("make", [hd.flow_svg, hd.card_html])
def test_no_library_name_install_or_dash_characters(make):
    text = make()
    # Skip the base64 font payloads when scanning.
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,", text).lower()
    for word in FORBIDDEN:
        assert word not in text, word
    assert "—" not in text and "–" not in text


def test_html_mode_writes_file_without_a_browser(tmp_path):
    out = tmp_path / "card.html"
    assert hd.main(["--html", str(out)]) == 0
    assert out.read_text().startswith("<!doctype html>")


def test_committed_svg_matches_the_generator():
    assert hd.SVG_OUT.read_text() == hd.flow_svg(), "run: python tools/hero_diagram.py"


def test_post_embeds_the_flow_and_points_at_the_hero():
    post = next((hd.ROOT / "_posts").glob("*evidence-grounded-questionnaires.md"))
    text = post.read_text()
    assert "/assets/img/posts/evidence-grounded-questionnaires-flow.svg)" in text
    assert "path: /assets/img/posts/evidence-grounded-questionnaires-hero.png" in text


def test_png_is_1200_by_630(tmp_path):
    pytest.importorskip("playwright")
    out = tmp_path / "hero.png"
    svg = tmp_path / "flow.svg"
    try:
        hd.main(["--png", str(out), "--svg", str(svg)])
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    data = out.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (1200, 630)
