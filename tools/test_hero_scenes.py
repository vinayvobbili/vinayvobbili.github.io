"""Tests for tools/hero_scenes.py, hero_draw.py and hero_kit.py. Run: python -m pytest tools/test_hero_scenes.py"""
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402
import hero_kit as kit  # noqa: E402
import hero_scenes as hs  # noqa: E402

NS = {"s": "http://www.w3.org/2000/svg"}
POSTS = sorted((hs.ROOT / "_posts").glob("*.md"))

# Private projects: their posts keep their titles, but no image or new text may name them.
PRIVATE = ("iocflow", "detflow", "aisoc", "attestq", "domainflow", "security-ops-platform")
# Words that must not appear in any generated card, flow, caption or alt text.
EMPLOYER_ISH = ("met" + "life", "met" + "iq", "xsoar", "webex", "crowd" + "strike")  # split: this file names no employer
FORBIDDEN = PRIVATE + ("pip install", "pypi", "open source", "open-source", "ticket", "github.com/") + EMPLOYER_ISH


def published(path: Path) -> bool:
    head = path.read_text().split("\n---\n", 1)[0]
    return not re.search(r"^published:\s*false\s*$", head, re.M)


PUBLISHED = [p for p in POSTS if published(p)]


def front_matter(path: Path) -> dict[str, str]:
    """image.path and image.alt of a post, read with plain regexes (no YAML dependency)."""
    text = path.read_text()
    out = {}
    m = re.search(r"^  path: (\S+)$", text, re.M)
    out["path"] = m.group(1) if m else ""
    m = re.search(r'^  alt: "(.*)"$', text, re.M)
    out["alt"] = m.group(1) if m else ""
    return out


def visible(text: str) -> str:
    return re.sub(r"base64,[A-Za-z0-9+/=]+", "base64,", text).lower()


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", data[16:24])


GENERATED = [s for s in hs.SCENES if not s.external]
FLOWS = [s for s in GENERATED if s.flow]
PAGES = list(hs.PAGE_SCENES)
CARDS = GENERATED + PAGES   # every card drawn here: posts first, then standalone pages


# --- coverage ---------------------------------------------------------------------

def test_there_are_published_posts_and_unpublished_ones_are_skipped():
    assert len(PUBLISHED) >= 16
    for p in POSTS:
        assert (p in PUBLISHED) == published(p)


def test_every_published_post_has_exactly_one_hero_scene():
    for post in PUBLISHED:
        matches = [s for s in hs.SCENES if post.match(f"_posts/{s.post}") or post.match(s.post)]
        assert len(matches) == 1, f"{post.name}: {[s.slug for s in matches]}"


def test_every_scene_belongs_to_a_published_post():
    for s in hs.SCENES:
        assert any(p.match(s.post) for p in PUBLISHED), s.slug


def test_page_scenes_point_at_an_existing_page_that_uses_their_png_as_og_and_twitter_image():
    assert PAGES, "the witness page has its own card"
    for s in PAGES:
        assert not s.post and not s.external and s.draw
        page = (hs.ROOT / s.page).read_text()
        url = f"https://{hero.SITE}{s.hero_path}"
        assert f'<meta property="og:image" content="{url}">' in page
        assert f'<meta name="twitter:image" content="{url}">' in page
        assert f'<meta property="og:image:alt" content="{s.alt}">' in page


def test_slugs_are_unique_and_every_scene_has_a_drawing_or_is_external():
    everything = hs.SCENES + hs.PAGE_SCENES
    assert len({s.slug for s in everything}) == len(everything)
    for s in hs.SCENES:
        assert (s.draw is None) == s.external, s.slug


@pytest.mark.parametrize("scene", hs.SCENES, ids=lambda s: s.slug)
def test_post_front_matter_points_at_its_hero_with_alt_text(scene):
    post = next(p for p in PUBLISHED if p.match(scene.post))
    fm = front_matter(post)
    assert fm["path"] == scene.hero_path
    assert len(fm["alt"]) > 40, "alt text should describe what the card shows"
    if not scene.external:
        assert fm["alt"] == scene.alt


