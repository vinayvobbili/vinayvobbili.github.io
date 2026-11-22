"""Drawing kit shared by the hero cards and the animated flow SVGs.

Everything here returns SVG markup (strings) for a 1100x330 diagram canvas, the same
size as tools/hero_diagram.py draws on: gradient nodes, white tiles, panels, pills,
arrows, line icons, and a small `Ctx` that turns "lit" state into SMIL when a cycle
length is set (the animated flow SVGs) and into plain, fully-lit markup when it is
not (the static PNG cards).

Text goes through `T()`, which records the widest the text may be as `data-maxw`, so
the render check in test_hero_scenes.py can measure every label against its box.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero_diagram as hd  # noqa: E402

INK, MUTED = hd.INK, hd.MUTED
GREEN, GREEN_LIGHT, AMBER, AMBER_LIGHT = hd.GREEN, hd.GREEN_LIGHT, hd.AMBER, hd.AMBER_LIGHT
RED, RED_LIGHT = "#dc2626", "#fb7185"
FONT = hd.FONT
font_faces = hd.font_faces

esc = html.escape

# gradient name -> (from, to); drawn as url(#g-<name>) once per document by defs()
COLORS = {
    "indigo": ("#4f46e5", "#8b5cf6"), "violet": ("#7c3aed", "#c084fc"), "cyan": ("#0891b2", "#22d3ee"),
    "pink": ("#db2777", "#fb7185"), "green": ("#15803d", "#34d399"), "amber": ("#f59e0b", "#fcd34d"),
    "red": ("#b91c1c", "#f87171"), "blue": ("#1d4ed8", "#60a5fa"), "teal": ("#0f766e", "#2dd4bf"),
    "slate": ("#334155", "#64748b"), "orange": ("#ea580c", "#fb923c"), "lime": ("#4d7c0f", "#a3e635"),
    "sky": ("#0369a1", "#38bdf8"), "plum": ("#86198f", "#e879f9"), "ink": ("#1e1b4b", "#4338ca"),
}
ARROW_COLORS = {"white": "#ffffff", "green": GREEN_LIGHT, "amber": AMBER_LIGHT, "red": RED_LIGHT,
                "ink": "#1e1b4b", "sky": "#7dd3fc"}


def g(name: str) -> str:
    return f"url(#g-{name})"


def defs() -> str:
    grads = "\n".join(
        f'<linearGradient id="g-{n}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/>'
        f'<stop offset="1" stop-color="{b}"/></linearGradient>' for n, (a, b) in COLORS.items())
    markers = "".join(
        f'<marker id="ar-{n}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        f'<path d="M1 1l8 4-8 4z" fill="{c}"/></marker>' for n, c in ARROW_COLORS.items())
    return f"""<defs>
{grads}
<filter id="shadow" x="-25%" y="-70%" width="150%" height="280%"><feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="#1e1b4b" flood-opacity=".35"/></filter>
<filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="7"/></filter>
{markers}
</defs>"""


# --- icons (24x24, stroked) ------------------------------------------------

ICONS = {
    "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "doc": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M9.5 12.5h6M9.5 16h6M9.5 9h2"/>',
    "audit": '<rect x="5" y="4.5" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5"/><path d="M8.7 18v-3M12 18v-6M15.3 18v-4"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5.5 5.5"/>',
    "gauge": '<path d="M4.5 16a7.5 7.5 0 0 1 15 0"/><path d="M12 16l3.5-4.5"/><circle cx="12" cy="16" r="1"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l2.5-2.5a4 4 0 0 0-5.7-5.7L11 7.3"/><path d="M14 10a4 4 0 0 0-5.7 0l-2.5 2.5a4 4 0 0 0 5.7 5.7L13 16.7"/>',
    "warn": '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.2" r=".6"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
    "ask": '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.6 2.2c-.8.5-1.2 1-1.2 1.9"/><circle cx="12" cy="17" r=".6"/>',
    "x": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "bolt": '<path d="M13 3L5 13.5h6L10 21l8-10.5h-6z"/>',
    "user": '<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-4 3.6-6 7-6s6.2 2 7 6"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "layers": '<path d="M12 4l8 4-8 4-8-4z"/><path d="M4 12l8 4 8-4"/><path d="M4 16l8 4 8-4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "db": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>',
    "cpu": '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    "scissors": '<circle cx="6.5" cy="6.5" r="2.5"/><circle cx="6.5" cy="17.5" r="2.5"/><path d="M8.5 8l11 9M8.5 16l11-9"/>',
    "filter": '<path d="M4 5h16l-6 7.5V19l-4-2v-4.5z"/>',
    "play": '<path d="M8 5l11 7-11 7z"/>',
    "film": '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M8 5v14M16 5v14M4 9h4M4 15h4M16 9h4M16 15h4"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4"/>',
    "loop": '<path d="M20 12a8 8 0 1 1-2.5-5.8"/><path d="M20 4v4.5h-4.5"/>',
    "stop": '<path d="M8 4h8l4 4v8l-4 4H8l-4-4V8z"/><path d="M8.5 12h7"/>',
    "bug": '<ellipse cx="12" cy="14" rx="4.5" ry="6"/><path d="M12 8V5M8 5l2 2.5M16 5l-2 2.5M4 12h4M16 12h4M5 19l3-2M19 19l-3-2"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.7" cy="6" r="1"/><circle cx="4.7" cy="12" r="1"/><circle cx="4.7" cy="18" r="1"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    "mask": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><path d="M4 4l16 16"/>',
    "network": '<circle cx="12" cy="5" r="2.4"/><circle cx="5" cy="18" r="2.4"/><circle cx="19" cy="18" r="2.4"/><path d="M11 7l-5 9M13 7l5 9M7.5 18h9"/>',
    "tag": '<path d="M9 4L7 20M17 4l-2 16M4 9h16M3.5 15h16"/>',
    "chat": '<path d="M4 5h16v11H11l-5 4v-4H4z"/>',
    "folder": '<path d="M3.5 7a2 2 0 0 1 2-2H10l2 2.5h6.5a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    "code": '<path d="M8 8l-4.5 4L8 16M16 8l4.5 4L16 16M13.5 5.5l-3 13"/>',
    "compare": '<path d="M7 4v12M7 16l-3-3M7 16l3-3M17 20V8M17 8l-3 3M17 8l3 3"/>',
    "pencil": '<path d="M4 20l1-4L16.5 4.5a2 2 0 0 1 3 3L8 19z"/>',
    "cloud": '<path d="M7 18a4 4 0 0 1-.5-7.9A5.5 5.5 0 0 1 17 8.5a4.8 4.8 0 0 1 0 9.5z"/>',
    "laptop": '<rect x="5" y="5" width="14" height="10" rx="1.5"/><path d="M3 19h18"/>',
    "flag": '<path d="M6 21V4M6 5h11l-2.5 4 2.5 4H6"/>',
    "sparkle": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M18.5 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
    "box": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "hash": '<path d="M9 4L7 20M17 4l-2 16M4 9h16M3.5 15h16"/>',
    "wave": '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2"/>',
    "trash": '<path d="M5 7h14M10 7V4.5h4V7M7 7l1 13h8l1-13"/>',
}


def icon(name: str, x: float, y: float, size: float, stroke: str = "#fff", sw: float = 2) -> str:
    return (f'<g transform="translate({x},{y}) scale({size / 24:.4f})" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


# --- text and shapes -------------------------------------------------------

def T(x: float, y: float, s: str, size: float = 16, fill: str = INK, weight: int = 700, anchor: str = "start",
      maxw: float | None = None, op: float | None = None, deco: str | None = None) -> str:
    """One line of text. `maxw` is the widest it may render; the render check enforces it."""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    m = f' data-maxw="{maxw:g}"' if maxw else ""
    o = f' opacity="{op}"' if op is not None else ""
    d = f' text-decoration="{deco}"' if deco else ""
    return (f'<text x="{x:g}" y="{y:g}"{a} {FONT} font-weight="{weight}" font-size="{size:g}" '
            f'fill="{fill}"{m}{o}{d}>{esc(s)}</text>')


def lines(x: float, y: float, rows: list[str], size: float = 15, lh: float = 22, fill: str = INK,
          weight: int = 700, anchor: str = "start", maxw: float | None = None) -> str:
    return "".join(T(x, y + i * lh, r, size, fill, weight, anchor, maxw) for i, r in enumerate(rows))


def rect(x, y, w, h, r=0, fill="none", extra="") -> str:
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}" fill="{fill}" {extra}/>'


def panel(x, y, w, h, r=18, fill="#fff", op=.96) -> str:
    """A white card with the soft drop shadow."""
    box = rect(x, y, w, h, r, fill, f'fill-opacity="{op}"')
    return f'<g filter="url(#shadow)">{box}</g>'


def header_panel(x, y, w, h, grad: str, title: str, ico: str | None = None, *, hh: float = 42, r: float = 20,
                 tcolor: str = "#fff", size: float = 19) -> str:
    """White card whose top band is a gradient with an icon and a title."""
    band = (f'<path d="M{x:g} {y + r:g}a{r:g} {r:g} 0 0 1 {r:g}-{r:g}h{w - 2 * r:g}a{r:g} {r:g} 0 0 1 {r:g} {r:g}'
            f'v{hh - r:g}H{x:g}z" fill="{g(grad)}"/>')
    tx = x + 18
    out = panel(x, y, w, h, r) + band
    if ico:
        out += icon(ico, x + 14, y + (hh - 26) / 2, 26, tcolor, 2.2)
        tx = x + 50
    return out + T(tx, y + hh / 2 + size * .35, title, size, tcolor, maxw=w - (tx - x) - 12)


def node(x, y, w, h, grad: str, ico: str, title: str, sub: str | None = None, *, r: int = 22,
         tsize: float = 20, ssize: float = 13.5) -> str:
    """Gradient block: icon in a soft disc, title, optional subtitle, all centred."""
    cx = x + w / 2
    out = f'<g filter="url(#shadow)">{rect(x, y, w, h, r, g(grad))}</g>'
    if h >= 104:
        cy = y + 38
        out += f'<circle cx="{cx:g}" cy="{cy:g}" r="24" fill="#fff" fill-opacity=".2"/>{icon(ico, cx - 17, cy - 17, 34, sw=2.2)}'
        ty = y + h - (27 if sub else 15)
        out += T(cx, ty, title, tsize, "#fff", anchor="middle", maxw=w - 16)
        if sub:
            out += T(cx, ty + 19, sub, ssize, "#fff", 400, "middle", maxw=w - 16, op=.95)
    else:  # short node: icon left of the text
        out += f'<circle cx="{x + 34:g}" cy="{y + h / 2:g}" r="20" fill="#fff" fill-opacity=".22"/>'
        out += icon(ico, x + 21, y + h / 2 - 13, 26, sw=2.2)
        ty = y + h / 2 + (-3 if sub else 7)
        out += T(x + 64, ty, title, tsize, "#fff", maxw=w - 74)
        if sub:
            out += T(x + 64, ty + 20, sub, ssize, "#fff", 400, maxw=w - 74, op=.95)
    return out


def tile(x, y, w, h, grad: str, ico: str, title: str, sub: str | None = None, *, tsize: float = 19,
         ssize: float = 14) -> str:
    """White card with a gradient icon disc on the left and a title (and subtitle) beside it."""
    cy = y + h / 2
    rr = min(27, h / 2 - 10)
    out = panel(x, y, w, h, 18) + f'<circle cx="{x + 14 + rr:g}" cy="{cy:g}" r="{rr:g}" fill="{g(grad)}"/>'
    out += icon(ico, x + 14 + rr - rr * .6, cy - rr * .6, rr * 1.2)
    tx = x + 28 + 2 * rr
    if sub:
        out += T(tx, cy - 3, title, tsize, INK, maxw=w - (tx - x) - 10)
        out += T(tx, cy + 19, sub, ssize, MUTED, 400, maxw=w - (tx - x) - 10)
    else:
        out += T(tx, cy + tsize * .35, title, tsize, INK, maxw=w - (tx - x) - 10)
    return out


def pill(x, y, w, text: str, *, h: float = 38, fill: str = "#fff", color: str = INK, size: float = 15,
         ico: str | None = None, ico_color: str = "#7c3aed", shadow: bool = True, op: float = .96) -> str:
    box = rect(x, y, w, h, h / 2, fill, f'fill-opacity="{op}"')
    out = f'<g filter="url(#shadow)">{box}</g>' if shadow else box
    tx = x + w / 2
    anchor = "middle"
    avail = w - 26
    if ico:
        out += icon(ico, x + 12, y + (h - 24) / 2, 24, ico_color, 2.2)
        tx, anchor, avail = x + 46, "start", w - 58
    return out + T(tx, y + h / 2 + size * .36, text, size, color, anchor=anchor, maxw=avail)


def chip(x, y, w, h, text: str, fill: str, stroke: str, color: str, size: float = 14, weight: int = 700) -> str:
    return (rect(x, y, w, h, h / 2, fill, f'stroke="{stroke}" stroke-width="1.5"')
            + T(x + w / 2, y + h / 2 + size * .36, text, size, color, weight, "middle", maxw=w - 14))


def arrow(d: str, color: str = "white", width: float = 3.5, dash: str | None = None, op: float = .85,
          head: bool = True) -> str:
    da = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#ar-{color})"' if head else ""
    return (f'<path d="{d}" fill="none" stroke="{ARROW_COLORS[color]}" stroke-opacity="{op}" stroke-width="{width:g}" '
            f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')


def diamond(cx, cy, r, grad: str, ico: str, *, isize: float = 36) -> str:
    d = f"M{cx} {cy - r} L{cx + r} {cy} L{cx} {cy + r} L{cx - r} {cy} Z"
    return (f'<g filter="url(#shadow)"><path d="{d}" fill="{g(grad)}" stroke="#fff" stroke-width="3" stroke-linejoin="round"/></g>'
            f'<circle cx="{cx}" cy="{cy}" r="24" fill="#fff" fill-opacity=".22"/>{icon(ico, cx - isize / 2, cy - isize / 2, isize, sw=2.2)}')


def diamond_path(cx, cy, r) -> str:
    return f"M{cx} {cy - r} L{cx + r} {cy} L{cx} {cy + r} L{cx - r} {cy} Z"


def bar(x, y, w, h, grad: str) -> str:
    return rect(x, y, w, h, min(h / 2, w / 3), g(grad))


# --- animation ---------------------------------------------------------------

class Ctx:
    """Static (cycle=0) or animated (cycle in seconds) drawing context.

    Scene code asks for things to be "shown" during time spans; in static mode they are
    just drawn, so the PNG card shows the finished, fully-lit diagram.
    """

    def __init__(self, cycle: float = 0.0):
        self.cycle = cycle

    @property
    def animated(self) -> bool:
        return self.cycle > 0

    def _f(self, t: float) -> float:
        return max(0.0, min(1.0, t / self.cycle))

    def animate(self, attr: str, points: list[tuple[float, str | float]]) -> str:
        times, values = hd.keyframes([(self._f(t), v) for t, v in points])
        return (f'<animate attributeName="{attr}" dur="{self.cycle:g}s" repeatCount="indefinite" '
                f'calcMode="linear" keyTimes="{times}" values="{values}"/>')

    def _track(self, spans: list[tuple[float, float]], lo: float, hi: float, fade: float):
        pts: list[tuple[float, float]] = [(0.0, lo)]
        for a, b in spans:
            b = min(b, self.cycle - fade)
            pts += [(a, lo), (a + fade, hi), (b, hi), (b + fade, lo)]
        pts.append((self.cycle, lo))
        return sorted(pts, key=lambda p: p[0])

    def show(self, markup: str, *spans: tuple[float, float], lo: float = 0.0, hi: float = 1.0,
             fade: float = .3) -> str:
        """Visible (opacity hi) during each (start, end) span, `lo` otherwise. Static: drawn as is."""
        if not self.animated:
            return markup
        return f'<g opacity="{lo:g}">{markup}{self.animate("opacity", self._track(list(spans), lo, hi, fade))}</g>'

    def only_static(self, markup: str) -> str:
        """Drawn in the static card only (the animated version shows it through show())."""
        return "" if self.animated else markup

    def only_animated(self, markup: str) -> str:
        return markup if self.animated else ""

    def ring(self, x, y, w, h, r, color: str, *spans: tuple[float, float], width: float = 4) -> str:
        """An outline that lights up during the spans (nothing in the static card)."""
        if not self.animated:
            return ""
        shape = rect(x, y, w, h, r, "none", f'stroke="{color}" stroke-width="{width:g}"')
        return self.show(shape, *spans, fade=.25)

    def ring_path(self, d: str, color: str, *spans: tuple[float, float], width: float = 7) -> str:
        if not self.animated:
            return ""
        shape = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width:g}" stroke-linejoin="round"/>'
        return self.show(shape, *spans, fade=.25)

    def dot(self, path: str, t0: float, t1: float, color: str, r: int = 6) -> str:
        """A glowing dot that travels along `path` between t0 and t1."""
        if not self.animated:
            return ""
        e = .12
        f0, f1 = self._f(t0), self._f(t1)
        motion = (f'<animateMotion dur="{self.cycle:g}s" repeatCount="indefinite" calcMode="linear" path="{path}" '
                  f'keyPoints="0;0;1;1" keyTimes="0;{f0:.4f};{f1:.4f};1"/>')
        fade = self.animate("opacity", [(0, 0), (t0, 0), (t0 + e, 1), (t1 - e, 1), (t1, 0), (self.cycle, 0)])
        return (f'<g opacity="0"><circle r="{r + 5}" fill="{color}" opacity=".35"/><circle r="{r}" fill="#fff"/>'
                f'<circle r="{r - 2.5}" fill="{color}"/>{motion}{fade}</g>')

    def grow(self, x, y, w, h, grad: str, t0: float, t1: float, hold: float) -> str:
        """A bar that grows from 0 to w between t0 and t1, holds until `hold`, then resets."""
        if not self.animated:
            return bar(x, y, w, h, grad)
        pts = [(0, 0), (t0, 0), (t1, w), (hold, w), (min(hold + .4, self.cycle), 0)]
        return (f'<rect x="{x:g}" y="{y:g}" width="0" height="{h:g}" rx="{min(h / 2, w / 3):g}" fill="{g(grad)}">'
                f'{self.animate("width", pts)}</rect>')

    def dim(self, markup: str, *spans: tuple[float, float], lo: float = .35) -> str:
        """Dimmed (lo) except during the spans, where it is full strength."""
        return self.show(markup, *spans, lo=lo, hi=1.0, fade=.3)
