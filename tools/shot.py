#!/usr/bin/env python3
"""Screenshot one or more pages from a locally-served preview and report any
failed / external-font requests — a self-review pass before pushing.

Pairs with tools/preview.sh:
    tools/preview.sh &                 # serve ./.preview on :8888
    python tools/shot.py http://localhost:8888 /posts/foo/ /attestq/

For each path it writes .preview/shot_<name>.png and prints, per page:
  - the computed font-family of the first <h1>
  - whether "Space Grotesk" actually loaded (catches broken @font-face)
  - any requests to fonts.googleapis.com / gstatic (should be none once
    fonts are self-hosted) and any failed requests.

Light and dark are both captured (?mode via prefers-color-scheme).

Requires Playwright (pip install playwright && playwright install chromium).
If it's not on PATH, run with an explicit interpreter, e.g.
    /path/to/venv/bin/python tools/shot.py ...
"""
import os
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright not found. `pip install playwright && playwright install chromium`")

OUTDIR = os.path.join(os.path.dirname(__file__), "..", ".preview")


def main(argv):
    if len(argv) < 2:
        sys.exit("usage: shot.py <base_url> <path> [path ...]")
    base, paths = argv[0], argv[1:]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path in paths:
            name = path.strip("/").replace("/", "_") or "index"
            for scheme in ("light", "dark"):
                ctx = browser.new_context(
                    viewport={"width": 1280, "height": 1300},
                    color_scheme=scheme,
                    reduced_motion="reduce",
                )
                pg = ctx.new_page()
                bad = []
                pg.on("requestfailed", lambda r: bad.append("FAILED " + r.url))
                pg.on("request", lambda r: bad.append("GOOGLE " + r.url)
                      if "googleapis" in r.url or "gstatic" in r.url else None)
                pg.goto(base + path, wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(600)
                info = pg.eval_on_selector(
                    "h1",
                    "el => getComputedStyle(el).fontFamily.split(',')[0] + "
                    "' | SpaceGrotesk-loaded=' + document.fonts.check('700 16px \"Space Grotesk\"')",
                )
                out = os.path.join(OUTDIR, f"shot_{name}_{scheme}.png")
                pg.screenshot(path=out)
                flags = f"  !! {bad}" if bad else ""
                print(f"[{scheme}] {path}: h1 {info}{flags} -> {out}")
                ctx.close()
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