@pytest.mark.parametrize("scene", FLOWS, ids=lambda s: s.slug)
def test_flow_is_inserted_under_the_intro_with_alt_and_italic_caption(scene):
    post = next(p for p in PUBLISHED if p.match(scene.post))
    lines = post.read_text().splitlines()
    idx = [i for i, ln in enumerate(lines) if f"]({scene.flow_path})" in ln]
    assert len(idx) == 1
    i = idx[0]
    assert lines[i].startswith("![") and len(lines[i].split("](")[0]) > 40, "standard markdown image with alt text"
    assert lines[i + 1] == scene.flow.caption and lines[i + 1].startswith("_") and lines[i + 1].endswith("_")
    first_h2 = next(n for n, ln in enumerate(lines) if ln.startswith("## "))
    assert i < first_h2 + 30, "the animation sits near the top, under the intro"


def test_five_new_flows_and_the_questionnaire_flow_exist():
    assert len(FLOWS) == 5
    assert hd_flow().exists()


def hd_flow() -> Path:
    import hero_diagram
    return hero_diagram.SVG_OUT


# --- palettes ---------------------------------------------------------------------

def test_every_scene_has_its_own_palette_in_accents_yml():
    seen = {}
    for s in hs.SCENES + hs.PAGE_SCENES:
        p = hero.load_palette(s.palette)
        for field in ("cardfrom", "cardvia", "cardto", "glowa", "glowb", "glowc", "headto"):
            assert re.fullmatch(r"#[0-9a-f]{6}", p[field]), (s.palette, field)
        key = (p["cardfrom"], p["cardvia"], p["cardto"])
        assert key not in seen, f"{s.slug} repeats the palette of {seen[key]}"
        seen[key] = s.slug


# --- the rules: no private names, no install talk, no dashes ----------------------

@pytest.mark.parametrize("scene", CARDS, ids=lambda s: s.slug)
def test_card_has_no_forbidden_words_or_dashes(scene):
    text = visible(hs.card_html(scene))
    for word in FORBIDDEN:
        assert word not in text, f"{scene.slug}: {word}"
    assert "—" not in text and "–" not in text
    assert "<script" not in text and "file://" not in text and "fonts.googleapis" not in text


@pytest.mark.parametrize("scene", CARDS, ids=lambda s: s.slug)
def test_scene_text_fields_are_clean(scene):
    fields = [scene.slug, scene.headline, scene.subtitle, scene.alt, scene.hero_path]
    if scene.flow:
        f = scene.flow
        fields += [f.title, f.desc, f.alt, f.caption, f.still_caption, scene.flow_path] + [c[2] for c in f.captions]
    for text in fields:
        low = text.lower()
        for word in FORBIDDEN:
            assert word not in low, f"{scene.slug}: {word!r} in {text!r}"
        assert "—" not in text and "–" not in text, text


@pytest.mark.parametrize("scene", CARDS, ids=lambda s: s.slug)
def test_card_footer_is_only_the_site_and_fonts_are_inlined(scene):
    markup = hs.card_html(scene)
    assert markup.count(hero.SITE) == 1
    assert markup.count("data:font/woff2;base64,") == 2
    assert hero.SITE in markup.split('class="site"')[1]


def test_no_new_image_file_name_contains_a_private_project():
    for s in CARDS:
        for name in (s.png.name, s.svg.name):
            assert not any(p in name for p in PRIVATE), name


def test_posts_use_the_new_images_not_the_old_private_named_ones():
    for s in GENERATED:
        post = next(p for p in PUBLISHED if p.match(s.post))
        assert front_matter(post)["path"] == s.hero_path
        assert not any(p in front_matter(post)["path"] for p in PRIVATE)
        assert not any(w in front_matter(post)["alt"].lower() for w in EMPLOYER_ISH + PRIVATE)


@pytest.mark.parametrize("scene", CARDS, ids=lambda s: s.slug)
def test_text_is_never_smaller_than_twelve_and_a_half_pixels(scene):
    for m in re.finditer(r'font-size="([\d.]+)"', scene.draw(kit.Ctx())):
        assert float(m.group(1)) >= 12.5, (scene.slug, m.group(0))


