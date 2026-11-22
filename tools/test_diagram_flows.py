"""Tests for tools/diagram_flows.py and tools/diagram_specs.py, the animated post diagrams. Run: python -m pytest tools/test_diagram_flows.py"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagram_flows as df  # noqa: E402
import font_metrics as fm  # noqa: E402
from diagram_specs import SPECS  # noqa: E402
from test_hero_scenes import EMPLOYER_ISH, FORBIDDEN, POSTS, PRIVATE, published  # noqa: E402

NS = {"s": "http://www.w3.org/2000/svg"}
IDS = [s.slug for s in SPECS]
SVGS = {s.slug: df.flow_svg(s) for s in SPECS}


def spec_of(slug: str) -> df.Spec:
    return next(s for s in SPECS if s.slug == slug)


def visible(text: str) -> str:
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,", text)


def texts(root: ET.Element, group: str) -> list[str]:
    scope = root.find(f".//s:g[@class='{group}']", NS)
    return ["".join(t.itertext()) for t in scope.findall(".//s:text", NS)]


# --- coverage -------------------------------------------------------------------------------

def test_every_published_post_mermaid_block_has_a_spec():
    """13 diagrams in 11 published posts; the questionnaire post's flowchart is drawn by tools/hero_gate.py."""
    assert len(SPECS) == 13
    assert len({s.slug for s in SPECS}) == 13
    for post in POSTS:
        if published(post):
            assert "```mermaid" not in post.read_text(), f"{post.name} still has a plain mermaid block"


def test_unpublished_posts_are_left_alone():
    for post in POSTS:
        if not published(post):
            assert not any(s.post in post.name for s in SPECS), post.name


def test_slugs_are_descriptive_and_name_no_private_project():
    for s in SPECS:
        assert s.slug.endswith("-flow") and s.slug == s.slug.lower()
        assert not any(p in s.slug for p in PRIVATE), s.slug
        assert s.svg_out.name == f"{s.slug}.svg"


# --- one SVG per spec ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug", IDS)
def test_valid_xml_with_title_desc_and_viewbox(slug):
    s = spec_of(slug)
    root = ET.fromstring(SVGS[slug])
    assert root.attrib["viewBox"] == f"0 0 {df.W} {s.h}" and root.attrib["role"] == "img"
    assert root.find("s:title", NS).text == s.title
    assert len(root.find("s:desc", NS).text) > 100
    assert 2 <= len(s.title.split()) and len(s.title) < 90


@pytest.mark.parametrize("slug", IDS)
@pytest.mark.parametrize("group", ["motion", "still"])
def test_every_label_of_the_original_block_is_drawn(slug, group):
    drawn = df._squash("".join(texts(ET.fromstring(SVGS[slug]), group)))
    for label in spec_of(slug).labels:
        assert df._squash(label) in drawn, f"{group}: {label!r} is not drawn"


@pytest.mark.parametrize("slug", IDS)
def test_no_private_names_employers_install_lines_or_dashes(slug):
    s = spec_of(slug)
    text = visible(SVGS[slug]).lower()
    for word in FORBIDDEN:
        assert word not in text, f"{slug}: {word}"
    assert "—" not in text and "–" not in text
    for field in (s.title, s.desc, s.alt, s.caption, *s.labels):
        low = field.lower()
        assert not any(w in low for w in FORBIDDEN), field
        assert "—" not in field and "–" not in field, field
    for w in EMPLOYER_ISH:
        assert w not in text


@pytest.mark.parametrize("slug", IDS)
def test_self_contained_smil_no_scripts_no_external_requests(slug):
    svg = SVGS[slug]
    assert "<script" not in svg and "onload" not in svg and "href" not in svg
    assert "https://" not in svg and "file://" not in svg
    assert "http://" not in svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert svg.count("data:font/woff2;base64,") == 2
    assert len(svg) < 400_000


@pytest.mark.parametrize("slug", IDS)
def test_animations_loop_and_keytimes_are_valid(slug):
    root = ET.fromstring(SVGS[slug])
    cycle = df.plan(spec_of(slug)).cycle
    animates = root.findall(".//s:animate", NS) + root.findall(".//s:animateMotion", NS)
    assert len(animates) >= 10
    for a in animates:
        assert a.attrib["repeatCount"] == "indefinite"
        if a.attrib.get("attributeName") == "stroke-dashoffset":
            continue  # the marching dashes on idle connectors: a 1 s linear loop
        assert a.attrib["dur"] == f"{cycle:g}s"
        times = [float(t) for t in a.attrib["keyTimes"].split(";")]
        assert times[0] == 0 and times[-1] == 1 and times == sorted(times), a.attrib
        if a.tag.endswith("}animate"):
            assert len(a.attrib["values"].split(";")) == len(times), a.attrib
        else:
            assert len(a.attrib["keyPoints"].split(";")) == len(times)


