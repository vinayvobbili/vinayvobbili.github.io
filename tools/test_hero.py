"""Tests for tools/hero.py. Run: python -m pytest tools/test_hero.py"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402


def test_every_palette_in_accents_yml_loads():
    text = hero.ACCENTS.read_text()
    keys = [line.split(":")[0] for line in text.splitlines() if line[:1].isalpha()]
    assert keys, "no palettes found"
    for key in keys:
        palette = hero.load_palette(key)
        assert {"grad", "accent", "glow", "shadow"} <= palette.keys(), key
        assert hero.gradient_stops(palette["grad"]), key


def test_unknown_accent_names_the_known_ones():
    with pytest.raises(SystemExit, match="known:.*coral"):
        hero.load_palette("no-such-palette")


def test_card_escapes_text_and_inlines_fonts():
    markup = hero.card_html(
        palette=hero.load_palette("coral"),
        kicker="A & B",
        headline="<script>",
        sub="sub",
        title="title",
    )
    assert "A &amp; B" in markup
    assert "&lt;script&gt;" in markup and "<script>" not in markup
    assert markup.count("data:font/woff2;base64,") == 2
    assert "file://" not in markup and "fonts.googleapis" not in markup


def test_html_mode_writes_file_without_a_browser(tmp_path):
    out = tmp_path / "card.html"
    rc = hero.main([
        "--accent", "coral", "--kicker", "k", "--headline", "h",
        "--sub", "s", "--title", "t", "--out", str(out), "--html",
    ])
    assert rc == 0
    assert out.read_text().startswith("<!doctype html>")