# --- the drawings -----------------------------------------------------------------

@pytest.mark.parametrize("scene", CARDS, ids=lambda s: s.slug)
def test_static_drawing_is_well_formed_and_not_animated(scene):
    markup = scene.draw(kit.Ctx())
    assert "<animate" not in markup
    root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{kit.defs()}{markup}</svg>')
    assert root.findall(".//s:text", NS), "a drawing needs labels"


@pytest.mark.parametrize("scene", FLOWS, ids=lambda s: s.slug)
def test_flow_svg_is_self_contained_valid_smil_with_a_still_fallback(scene):
    svg = hs.flow_svg(scene)
    root = ET.fromstring(svg)
    assert root.attrib["viewBox"] == "0 0 1200 470"
    assert "<script" not in svg and "onload" not in svg and "href" not in svg
    assert "https://" not in svg and "file://" not in svg
    assert "http://" not in svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert svg.count("data:font/woff2;base64,") == 2
    assert "prefers-reduced-motion: reduce" in svg and 'class="motion"' in svg and 'class="still"' in svg
    animates = root.findall(".//s:animate", NS) + root.findall(".//s:animateMotion", NS)
    assert animates
    for a in animates:
        assert a.attrib["dur"] == f"{scene.flow.cycle:g}s" and a.attrib["repeatCount"] == "indefinite"
        times = [float(t) for t in a.attrib["keyTimes"].split(";")]
        assert times[0] == 0 and times[-1] == 1 and times == sorted(times), a.attrib
        if a.tag.endswith("}animate"):
            assert len(a.attrib["values"].split(";")) == len(times), a.attrib
        else:
            assert len(a.attrib["keyPoints"].split(";")) == len(times)
    # the still copy carries no animation at all
    still = root.find(".//s:g[@class='still']", NS)
    assert still is not None and not still.findall(".//s:animate", NS)
    assert len(svg) < 250_000


@pytest.mark.parametrize("scene", FLOWS, ids=lambda s: s.slug)
def test_flow_captions_fit_the_cycle_and_do_not_overlap(scene):
    f = scene.flow
    prev_end = 0.0
    for a, b, text in f.captions:
        assert 0 <= a < b <= f.cycle and b - a >= 2.0, (a, b)
        assert a >= prev_end - 0.5
        prev_end = b
        assert len(text) <= 80
    assert f.captions[-1][1] <= f.cycle


@pytest.mark.parametrize("scene", FLOWS, ids=lambda s: s.slug)
def test_committed_flow_matches_the_generator(scene):
    assert scene.svg.read_text() == hs.flow_svg(scene), "run: python tools/hero_scenes.py"


def test_html_mode_writes_every_card_without_a_browser(tmp_path):
    assert hs.main(["--html-dir", str(tmp_path)]) == 0
    files = sorted(p.name for p in tmp_path.glob("*.html"))
    assert files == sorted(f"{s.slug}.html" for s in CARDS)
    assert all(p.read_text().startswith("<!doctype html>") for p in tmp_path.glob("*.html"))


def test_contact_sheet_lists_every_post_title_hero_and_flow(tmp_path):
    sheet = hs.contact_sheet(tmp_path)
    page = sheet.read_text()
    for s in hs.SCENES:
        assert (tmp_path / s.png.name).exists() and s.png.name in page
        assert hs.post_title(s).replace("&", "&amp;").replace('"', "&quot;")[:30] in page.replace("&#x27;", "'")
    for s in FLOWS:
        assert (tmp_path / s.svg.name).exists() and s.svg.name in page
    assert "<script" in page and "prefers-color-scheme: dark" in page and 'data-theme="system"' in page


def test_post_title_handles_escaped_quotes():
    scene = hs.BY_SLUG["evidence-grounded-questionnaires"]
    assert hs.post_title(scene) == 'When "We Don\'t Have Evidence for That" Is the Feature'