@pytest.mark.parametrize("slug", IDS)
def test_reduced_motion_still_is_fully_lit_and_has_no_animation(slug):
    root = ET.fromstring(SVGS[slug])
    svg = SVGS[slug]
    assert "prefers-reduced-motion: reduce" in svg and 'class="motion"' in svg and 'class="still"' in svg
    still = root.find(".//s:g[@class='still']", NS)
    assert not still.findall(".//s:animate", NS) and not still.findall(".//s:animateMotion", NS)
    assert f'opacity="{df.DIM:g}"' not in ET.tostring(still, encoding="unicode"), "nothing in the still is dimmed"


@pytest.mark.parametrize("slug", IDS)
def test_text_is_never_smaller_than_seventeen_pixels(slug):
    for m in re.finditer(r'font-size="([\d.]+)"', visible(SVGS[slug])):
        assert float(m.group(1)) >= 17, m.group(0)
    # the only relative size is a subscript digit (user₁), as in the original block
    for m in re.finditer(r'<[^>]*font-size="[\d.]+%"[^>]*>', visible(SVGS[slug])):
        assert m.group(0).startswith("<tspan") and "baseline-shift" in m.group(0)


@pytest.mark.parametrize("slug", IDS)
def test_layout_has_no_touching_boxes_and_no_dangling_ids(slug):
    assert df.layout_problems(spec_of(slug)) == []


@pytest.mark.parametrize("slug", IDS)
def test_every_edge_and_node_takes_part_in_a_scenario(slug):
    s = spec_of(slug)
    pl = df.plan(s)
    for e in s.edges:
        assert e.id in pl.dots, f"{slug}: edge {e.id} is never lit"
    for n in s.nodes:
        assert n.id in pl.reach, f"{slug}: node {n.id} is never reached"


@pytest.mark.parametrize("slug", IDS)
def test_text_chip_and_label_widths_fit_their_boxes_by_the_font_metrics(slug):
    """The same limits the browser check enforces, worked out from the font's advance widths."""
    root = ET.fromstring(SVGS[slug])
    for t in root.findall(".//s:text", NS):
        maxw = float(t.attrib.get("data-maxw", "0"))
        if not maxw:
            continue
        size = float(t.attrib["font-size"])
        weight = int(t.attrib["font-weight"])
        assert df.width_of("".join(t.itertext()), size, weight) <= maxw + 1.5, "".join(t.itertext())


@pytest.mark.parametrize("slug", IDS)
def test_caption_and_alt_for_the_post(slug):
    s = spec_of(slug)
    assert s.caption.startswith("_") and s.caption.endswith("_") and "\n" not in s.caption
    assert len(s.alt) > 100 and s.alt.startswith("Animated ")
    assert '"' not in s.alt and "]" not in s.alt and "[" not in s.alt


@pytest.mark.parametrize("slug", IDS)
def test_committed_svg_matches_the_generator(slug):
    s = spec_of(slug)
    assert s.svg_out.read_text() == SVGS[slug], "run: python tools/diagram_flows.py"


@pytest.mark.parametrize("slug", IDS)
def test_post_uses_the_svg_with_alt_and_italic_caption_under_its_section(slug):
    s = spec_of(slug)
    text = s.post_file().read_text()
    lines = text.splitlines()
    idx = [i for i, ln in enumerate(lines) if f"]({s.img_path})" in ln]
    assert len(idx) == 1
    i = idx[0]
    assert lines[i] == f"![{s.alt}]({s.img_path})"
    assert lines[i + 1] == s.caption
    heading = max(n for n, ln in enumerate(lines[:i]) if re.match(r"#{2,4} ", ln))
    assert s.section in lines[heading]
    assert "```mermaid" not in text
    assert not re.search(r"^mermaid: true$", text.split("\n---\n", 1)[0], re.M), "no mermaid block left: the flag goes"


# --- timelines ----------------------------------------------------------------------------------------

