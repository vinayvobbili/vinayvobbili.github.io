#!/usr/bin/env python3
"""Check the click-to-play video (_includes/youtube-facade.html) on a served page, local or live.

    python tools/facade_check.py http://127.0.0.1:4000 /posts/three-phases-of-rag-quality/
    python tools/facade_check.py https://vinayvobbili.github.io /posts/three-phases-of-rag-quality/ --shots out/

For light and dark it loads the page, reports every request to a host other than the page's own
(a clean facade makes none to YouTube), screenshots the player, clicks it, and confirms an
iframe on www.youtube-nocookie.com replaced the thumbnail. With --shots DIR it writes
facade-light.png, facade-dark.png and facade-playing.png there. Exit 1 on any problem.
Needs Playwright (pip install playwright && playwright install chromium).
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

EMBED_HOST = "www.youtube-nocookie.com"


def check(base: str, path: str, shots: Path | None = None) -> list[str]:
    """Problems found on base+path, one line each; an empty list means the facade is sound."""
    from playwright.sync_api import sync_playwright

    problems = []
    own = urlparse(base).netloc
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": 1280, "height": 1100}, color_scheme=scheme)
            page = ctx.new_page()
            hosts = []
            page.on("request", lambda r: hosts.append(urlparse(r.url).netloc))
            page.goto(base + path, wait_until="networkidle", timeout=45000)
            fig = page.locator(".yt-facade").first
            if fig.count() == 0:
                problems.append(f"{scheme}: no .yt-facade on {path}")
                continue
            fig.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            foreign = sorted({h for h in hosts if h and h != own and not h.startswith("127.0.0.1")})
            bad = [h for h in foreign if "youtube" in h or "ytimg" in h or "google" in h]
            if bad:
                problems.append(f"{scheme}: requests to {bad} before the click")
            if page.locator(".yt-facade iframe").count():
                problems.append(f"{scheme}: an iframe is on the page before the click")
            if shots:
                shots.mkdir(parents=True, exist_ok=True)
                fig.screenshot(path=str(shots / f"facade-{scheme}.png"))
            fig.locator("a.yt-facade__play").click()
            page.wait_for_selector(".yt-facade iframe", timeout=5000)
            src = fig.locator("iframe").get_attribute("src")
            if urlparse(src).netloc != EMBED_HOST or "autoplay=1" not in src:
                problems.append(f"{scheme}: iframe src is {src}")
            if shots and scheme == "light":
                fig.screenshot(path=str(shots / "facade-playing.png"))
            chapter = fig.locator("ul.yt-facade__chapters a").nth(1)
            if chapter.count():
                seconds = chapter.get_attribute("data-yt-start")
                chapter.click()
                src = fig.locator("iframe").get_attribute("src")
                if f"start={seconds}" not in src:
                    problems.append(f"{scheme}: chapter click left the iframe at {src}")
            ctx.close()
        browser.close()
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("base", help="site root, e.g. http://127.0.0.1:4000")
    ap.add_argument("path", help="page path, e.g. /posts/three-phases-of-rag-quality/")
    ap.add_argument("--shots", type=Path, help="directory for the screenshots")
    args = ap.parse_args(argv)
    problems = check(args.base.rstrip("/"), args.path, args.shots)
    for line in problems:
        print(line)
    if not problems:
        print("facade ok: no YouTube request before the click, nocookie iframe after")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