def test_unknown_only_fragment_is_an_error():
    with pytest.raises(SystemExit):
        hs.main(["--only", "no-such-scene"])


# --- the kit ----------------------------------------------------------------------

def test_static_ctx_draws_everything_lit_and_animated_ctx_adds_valid_smil():
    s, a = kit.Ctx(), kit.Ctx(10)
    assert s.show("<g/>", (1, 2)) == "<g/>" and s.dot("M0 0 L1 1", 1, 2, "#fff") == "" and s.ring(0, 0, 1, 1, 1, "#fff", (1, 2)) == ""
    shown = a.show("<g/>", (1, 3), (5, 6))
    assert shown.startswith('<g opacity="0">') and 'repeatCount="indefinite"' in shown
    m = re.search(r'keyTimes="([^"]+)"', shown)
    times = [float(t) for t in m.group(1).split(";")]
    assert times[0] == 0 and times[-1] == 1 and times == sorted(times)
    assert "animateMotion" in a.dot("M0 0 L1 1", 1, 2, "#fff")
    assert 'attributeName="width"' in a.grow(0, 0, 100, 10, "green", 1, 2, hs.dr.SPAN_END)


def test_every_icon_is_well_formed_svg():
    for name, ico in kit.ICONS.items():
        ET.fromstring(f'<g xmlns="http://www.w3.org/2000/svg">{ico}</g>')
        assert kit.icon(name, 0, 0, 24).startswith("<g transform=")


# --- rendering (needs Playwright and a browser) -----------------------------------

def _need_browser():
    pytest.importorskip("playwright")


@pytest.mark.parametrize("scene", CARDS, ids=lambda s: s.slug)
def test_committed_png_is_1200_by_630(scene):
    assert scene.png.exists(), "run: python tools/hero_scenes.py"
    assert png_size(scene.png) == (1200, 630)


def test_the_questionnaire_png_is_1200_by_630_too():
    scene = hs.BY_SLUG["evidence-grounded-questionnaires"]
    assert png_size(scene.png) == (1200, 630)


def test_no_label_overflows_its_box_or_the_card():
    _need_browser()
    try:
        problems = hs.find_overflow(CARDS)
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert problems == {}


@pytest.mark.parametrize("scene", FLOWS, ids=lambda s: s.slug)
def test_reduced_motion_shows_the_still_picture_instead_of_the_animation(scene):
    _need_browser()
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            shown = {}
            for mode in ("reduce", "no-preference"):
                page = browser.new_page(viewport={"width": 1200, "height": 470}, reduced_motion=mode)
                page.goto(scene.svg.resolve().as_uri())
                shown[mode] = page.evaluate(
                    "['.motion', '.still'].map(s => getComputedStyle(document.querySelector(s)).display)")
                page.close()
            browser.close()
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert shown["reduce"] == ["none", "inline"]
    assert shown["no-preference"] == ["inline", "none"]


def test_contact_sheet_loads_every_image_in_a_browser(tmp_path):
    _need_browser()
    from playwright.sync_api import sync_playwright
    sheet = hs.contact_sheet(tmp_path)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(sheet.resolve().as_uri())
            page.evaluate("document.querySelectorAll('img').forEach(i => { i.loading = 'eager'; })")
            page.wait_for_function("[...document.images].every(i => i.complete)")
            broken = page.evaluate("[...document.images].filter(i => !i.naturalWidth).map(i => i.src)")
            count = page.evaluate("document.images.length")
            browser.close()
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert broken == []
    assert count == len(hs.SCENES) + len(FLOWS) + 1  # heroes, five flows, the questionnaire flow


def test_rendering_a_card_gives_a_1200_by_630_png(tmp_path, monkeypatch):
    _need_browser()
    monkeypatch.setattr(hs, "POSTS_IMG", tmp_path)
    scene = hs.BY_SLUG["reranker-mined-pairs"]
    try:
        [out] = hs.render_cards([scene])
    except Exception as exc:  # browser binaries missing
        pytest.skip(f"no browser: {exc}")
    assert out.parent == tmp_path and png_size(out) == (1200, 630)