def test_witness_branches_dim_until_their_scenario_reaches_them():
    s = spec_of("witness-two-gates-flow")
    pl = df.plan(s)
    assert len(s.scenarios) == 3
    assert df.branch_nodes(s, pl) == {"g2", "l", "x"}
    # the three scenarios run one after the other, each ending before the next starts
    ends = [e for _, e in pl.scn]
    starts = [b for b, _ in pl.scn]
    assert starts[0] == 0 and starts[1:] == ends[:-1] and pl.cycle == ends[-1]


def test_single_scenario_diagrams_have_no_dimmed_branches():
    s = spec_of("billing-header-kv-cache-setup-flow")
    assert df.branch_nodes(s, df.plan(s)) == set()


def test_steps_run_in_order_inside_a_scenario():
    s = spec_of("three-chat-template-patterns-prefix-cache-flow")
    pl = df.plan(s)
    starts = [pl.dots[e][0] for e in ("e-prefill", "e-snap", "e-lookup", "e-hit")]
    assert starts == sorted(starts) and len(set(starts)) == 4


def test_frame_times_fall_inside_the_loop():
    for s in SPECS:
        pl = df.plan(s)
        times = df.frame_times(s)
        assert len(times) == 3 and all(0 < t < pl.cycle for t in times) and list(times) == sorted(times)


# --- geometry helpers ------------------------------------------------------------------------------------

def test_rounded_polyline_rounds_each_corner_and_stops_at_the_last_point():
    d = df.rounded([(0, 0), (100, 0), (100, 100)], r=10)
    assert d.startswith("M0 0 L90.0 0.0 Q100 0 100.0 10.0") and d.endswith("L100.0 100.0")


def test_a_connector_stops_short_of_the_node_it_points_at():
    s = spec_of("billing-header-kv-cache-setup-flow")
    e = next(e for e in s.edges if e.id == "e-req")
    (_, y0), (x1, y1) = df.edge_points(s, e)[-2:]
    assert y0 == y1 and df.anchor(s, e.b)[0] - x1 == pytest.approx(df.GAP)


def test_diamond_anchors_lie_on_the_slanted_edges():
    s = spec_of("ioc-lifecycle-multi-agent-team-flow")
    sup = s.node("sup")
    x, y = df.anchor(s, "sup.bd:40")
    assert x == pytest.approx(sup.cx + 40) and sup.cy < y < sup.bottom
    x2, y2 = df.anchor(s, "sup.ld:0")
    assert x2 == pytest.approx(sup.x) and y2 == pytest.approx(sup.cy)


def test_routes_make_orthogonal_corners():
    e = df.Edge("e", (0, 0), (100, 60), route="vhv", mid=20)
    assert df.route_via(e, (0, 0), (100, 60)) == ((0, 20), (100, 20))
    assert df.route_via(df.Edge("e", (0, 0), (1, 1), route="hv"), (0, 0), (100, 60)) == ((100, 0),)
    assert df.route_via(df.Edge("e", (0, 0), (1, 1)), (0, 0), (100, 60)) == ()


def test_subscript_digits_become_baseline_shifted_tspans():
    out = df.T(0, 0, "user₁ + asst₂", 18, "#fff")
    assert out.count("baseline-shift") == 2 and ">user<" in out
    assert df.width_of("user₁", 18, 400) > df.width_of("user", 18, 400)


def test_a_node_without_a_size_is_fitted_to_its_text():
    n = df.Node("n", ("a fairly long title for a card", "and a detail line"), icon="doc")
    df.fit(n)
    assert n.w >= df.ICON_BLOCK + df.width_of("a fairly long title for a card", df.TSIZE) and n.h >= 92
    gate = df.fit(df.Node("g", ("gate", "does the record", "say that?"), kind="gate"))
    assert gate.w > gate.h > 150


# --- the posts --------------------------------------------------------------------------------------------------

SAMPLE = """---
title: "A post"
mermaid: true
---

## A section

Words.

```mermaid
flowchart LR
    A[claude-code-router] --> B[Shim<br/>strips]
```

After.
"""


def sample_spec(**kw) -> df.Spec:
    base = {"slug": "sample-flow", "post": "sample", "section": "A section", "title": "Sample", "desc": "d",
            "alt": "Animated a b", "caption": "_cap_", "h": 300, "nodes": [], "edges": [], "scenarios": [],
            "labels": ("claude-code-router", "Shim")}
    base.update(kw)
    return df.Spec(**base)


