"""Tests for tools/optimize_images.py and for the images the site actually ships.

Run: python -m pytest tools/test_optimize_images.py
"""
import random
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_images as oi  # noqa: E402

ROOT = oi.ROOT
# a grainy synthetic gradient dithers worse than the real cards (which pass oi.MAX_MAE), so the
# mechanism tests allow more error
LOOSE = 4.0
needs_pngquant =pytest.mark.skipif(not shutil.which("pngquant"), reason="pngquant not installed")
needs_cwebp = pytest.mark.skipif(not shutil.which("cwebp"), reason="cwebp not installed")


def gradient_card(path: Path) -> None:
    """A two-axis gradient with a little grain, like the hero backgrounds, as a truecolor PNG."""
    rng = random.Random(7)
    img = Image.new("RGB", (600, 315))
    img.putdata([(20 + x * 60 // 599 + rng.randint(0, 1), 90 + y * 60 // 314 + rng.randint(0, 1), 160 + rng.randint(0, 1))
                 for y in range(315) for x in range(600)])
    img.save(path)


@needs_pngquant
def test_optimize_png_shrinks_a_truecolor_card_and_keeps_it_a_png(tmp_path):
    card = tmp_path / "x-hero.png"
    gradient_card(card)
    assert not oi.is_palette_png(card)
    before, after = oi.optimize_png(card, max_mae=LOOSE)
    assert after < before * 0.6
    assert oi.is_palette_png(card)
    assert Image.open(card).size == (600, 315)


@needs_pngquant
def test_optimize_png_is_idempotent(tmp_path):
    card = tmp_path / "x-hero.png"
    gradient_card(card)
    assert oi.optimize_png(card, max_mae=LOOSE)
    size = card.stat().st_size
    assert oi.optimize_png(card, max_mae=LOOSE) is None
    assert card.stat().st_size == size


@needs_pngquant
def test_optimize_png_refuses_a_result_that_differs_too_much(tmp_path):
    card = tmp_path / "x-hero.png"
    gradient_card(card)
    original = card.read_bytes()
    assert oi.optimize_png(card, max_mae=0.0) is None
    assert card.read_bytes() == original


@needs_pngquant
def test_squeezed_card_stays_visually_close(tmp_path):
    card, kept = tmp_path / "a.png", tmp_path / "b.png"
    gradient_card(card)
    shutil.copy(card, kept)
    oi.optimize_png(card, max_mae=LOOSE)
    assert 0 < oi.mean_abs_error(kept, card) < LOOSE


@needs_cwebp
def test_make_webp_resizes_to_the_requested_width(tmp_path):
    card = tmp_path / "x-hero.png"
    gradient_card(card)
    out = tmp_path / "x-hero-300.webp"
    oi.make_webp(card, out, 300)
    assert Image.open(out).size == (300, 158)


def test_thumb_path_sits_next_to_the_hero():
    hero = Path("/a/b/some-post-hero.png")
    assert oi.thumb_path(hero) == Path(f"/a/b/some-post-hero-{oi.THUMB_WIDTH}.webp")


# ---- the images the site ships ----------------------------------------------------------

def test_every_shipped_image_is_within_budget():
    # fix: python tools/optimize_images.py
    assert oi.problems() == []


def test_there_are_heroes_to_check():
    assert len(oi.post_heroes()) >= 10
    assert oi.ROOT / "assets/img/posts/witness-page-hero.png" in oi.all_heroes()


def test_heroes_keep_their_png_names_and_social_card_size():
    # og:image URLs and LinkedIn previews point at these files
    for hero in oi.all_heroes():
        assert hero.suffix == ".png"
        assert Image.open(hero).size == (1200, 630), hero.name


def test_avatar_is_a_224px_webp_and_the_site_uses_it():
    assert Image.open(oi.AVATAR_WEBP).size == (oi.AVATAR_SIZE, oi.AVATAR_SIZE)
    assert oi.AVATAR_WEBP.stat().st_size <= oi.AVATAR_BUDGET
    config = (ROOT / "_config.yml").read_text()
    assert "avatar: /assets/img/avatar.webp" in config


def test_thumbnails_are_the_right_width():
    for hero in oi.post_heroes():
        assert Image.open(oi.thumb_path(hero)).width == oi.THUMB_WIDTH, hero.name


def test_home_list_serves_the_thumbnail():
    home = (ROOT / "_layouts" / "home.html").read_text()
    assert "replace: '-hero.png', '-hero-640.webp'" in home


def test_post_hero_plugin_makes_the_header_image_eager():
    plugin = (ROOT / "_plugins" / "eager-hero.rb").read_text()
    assert "fetchpriority" in plugin and "preview-img" in plugin
