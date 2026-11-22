"""The branded favicon set: right sizes, brand colours, a valid manifest, and the head links to them.

Run: python -m pytest tools/test_favicon.py
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import favicon as fav  # noqa: E402

ROOT = fav.ROOT
OUT = fav.OUT


def test_svg_is_well_formed_and_uses_the_brand_gradient():
    svg = fav.mark_svg()
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    for color in (fav.BLUE, fav.MID, fav.GREEN):
        assert color in svg
    assert 'rx="112"' in svg and 'rx="0"' in fav.mark_svg(rounded=False)


def test_full_bleed_icons_keep_the_mark_inside_the_safe_zone():
    assert 'scale(0.8)' in fav.mark_svg(rounded=False, scale=0.8)
    assert all(scale <= 0.8 for _, (_, rounded, scale) in fav.PNGS.items() if not rounded)


def test_no_company_marks_or_text_in_the_icon():
    assert "<text" not in fav.mark_svg()
    assert "<image" not in fav.mark_svg()


@pytest.mark.parametrize("name,spec", list(fav.PNGS.items()), ids=list(fav.PNGS))
def test_each_png_is_the_right_size_and_brand_coloured(name, spec):
    img = Image.open(OUT / name).convert("RGBA")
    assert img.size == (spec[0], spec[0])
    px = img.getpixel((img.width // 2, img.height - 3 if spec[1] else img.height - 2))
    r, g, b, a = px
    assert a > 0 and b + g > r * 2, f"{name}: bottom edge is not the blue to green gradient: {px}"


def test_rounded_icons_have_transparent_corners_and_full_bleed_ones_do_not():
    assert Image.open(OUT / "favicon-96x96.png").convert("RGBA").getpixel((0, 0))[3] == 0
    assert Image.open(OUT / "apple-touch-icon.png").convert("RGBA").getpixel((0, 0))[3] == 255


def test_ico_holds_16_32_and_48():
    with Image.open(OUT / "favicon.ico") as ico:
        assert {(16, 16), (32, 32), (48, 48)} <= set(ico.info["sizes"])


def test_manifest_lists_the_icons_and_brand_colour():
    text = (OUT / "site.webmanifest").read_text()
    body = text.split("---", 2)[2]
    body = re.sub(r"\{%.*?%\}", "", body)
    body = re.sub(r"\{\{.*?\}\}", "x", body)
    data = json.loads(body)
    assert [i["sizes"] for i in data["icons"]] == ["192x192", "512x512"]
    assert data["theme_color"] == fav.THEME_COLOR


def test_every_file_the_manifest_and_head_name_exists():
    head = (ROOT / "_includes" / "favicons.html").read_text()
    for name in re.findall(r"favicon_path \}\}/([\w.\-]+)", head):
        assert (OUT / name).is_file(), name
    manifest = (OUT / "site.webmanifest").read_text()
    for name in re.findall(r"favicon_path \}\}/([\w.\-]+)", manifest):
        assert (OUT / name).is_file(), name


def test_preview_page_shows_16_32_and_180_on_light_and_dark(tmp_path):
    html = fav.preview_html()
    assert html.count('width="16"') >= 2 and html.count('width="32"') == 2 and html.count('width="180"') == 2
    assert 'class="light"' in html and 'class="dark"' in html