def test_replace_block_swaps_the_block_for_image_and_caption_and_drops_the_flag():
    out = df.replace_block(SAMPLE, sample_spec())
    assert "```mermaid" not in out and "mermaid: true" not in out
    assert "![Animated a b](/assets/img/posts/sample-flow.svg)\n_cap_\n\nAfter." in out
    assert out.startswith('---\ntitle: "A post"\n---')
    assert df.replace_block(out, sample_spec()) == out, "applying twice changes nothing"


def test_replace_block_keeps_the_flag_while_another_block_remains():
    two = SAMPLE + "\n## Other\n\n```mermaid\nflowchart LR\n    X --> Y\n```\n"
    out = df.replace_block(two, sample_spec())
    assert "mermaid: true" in out and out.count("```mermaid") == 1


def test_replace_block_refuses_a_block_that_lacks_a_label():
    with pytest.raises(ValueError, match="does not contain"):
        df.replace_block(SAMPLE, sample_spec(labels=("claude-code-router", "not in the block")))


# --- the contact sheet ----------------------------------------------------------------------------------------------

def test_contact_sheet_lists_every_diagram_with_its_post_and_section(tmp_path):
    sheet = df.contact_sheet(SPECS, tmp_path)
    page = sheet.read_text()
    for s in SPECS:
        assert (tmp_path / s.svg_out.name).read_text() == s.svg_out.read_text()
        assert f'src="{s.svg_out.name}"' in page
        assert s.section.split(":")[0] in page
    assert 'data-v="dark"' in page and 'data-v="light"' in page and "prefers-color-scheme" in page


def test_main_lists_the_specs(capsys):
    assert df.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == len(SPECS) and "witness-two-gates-flow" in out


def test_main_writes_the_svgs_without_a_browser(tmp_path, monkeypatch):
    monkeypatch.setattr(df, "IMG_DIR", tmp_path)
    assert df.main(["--only", "billing"]) == 0
    assert (tmp_path / "billing-header-kv-cache-setup-flow.svg").read_text() == SVGS["billing-header-kv-cache-setup-flow"]


# --- font metrics ---------------------------------------------------------------------------------------------------

def test_font_metrics_cover_printable_ascii_in_both_weights():
    for w in (400, 700):
        assert all(chr(c) in fm.WIDTHS[w] for c in range(33, 127)), w
    assert fm.text_width("iiii", 20) < fm.text_width("MMMM", 20)
    assert fm.text_width("Shim", 22, 700) == pytest.approx(sum(fm.WIDTHS[700][c] for c in "Shim") * 22 / 1000)
    assert fm.text_width("→", 20) == pytest.approx(fm.FALLBACK[700] * 20 / 1000)


def test_font_metrics_table_matches_the_font_files():
    pytest.importorskip("fontTools")
    assert fm.measure() == fm.WIDTHS


# --- rendering (needs Playwright and a browser) --------------------------------------------------------------------------

def _need_browser():
    pytest.importorskip("playwright")


@pytest.mark.parametrize("slug", IDS)
def test_no_label_overflows_overlaps_or_leaves_the_drawing(slug):
    _need_browser()
    try:
        bad = df.find_problems(spec_of(slug))
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert bad == []


def test_reduced_motion_swaps_the_animation_for_the_still():
    _need_browser()
    from playwright.sync_api import sync_playwright
    s = SPECS[0]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            shown = {}
            for mode in ("reduce", "no-preference"):
                page = browser.new_page(viewport={"width": df.W, "height": s.h}, reduced_motion=mode)
                page.goto(s.svg_out.resolve().as_uri())
                shown[mode] = page.evaluate(
                    "['.motion', '.still'].map(q => getComputedStyle(document.querySelector(q)).display)")
                page.close()
            browser.close()
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert shown["reduce"] == ["none", "inline"]
    assert shown["no-preference"] == ["inline", "none"]


def test_frames_are_rendered_on_a_dark_and_a_light_page(tmp_path):
    _need_browser()
    s = spec_of("witness-two-gates-flow")
    try:
        shots = df.render_frames(s, tmp_path)
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert len(shots) == 6 and {p.name.split("-")[-2] for p in shots} == {"dark", "light"}
    for p in shots:
        assert p.exists() and p.stat().st_size > 20_000
    dark = [p.read_bytes() for p in shots if "-dark-" in p.name]
    assert len(set(dark)) == len(dark), "frames of different moments differ"
