#!/usr/bin/env python3
"""Keep the site's images small without changing how they look.

  * Hero cards stay PNG (og:image and LinkedIn previews need PNG, and the URLs must not move),
    but are quantized to a palette with pngquant (quality 70-90). A result that differs from
    the source by more than MAX_MAE on average is refused, so a bad squeeze never lands.
  * Each post's home-list thumbnail is a 640 px WebP next to its hero (<slug>-hero-640.webp);
    _layouts/home.html serves it in place of the 1200 px PNG.
  * The sidebar avatar is shown at 112 px, so assets/img/avatar.webp is a 224 px (2x) WebP
    made from avatar.png.

    python tools/optimize_images.py            # squeeze new heroes, rebuild thumbnails and the avatar
    python tools/optimize_images.py --check    # change nothing; exit 1 if anything is over budget
    python tools/optimize_images.py --video-thumb SRC.png NAME   # make assets/img/posts/NAME-video-thumb.webp

Run it after hero_scenes.py makes a new or changed hero. Needs pngquant and cwebp
(`brew install pngquant webp`) and Pillow.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_IMG = ROOT / "assets" / "img" / "posts"
POSTS = ROOT / "_posts"
AVATAR_SRC = ROOT / "assets" / "img" / "avatar.png"
AVATAR_WEBP = ROOT / "assets" / "img" / "avatar.webp"

PNG_QUALITY = "70-90"
MAX_MAE = 2.0            # mean absolute error per channel (0-255) a squeezed hero may have
HERO_BUDGET = 200_000    # bytes; a palette hero card is about 120 to 170 KB
THUMB_WIDTH = 640        # the list card shows the image about 290 px wide, so this is 2x
THUMB_BUDGET = 40_000
AVATAR_SIZE = 224
AVATAR_BUDGET = 15_000
VIDEO_THUMB_WIDTH = 960  # the click-to-play facade (_includes/youtube-facade.html) fills the post column, 16:9
VIDEO_THUMB_BUDGET = 60_000


def is_palette_png(path: Path) -> bool:
    """True when the PNG is already 8-bit indexed (colour type 3), e.g. pngquant output."""
    head = path.read_bytes()[:26]
    return head[:8] == b"\x89PNG\r\n\x1a\n" and head[25] == 3


def mean_abs_error(a: Path, b: Path) -> float:
    from PIL import Image, ImageChops, ImageStat

    with Image.open(a) as ia, Image.open(b) as ib:
        diff = ImageChops.difference(ia.convert("RGB"), ib.convert("RGB"))
        return sum(ImageStat.Stat(diff).mean) / 3


def optimize_png(path: Path, quality: str = PNG_QUALITY, max_mae: float = MAX_MAE) -> tuple[int, int] | None:
    """Quantize a PNG in place. Returns (bytes before, bytes after), or None when it was left
    alone (already a palette PNG, no smaller, or too different from the original)."""
    if is_palette_png(path):
        return None
    before = path.stat().st_size
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / path.name
        subprocess.run(["pngquant", "--quality", quality, "--speed", "1", "--strip", "--force",
                        "--output", str(out), str(path)], check=False, capture_output=True)
        if not out.exists() or out.stat().st_size >= before:
            return None
        if mean_abs_error(path, out) > max_mae:
            return None
        after = out.stat().st_size
        shutil.copyfile(out, path)
    return before, after


def make_webp(src: Path, dst: Path, width: int, height: int = 0, quality: int = 82) -> None:
    """Resize to width (height 0 keeps the aspect ratio) and write a WebP."""
    subprocess.run(["cwebp", "-quiet", "-q", str(quality), "-m", "6", "-resize", str(width), str(height),
                    str(src), "-o", str(dst)], check=True)


def thumb_path(hero: Path) -> Path:
    return hero.with_name(hero.stem + f"-{THUMB_WIDTH}.webp")


def video_thumb_path(name: str) -> Path:
    return POSTS_IMG / f"{name}-video-thumb.webp"


def video_thumbs() -> list[Path]:
    return sorted(POSTS_IMG.glob("*-video-thumb.webp"))


def post_heroes() -> list[Path]:
    """The hero PNG each post names as its image."""
    found = []
    for post in sorted(POSTS.glob("*.md")):
        for rel in re.findall(r"^  path: (/assets/img/posts/\S+-hero\.png)$", post.read_text(), re.M):
            if (ROOT / rel.lstrip("/")).is_file():
                found.append(ROOT / rel.lstrip("/"))
    return found


def all_heroes() -> list[Path]:
    """Every hero card, including the ones of standalone pages (the witness page)."""
    return sorted(POSTS_IMG.glob("*-hero.png"))


def problems() -> list[str]:
    """What is over budget or missing, one line each."""
    out = []
    for hero in all_heroes():
        if not is_palette_png(hero):
            out.append(f"{hero.name} is not quantized")
        if hero.stat().st_size > HERO_BUDGET:
            out.append(f"{hero.name} is {hero.stat().st_size // 1000} KB (budget {HERO_BUDGET // 1000})")
    for hero in post_heroes():
        thumb = thumb_path(hero)
        if not thumb.is_file():
            out.append(f"{thumb.name} is missing")
        elif thumb.stat().st_size > THUMB_BUDGET:
            out.append(f"{thumb.name} is {thumb.stat().st_size // 1000} KB (budget {THUMB_BUDGET // 1000})")
    for thumb in video_thumbs():
        if thumb.stat().st_size > VIDEO_THUMB_BUDGET:
            out.append(f"{thumb.name} is {thumb.stat().st_size // 1000} KB (budget {VIDEO_THUMB_BUDGET // 1000})")
    if not AVATAR_WEBP.is_file():
        out.append(f"{AVATAR_WEBP.name} is missing")
    elif AVATAR_WEBP.stat().st_size > AVATAR_BUDGET:
        out.append(f"{AVATAR_WEBP.name} is {AVATAR_WEBP.stat().st_size // 1000} KB (budget {AVATAR_BUDGET // 1000})")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything is over budget")
    ap.add_argument("--video-thumb", nargs=2, metavar=("SRC", "NAME"),
                    help="make assets/img/posts/NAME-video-thumb.webp (960 px wide) from a 16:9 image")
    args = ap.parse_args(argv)

    if args.video_thumb:
        if not shutil.which("cwebp"):
            sys.exit("cwebp not found: brew install webp")
        out = video_thumb_path(args.video_thumb[1])
        make_webp(Path(args.video_thumb[0]), out, VIDEO_THUMB_WIDTH)
        print(f"{out.name}: {out.stat().st_size // 1000} KB")
        return 1 if out.stat().st_size > VIDEO_THUMB_BUDGET else 0

    if args.check:
        issues = problems()
        for line in issues:
            print(line)
        return 1 if issues else 0

    for tool in ("pngquant", "cwebp"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: brew install pngquant webp")
    saved = 0
    for hero in all_heroes():
        result = optimize_png(hero)
        if result:
            saved += result[0] - result[1]
            print(f"{hero.name}: {result[0] // 1000} KB -> {result[1] // 1000} KB")
    for hero in post_heroes():
        make_webp(hero, thumb_path(hero), THUMB_WIDTH)
    make_webp(AVATAR_SRC, AVATAR_WEBP, AVATAR_SIZE, AVATAR_SIZE, quality=85)
    print(f"saved {saved // 1000} KB on hero PNGs; thumbnails and {AVATAR_WEBP.name} rebuilt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
