"""The theme choice (Light, Dark, System) must reach the brand palette, and white text on the
sidebar gradient must stay readable.

Run: python -m pytest tools/test_contrast.py
Against a served site: python tools/contrast_check.py http://127.0.0.1:4000 /
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contrast_check import blend, contrast, luminance, parse_rgb, worst_contrast

SCSS = (Path(__file__).resolve().parent.parent / "assets" / "css" / "jekyll-theme-chirpy.scss").read_text()
WHITE = (255, 255, 255)


def hex_rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def test_contrast_matches_wcag_reference_values():
    assert contrast((0, 0, 0), WHITE) == pytest.approx(21.0)
    assert contrast(WHITE, WHITE) == pytest.approx(1.0)
    assert luminance((255, 255, 255)) == pytest.approx(1.0)


def test_parse_rgb_accepts_the_formats_chrome_returns():
    assert parse_rgb("rgb(1, 2, 3)") == (1, 2, 3, 1.0)
    assert parse_rgb("rgba(1, 2, 3, 0.5)") == (1, 2, 3, 0.5)
    assert parse_rgb("rgb(1 2 3 / 25%)") == (1, 2, 3, 0.25)


def test_translucent_text_is_blended_before_measuring():
    # 95% white over the brand blue is a little under pure white over it
    blue = hex_rgb("#0046ad")
    assert worst_contrast("rgba(255, 255, 255, 0.95)", [blue]) < worst_contrast("rgb(255, 255, 255)", [blue])
    assert blend((255, 255, 255, 0.0), blue) == blue


def test_scss_keys_the_palette_on_the_attribute_chirpy_sets():
    # Chirpy 7 sets data-bs-theme; data-mode is never set, so rules on it never apply
    assert "data-mode" not in SCSS
    assert ":root[data-bs-theme='light']" in SCSS
    assert ":root[data-bs-theme='dark']" in SCSS
    assert ":root:not([data-bs-theme])" in SCSS


def test_sidebar_gradient_keeps_white_text_readable():
    m = re.search(r"\$brand-grad-text:\s*linear-gradient\(([^;]+)\);", SCSS)
    assert m, "the sidebar gradient variable is missing"
    stops = re.findall(r"#[0-9a-fA-F]{6}", m.group(1))
    assert len(stops) >= 3
    for stop in stops:
        # the nav and subtitle text is 95% white
        assert worst_contrast("rgba(255, 255, 255, 0.95)", [hex_rgb(stop)]) >= 4.5, stop


def test_sidebar_and_topbar_use_the_readable_gradient():
    sidebar = re.search(r"#sidebar \{\s*background: (\S+)", SCSS)
    topbar = re.search(r"#topbar-wrapper \{\s*background: (\S+)", SCSS)
    assert sidebar and sidebar.group(1) == "$brand-grad-text"
    assert topbar and topbar.group(1) == "$brand-grad-text"


def test_sidebar_hover_highlight_darkens_instead_of_lightening():
    # a white overlay on the green end of the gradient drops white text under 4.5:1
    for mixin in ("brand-light", "brand-dark"):
        body = re.search(r"@mixin %s \{(.*?)\n\}" % mixin, SCSS, re.S).group(1)
        assert re.search(r"--sidebar-hover-bg: #\{rgba\(#000", body), mixin
