#!/usr/bin/env python3
"""Build the site's favicon set: a bold double-V monogram on the brand blue to green gradient,
with the same soft highlight and glow as the hero cards. It replaces Chirpy's default icons by
using their file names in assets/img/favicons/ (the theme's _includes/favicons.html links them).

    python tools/favicon.py                      # write the icons and site.webmanifest
    python tools/favicon.py --preview out.html   # also write a page showing 16, 32 and 180 px on light and dark

Needs Playwright (renders the SVG at each size so small icons are anti-aliased by the browser) and Pillow.
"""
import argparse
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "favicons"

BLUE, MID, GREEN = "#0046ad", "#0077c8", "#00a651"
THEME_COLOR = BLUE

# name -> (pixel size, rounded corners?, mark scale). Android's maskable 512 and the iOS touch icon are
# full-bleed (the OS rounds or crops them), so their mark sits inside the safe zone.
PNGS = {
    "favicon-16x16.png": (16, True, 1.0),
    "favicon-32x32.png": (32, True, 1.0),
    "favicon-96x96.png": (96, True, 1.0),
    "apple-touch-icon.png": (180, False, 0.8),
    "web-app-manifest-192x192.png": (192, False, 0.8),
    "web-app-manifest-512x512.png": (512, False, 0.8),
}
ICO_SIZES = [(16, 16), (32, 32), (48, 48)]

MANIFEST = """---
layout: compress
---

{%% assign favicon_path = "/assets/img/favicons" | relative_url %%}

{
  "name": "{{ site.title }}",
  "short_name": "{{ site.title }}",
  "description": "{{ site.description }}",
  "icons": [
    {
      "src": "{{ favicon_path }}/web-app-manifest-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "{{ favicon_path }}/web-app-manifest-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ],
  "start_url": "{{ '/index.html' | relative_url }}",
  "theme_color": "%(theme)s",
  "background_color": "#ffffff",
  "display": "standalone"
}
"""


def mark_svg(rounded: bool = True, scale: float = 1.0) -> str:
    """The icon as an SVG on a 512 unit square."""
    radius = 112 if rounded else 0
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <title>Vinay Vobbilichetty</title>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{BLUE}"/>
      <stop offset="0.48" stop-color="{MID}"/>
      <stop offset="1" stop-color="{GREEN}"/>
    </linearGradient>
    <radialGradient id="hi" cx="0.85" cy="0.15" r="0.55">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.32"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="gl" cx="0.08" cy="0.98" r="0.6">
      <stop offset="0" stop-color="#00ffb3" stop-opacity="0.34"/>
      <stop offset="1" stop-color="#00ffb3" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="512" height="512" rx="{radius}" fill="url(#g)"/>
  <rect width="512" height="512" rx="{radius}" fill="url(#hi)"/>
  <rect width="512" height="512" rx="{radius}" fill="url(#gl)"/>
  <g transform="translate(256 256) scale({scale}) translate(-256 -256)" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="52">
    <path d="M80 134 L154 374 L228 134" stroke="#ffffff"/>
    <path d="M284 134 L358 374 L432 134" stroke="#bdfbe0"/>
  </g>
</svg>
"""


def render_png(svg: str, size: int):
    """Render the SVG at size x size with a transparent background; returns a Pillow image."""
    from PIL import Image
    from playwright.sync_api import sync_playwright

    sized = svg.replace('viewBox="0 0 512 512" width="512" height="512"',
                        f'viewBox="0 0 512 512" width="{size}" height="{size}"')
    html = f"<html><body style='margin:0;background:transparent'><div style='width:{size}px;height:{size}px'>" \
           f"{sized}</div></body></html>"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": size, "height": size})
        page.set_content(html)
        data = page.screenshot(omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size})
        browser.close()
    return Image.open(io.BytesIO(data)).convert("RGBA")


def build(out: Path = OUT) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    svg_path = out / "favicon.svg"
    svg_path.write_text(mark_svg(rounded=True))
    written.append(svg_path)
    for name, (size, rounded, scale) in PNGS.items():
        img = render_png(mark_svg(rounded, scale), size)
        img.save(out / name, optimize=True)
        written.append(out / name)
    big = render_png(mark_svg(True, 1.0), 256)
    big.save(out / "favicon.ico", sizes=ICO_SIZES)
    written.append(out / "favicon.ico")
    manifest = out / "site.webmanifest"
    manifest.write_text(MANIFEST % {"theme": THEME_COLOR})
    written.append(manifest)
    return written


def preview_html(out: Path = OUT) -> str:
    """A page that shows the icons as a browser tab, a bookmark and a home-screen icon, on light and dark."""
    import base64

    def uri(name: str) -> str:
        return "data:image/png;base64," + base64.b64encode((out / name).read_bytes()).decode()

    def tile(theme: str) -> str:
        return f"""<section class="{theme}">
  <h2>{theme.title()} browser chrome</h2>
  <div class="tab"><img src="{uri('favicon-16x16.png')}" width="16" height="16" alt="16 px"><span>Vinay Vobbilichetty</span></div>
  <div class="row">
    <figure><img src="{uri('favicon-16x16.png')}" width="16" height="16" alt=""><figcaption>16 px</figcaption></figure>
    <figure><img src="{uri('favicon-32x32.png')}" width="32" height="32" alt=""><figcaption>32 px</figcaption></figure>
    <figure><img src="{uri('apple-touch-icon.png')}" width="180" height="180" style="border-radius:40px" alt=""><figcaption>180 px home screen</figcaption></figure>
    <figure><img src="{uri('web-app-manifest-512x512.png')}" width="96" height="96" style="border-radius:22px" alt=""><figcaption>512 px app icon, shown at 96</figcaption></figure>
  </div>
</section>"""

    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Favicon preview</title>
<style>
  body {{ margin: 0; font: 15px system-ui, sans-serif; display: grid; grid-template-columns: 1fr 1fr; min-height: 100vh; }}
  section {{ padding: 2rem; }}
  .light {{ background: #f9f5ea; color: #10203b; }}
  .dark {{ background: #0d1117; color: #eaf1fb; }}
  h2 {{ font-size: 1rem; margin: 0 0 1.2rem; }}
  .tab {{ display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 10px 10px 0 0; }}
  .light .tab {{ background: #fff; }} .dark .tab {{ background: #1c2330; }}
  .row {{ display: flex; align-items: flex-end; gap: 2rem; margin-top: 1.5rem; flex-wrap: wrap; }}
  figure {{ margin: 0; text-align: center; }} figcaption {{ margin-top: .5rem; font-size: 12px; opacity: .7; }}
  @media (max-width: 720px) {{ body {{ grid-template-columns: 1fr; }} }}
</style>
{tile('light')}{tile('dark')}"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--preview", type=Path, help="also write a preview page to this path")
    args = ap.parse_args(argv)
    for path in build():
        print(path.relative_to(ROOT))
    if args.preview:
        args.preview.write_text(preview_html())
        print(args.preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())
