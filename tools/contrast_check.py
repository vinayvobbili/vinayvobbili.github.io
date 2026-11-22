#!/usr/bin/env python3
"""Measure text contrast on a served copy of the site in every theme choice.

Chirpy 7 sets `data-bs-theme` on <html> (light or dark; the System choice just resolves to the
OS setting and leaves `data-theme-persisted` off). This opens a page once per case, computes the
colour of the sidebar title, subtitle, nav links, body text and links, and the WCAG contrast
against the real background (for the sidebar, the worse of the two gradient end stops).

    python tools/contrast_check.py http://127.0.0.1:4000 /posts/billing-header-kv-cache/
    python tools/contrast_check.py https://vinayvobbili.github.io      # the live site

Exit status is 1 when any pair is under 4.5:1 (3:1 for large text). Needs Playwright (see shot.py).
"""
import sys

WCAG_AA = 4.5
WCAG_AA_LARGE = 3.0

# name, selector, background source ("page" or "sidebar"), minimum ratio
TARGETS = [
    ("sidebar title", "#sidebar .site-title", "sidebar", WCAG_AA_LARGE),
    ("sidebar subtitle", "#sidebar .site-subtitle", "sidebar", WCAG_AA),
    ("sidebar nav link", "#sidebar .nav-item:not(.active) .nav-link", "sidebar", WCAG_AA),
    ("sidebar nav active", "#sidebar .nav-item.active .nav-link", "sidebar", WCAG_AA),
    ("sidebar footer icon", "#sidebar .sidebar-bottom a", "sidebar", WCAG_AA),
    ("body text", "main .content p, main #post-list .card-text", "page", WCAG_AA),
    ("heading", "main .content h2, main .card-title", "page", WCAG_AA),
    ("link", "main .content a", "page", WCAG_AA),
]

# theme choice -> (OS colour scheme, localStorage `theme` value or None for System)
CASES = {
    "light": ("light", "light"),
    "dark": ("light", "dark"),
    "system (OS light)": ("light", None),
    "system (OS dark)": ("dark", None),
}


def parse_rgb(css: str) -> tuple[float, float, float, float]:
    """'rgb(1, 2, 3)', 'rgba(1,2,3,.5)' or 'rgb(1 2 3 / 50%)' -> (r, g, b, alpha)."""
    inner = css[css.index("(") + 1:css.rindex(")")]
    parts = [p for p in inner.replace("/", " ").replace(",", " ").split() if p]
    r, g, b = (float(x) for x in parts[:3])
    alpha = 1.0
    if len(parts) > 3:
        alpha = float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1)
    return r, g, b, alpha


def blend(fg: tuple, bg: tuple) -> tuple[float, float, float]:
    """Composite an rgba foreground over an opaque background."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def luminance(rgb) -> float:
    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def worst_contrast(fg_css: str, backgrounds: list[tuple], overlay_css: str = "") -> float:
    """Worst ratio of the text colour over each background; overlay_css is the element's own
    (translucent) background, laid over the backdrop first."""
    fg = parse_rgb(fg_css)
    overlay = parse_rgb(overlay_css) if overlay_css else (0, 0, 0, 0)
    worst = 99.0
    for bg in backgrounds:
        backdrop = blend(overlay, bg)
        worst = min(worst, contrast(blend(fg, backdrop), backdrop))
    return worst


GRADIENT_JS = """
() => {
  const sb = document.querySelector('#sidebar');
  const stops = sb ? getComputedStyle(sb).backgroundImage.match(/rgba?\\([^)]*\\)/g) : null;
  return {
    pageBg: getComputedStyle(document.body).backgroundColor,
    stops: stops || [getComputedStyle(sb || document.body).backgroundColor],
  };
}
"""

COLOR_JS = """
(sel) => {
  const el = document.querySelector(sel);
  return el ? [getComputedStyle(el).color, getComputedStyle(el).backgroundColor] : null;
}
"""


def measure(page, base: str, path: str, scheme: str, stored):
    page.emulate_media(color_scheme=scheme)
    page.add_init_script(
        "try { localStorage.removeItem('theme'); "
        + (f"localStorage.setItem('theme', '{stored}'); " if stored else "")
        + "} catch (e) {}"
    )
    page.goto(base.rstrip("/") + path, wait_until="load")
    page.wait_for_timeout(900)  # the sidebar colours transition for 0.3 s
    bgs = page.evaluate(GRADIENT_JS)
    page_bg = parse_rgb(bgs["pageBg"])[:3]
    sidebar_bgs = [parse_rgb(s)[:3] for s in bgs["stops"]]
    rows = []
    for name, sel, where, minimum in TARGETS:
        found = page.evaluate(COLOR_JS, sel)
        if found is None:
            continue
        color, own_bg = found
        backgrounds = sidebar_bgs if where == "sidebar" else [page_bg]
        overlay = own_bg if where == "sidebar" else ""
        rows.append((name, color, worst_contrast(color, backgrounds, overlay), minimum))
    return page.evaluate("document.documentElement.dataset.bsTheme"), page_bg, rows


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    if not argv:
        sys.exit(__doc__)
    base, paths = argv[0], argv[1:] or ["/"]
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path in paths:
            for label, (scheme, stored) in CASES.items():
                ctx = browser.new_context(viewport={"width": 1280, "height": 900})
                page = ctx.new_page()
                theme, page_bg, rows = measure(page, base, path, scheme, stored)
                print(f"{path}  [{label}]  data-bs-theme={theme}  page bg rgb{tuple(int(c) for c in page_bg)}")
                for name, color, ratio, minimum in rows:
                    flag = "ok  " if ratio >= minimum else "FAIL"
                    failed += ratio < minimum
                    print(f"  {flag} {name:18} {ratio:5.2f}:1 (min {minimum})  {color}")
                ctx.close()
        browser.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
