#!/usr/bin/env python3
"""Render a post's 1200x630 hero / social card in the site's house style.

The card is a dark panel with the post's accent gradient as a left rail, a
small uppercase kicker, one big headline, a one-line subtitle, and a footer
with the post title and the site name. Colours come from the same
_data/accents.yml palettes the post itself uses, and the fonts are the
self-hosted Space Grotesk files, so the card matches the page.

    python tools/hero.py --accent coral \\
        --kicker "Meeting recap · Local inference" \\
        --headline "Who owes what by when" \\
        --sub "A recording in, a transcript and an action list out." \\
        --title "The Bridge Call Nobody Writes Up" \\
        --out assets/img/posts/meeting-recap-hero.png

Pass --html to write the card's HTML instead of a PNG (no browser needed).

Requires Playwright for PNG output (same as tools/shot.py):
    pip install playwright && playwright install chromium
"""
import argparse
import base64
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCENTS = ROOT / "_data" / "accents.yml"
FONTS = ROOT / "assets" / "fonts"
WIDTH, HEIGHT = 1200, 630
SITE = "vinayvobbili.github.io"


def load_palette(key: str, path: Path = ACCENTS) -> dict[str, str]:
    """Read one palette's fields from accents.yml.

    The file is flat (`key:` then indented `field: "value"` lines), so a small
    line parser keeps this tool free of a YAML dependency.
    """
    palettes: dict[str, dict[str, str]] = {}
    current = None
    for line in path.read_text().splitlines():
        top = re.match(r"^([a-z][a-z0-9_-]*):", line)
        if top:
            current = palettes.setdefault(top.group(1), {})
            continue
        field = re.match(r'^\s+([a-z]+):\s*"(.*)"', line)
        if field and current is not None:
            current[field.group(1)] = field.group(2)
    if key not in palettes:
        raise SystemExit(f"unknown accent {key!r}; known: {', '.join(sorted(palettes))}")
    return palettes[key]


def gradient_stops(grad: str) -> list[str]:
    """The hex colours of a CSS linear-gradient, in order."""
    return re.findall(r"#[0-9a-fA-F]{6}", grad)


def card_html(*, palette: dict[str, str], kicker: str, headline: str, sub: str, title: str) -> str:
    stops = gradient_stops(palette["grad"])
    kicker_colour = stops[-1] if stops else palette["accent"]
    # Inlined as data URIs: a page loaded with set_content can't fetch file:// fonts.
    faces = "\n".join(
        f"@font-face {{ font-family: 'Space Grotesk'; font-weight: {w}; src: url('data:font/woff2;base64,"
        f"{base64.b64encode((FONTS / f'space-grotesk-{w}.woff2').read_bytes()).decode()}') format('woff2'); }}"
        for w in (400, 700)
    )
    e = html.escape
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
{faces}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {WIDTH}px; height: {HEIGHT}px; }}
body {{
  font-family: 'Space Grotesk', sans-serif;
  color: #f8f5f0;
  background:
    radial-gradient(circle at 82% 18%, {palette["glow"]} 0, transparent 42%),
    radial-gradient(circle at 10% 100%, {palette["shadow"]} 0, transparent 50%),
    linear-gradient(135deg, #1c1a1f 0%, #24201f 100%);
  position: relative; overflow: hidden;
  display: flex; flex-direction: column; padding: 76px 76px 74px 78px;
}}
.rail {{ position: absolute; left: 0; top: 0; bottom: 0; width: 14px; background: {palette["grad"]}; }}
.kicker {{
  font-weight: 700; font-size: 26px; letter-spacing: 0.08em; text-transform: uppercase;
  color: {kicker_colour};
}}
.main {{ flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 22px; }}
.headline {{ font-weight: 700; font-size: 88px; line-height: 1.02; letter-spacing: -0.01em; }}
.sub {{ font-weight: 400; font-size: 36px; line-height: 1.25; color: #dcd6cf; }}
.footer {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 25px; }}
.footer .title {{ color: #a39a92; }}
.footer .site {{ font-weight: 700; }}
</style></head><body>
<div class="rail"></div>
<div class="kicker">{e(kicker)}</div>
<div class="main"><div class="headline">{e(headline)}</div><div class="sub">{e(sub)}</div></div>
<div class="footer"><span class="title">{e(title)}</span><span class="site">{SITE}</span></div>
</body></html>
"""


def render_png(markup: str, out: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright not found. `pip install playwright && playwright install chromium`")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        page.set_content(markup, wait_until="load")
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT})
        browser.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--accent", required=True, help="palette key from _data/accents.yml")
    ap.add_argument("--kicker", required=True)
    ap.add_argument("--headline", required=True)
    ap.add_argument("--sub", required=True)
    ap.add_argument("--title", required=True, help="post title, shown in the footer")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--html", action="store_true", help="write the HTML instead of a PNG")
    args = ap.parse_args(argv)

    markup = card_html(
        palette=load_palette(args.accent),
        kicker=args.kicker,
        headline=args.headline,
        sub=args.sub,
        title=args.title,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.html:
        args.out.write_text(markup)
    else:
        render_png(markup, args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
