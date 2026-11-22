#!/usr/bin/env python3
"""Draw the blog's flowcharts and sequence diagrams as animated, colored, self-contained SVGs.

Every post diagram that used to be a plain mermaid block is one `Spec` in tools/diagram_specs.py:
its nodes, groups, edges and the scenarios that light them in turn. This module turns a spec into an SVG in
the family of tools/hero_gate.py (the confidence-gate flowchart) and tools/hero_kit.py: a gradient panel with
its own border so it reads on a light and a dark page, a gradient card per stage with an icon, flow dots
travelling along the connectors, a staged highlight that walks each scenario (a branch lights only on the
scenarios that take it), a still for prefers-reduced-motion, and the Space Grotesk font inlined.

The labels are at least 17 px on the 1200 px canvas (about 11.5 px at the post's width).

    python tools/diagram_flows.py                      # write every SVG into assets/img/posts
    python tools/diagram_flows.py --only kv-cache      # one spec, by slug fragment
    python tools/diagram_flows.py --list               # slug, post, section
    python tools/diagram_flows.py --frames DIR         # also paused screenshots on a dark and a light page
    python tools/diagram_flows.py --check              # render; fail if a label overflows, overlaps or leaves the canvas
    python tools/diagram_flows.py --sheet DIR          # a contact sheet page (every diagram beside its post), SVG copies next to it
"""
import argparse
import html
import itertools
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402
import hero_kit as kit  # noqa: E402
from font_metrics import text_width  # noqa: E402

ROOT = hero.ROOT
IMG_DIR = ROOT / "assets" / "img" / "posts"

W = 1200
TSIZE, SSIZE, ESIZE, CSIZE = 22, 18, 17.5, 17   # node title, node detail, edge label, chip
DIM = 0.38                                      # opacity of a stage or branch the scenario has not reached
STEP, DOT, LEAD, TAIL = 1.15, 0.8, 0.4, 1.8     # seconds per step, a dot's travel, before the first step, hold at the end
GAP = 6                                         # connectors stop this far short of the node they point at
LABEL_COLORS = {"white": kit.INK, "green": "#15803d", "amber": "#b45309", "red": "#b91c1c", "sky": "#0369a1"}
DOT_COLORS = {"white": "#7dd3fc", "green": kit.GREEN_LIGHT, "amber": kit.AMBER_LIGHT, "red": kit.RED_LIGHT, "sky": "#7dd3fc"}
RING_COLORS = {"green": kit.GREEN_LIGHT, "amber": kit.AMBER_LIGHT, "red": kit.RED_LIGHT, "sky": "#7dd3fc"}
ACTIVE = "#fde68a"                              # the stage a dot has just reached

# panel gradient (three stops) and the three soft glows in its corners
PALETTES = {
    "navy": (("#0b1f4d", "#312e81", "#115e59"), ("#22d3ee", "#f59e0b", "#34d399")),
    "plum": (("#2e1065", "#581c87", "#831843"), ("#e879f9", "#38bdf8", "#fbbf24")),
    "ocean": (("#082f49", "#0c4a6e", "#134e4a"), ("#38bdf8", "#a78bfa", "#34d399")),
    "ember": (("#431407", "#7c2d12", "#581c87"), ("#fb923c", "#f472b6", "#fbbf24")),
    "forest": (("#052e16", "#14532d", "#134e4a"), ("#a3e635", "#22d3ee", "#fbbf24")),
    "indigo": (("#1e1b4b", "#312e81", "#4c1d95"), ("#818cf8", "#f472b6", "#2dd4bf")),
    "rose": (("#4c0519", "#831843", "#3b0764"), ("#fb7185", "#fbbf24", "#a78bfa")),
    "teal": (("#042f2e", "#115e59", "#1e3a8a"), ("#2dd4bf", "#fbbf24", "#818cf8")),
}


# --- the spec -------------------------------------------------------------------------

@dataclass
class Node:
    """One box of the diagram. kind: card, pill (a terminal), gate (a decision diamond), hex, db, note."""
    id: str
    lines: tuple[str, ...]
    grad: str = "indigo"
    icon: str | None = None
    kind: str = "card"
    nt: int = 1                    # how many leading lines are the title (bigger and bold)
    bold: tuple[int, ...] = ()     # detail lines (by index) that are bold as well
    chips: tuple[str, ...] = ()
    layout: str = "left"           # card: icon left of the text, or "top" (icon over the text)
    ring: str | None = None        # color that stays lit once a scenario reaches the node
    x: float = 0
    y: float = 0
    w: float = 0                   # 0 = fit to the text
    h: float = 0
    text: str = "#fff"
    tsize: float = TSIZE
    ssize: float = SSIZE
    life: bool = False             # a participant: a lifeline hangs below it

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def at(self, x: float | None = None, y: float | None = None, *, cx: float | None = None,
           cy: float | None = None) -> "Node":
        """Place by the top-left corner, or by the centre (cx and cy are resolved once the size is known)."""
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        self.mid_x, self.mid_y = cx, cy
        return fit(self)    # the size is known from here on, so later nodes can be placed against this one

    mid_x: float | None = field(default=None, repr=False)
    mid_y: float | None = field(default=None, repr=False)


@dataclass
class Group:
    """A subgraph: a soft panel behind some nodes, with a title."""
    id: str
    label: str
    x: float
    y: float
    w: float
    h: float
    icon: str | None = None
    note: str | None = None        # a second line under the title
    note_bold: bool = False
    color: str = "#ffffff"


@dataclass
class Edge:
    """A connector. `a` and `b` are "node.side" or "node.side:offset" (side l, r, t or b; offset slides along it),
    or an absolute (x, y). `via` are the corners in between. color: white (dots only) or a branch color that stays lit."""
    id: str
    a: str | tuple
    b: str | tuple
    via: tuple[tuple[float, float], ...] = ()
    color: str = "white"
    dash: bool = False
    label: tuple[str, ...] = ()
    lpos: tuple[float, float] | None = None   # label centre; default: middle of the longest segment
    plain: bool = False            # label as bare text above the line (sequence messages) instead of a pill
    head: bool = True
    route: str = ""                # vhv, hvh, hv or vh: orthogonal corners worked out from the two anchors
    mid: float | None = None       # where the middle leg of a vhv (y) or hvh (x) route runs


@dataclass
class Scenario:
    """One walk through the diagram. A step is (edge ids, node ids): the dots run, then the nodes light."""
    start: str                                 # node ids that are lit from the start
    steps: tuple[tuple[str, str], ...]


@dataclass
class Spec:
    slug: str                                  # file stem: assets/img/posts/<slug>.svg
    post: str                                  # the post's file name without the date and extension
    section: str                               # the heading the diagram sits under
    title: str
    desc: str
    alt: str
    caption: str
    h: int
    nodes: list[Node]
    edges: list[Edge]
    scenarios: list[Scenario]
    labels: tuple[str, ...]                    # the wording of the mermaid block: every one must be drawn
    groups: list[Group] = field(default_factory=list)
    palette: str = "navy"
    lifeline_to: float = 0                     # sequence diagrams: where the lifelines end
    notes: str = ""                            # what was changed from the original wording, for the report

    @property
    def img_path(self) -> str:
        return f"/assets/img/posts/{self.slug}.svg"

    @property
    def svg_out(self) -> Path:
        return IMG_DIR / f"{self.slug}.svg"

    def node(self, nid: str) -> Node:
        return next(n for n in self.nodes if n.id == nid)

    def post_file(self) -> Path:
        return next((ROOT / "_posts").glob(f"*{self.post}.md"))


# --- text ------------------------------------------------------------------------------

SUB = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"}
SUB_RE = re.compile("[" + "".join(SUB) + "]+")


def width_of(s: str, size: float, weight: int = 700) -> float:
    plain = SUB_RE.sub(lambda m: "", s)
    sub = sum(len(m.group(0)) for m in SUB_RE.finditer(s))
    return text_width(plain, size, weight) + sub * size * 0.7 * 0.6


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def tspans(s: str) -> str:
    """Escape a line, turning subscript digits (user₁) into a small, lowered tspan the font does not need to carry."""
    out, pos = "", 0
    for m in SUB_RE.finditer(s):
        out += esc(s[pos:m.start()]) + f'<tspan baseline-shift="sub" font-size="82%">{"".join(SUB[c] for c in m.group(0))}</tspan>'
        pos = m.end()
    return out + esc(s[pos:])


def T(x: float, y: float, s: str, size: float, fill: str, weight: int = 700, anchor: str = "start",
      maxw: float | None = None, op: float | None = None, halo: str | None = None) -> str:
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    m = f' data-maxw="{maxw:g}"' if maxw else ""
    o = f' opacity="{op}"' if op is not None else ""
    h = f' stroke="{halo}" stroke-width="6" stroke-linejoin="round" paint-order="stroke"' if halo else ""
    return (f'<text x="{x:g}" y="{y:g}"{a} {kit.FONT} font-weight="{weight}" font-size="{size:g}" fill="{fill}"{m}{o}{h}>'
            f'{tspans(s)}</text>')


def lh_of(size: float) -> float:
    return round(size * 1.24)


def lh_line(n: "Node", i: int) -> float:
    """Height of a node's i-th line; a line with a subscript gets a little more room."""
    return lh_of(n.tsize if i < n.nt else n.ssize) + (4 if SUB_RE.search(n.lines[i]) else 0)


# --- node geometry -----------------------------------------------------------------------

ICON_BLOCK = 78       # left layout: where the text starts, from the node's left edge
PAD = 22


def chip_rows(chips: tuple[str, ...], avail: float) -> list[list[tuple[str, float]]]:
    rows: list[list[tuple[str, float]]] = [[]]
    used = 0.0
    for c in chips:
        w = width_of(c, CSIZE) + 26
        if rows[-1] and used + 8 + w > avail:
            rows.append([])
            used = 0.0
        used += (8 if rows[-1] else 0) + w
        rows[-1].append((c, w))
    return rows


def line_weight(n: Node, i: int) -> int:
    return 700 if i < n.nt or i in n.bold else 400


def text_block(n: Node) -> tuple[float, float]:
    """(widest line, total height) of a node's lines and chips, with chips wrapped to the widest line."""
    widths = [width_of(s, n.tsize if i < n.nt else n.ssize, line_weight(n, i)) for i, s in enumerate(n.lines)]
    h = sum(lh_line(n, i) for i in range(len(n.lines)))
    widest = max(widths, default=0)
    if n.chips:
        rows = chip_rows(n.chips, max(widest, n.w - ICON_BLOCK - PAD if n.w else 0, 220))
        widest = max(widest, max(sum(w for _, w in r) + 8 * (len(r) - 1) for r in rows))
        h += 8 + len(rows) * 38
    return widest, h


def fit(n: Node) -> Node:
    """Fill in the node's width and height from its text unless the spec fixed them."""
    widest, th = text_block(n)
    if n.kind == "gate":
        ry = max(80, th / 2 + 58) if not n.h else n.h / 2
        rx = n.w / 2
        if not rx:  # each line must fit the diamond's width at its own height
            y = -th / 2 + 14
            for i, s in enumerate(n.lines):
                size = n.tsize if i < n.nt else n.ssize
                far = max(abs(y), abs(y + lh_of(size))) + 6
                lw = width_of(s, size, line_weight(n, i))
                rx = max(rx, (lw / 2 + 8) / max(0.2, 1 - far / ry))
                y += lh_of(size)
        n.w, n.h = round(rx * 2), round(ry * 2)
    elif n.kind == "db":
        n.w = n.w or round(widest + 44)
        n.h = n.h or round(th + 62)
    elif n.kind == "note":
        n.w = n.w or round(widest + 40)
        n.h = n.h or round(th + 28)
    elif n.layout == "top":
        n.w = n.w or max(150, round(widest + 32))
        n.h = n.h or round(68 + th + 22)
    else:
        inset = 22 if n.kind in ("pill", "hex") else 0
        no_icon = n.icon is None
        n.w = n.w or round((widest + 2 * PAD + 2 * inset) if no_icon else (ICON_BLOCK + widest + PAD + inset))
        n.h = n.h or max(92, round(th + 2 * 20))
    if n.mid_x is not None:
        n.x = n.mid_x - n.w / 2
    if n.mid_y is not None:
        n.y = n.mid_y - n.h / 2
    return n


def avail_width(n: Node) -> float:
    if n.kind == "gate":
        return n.w * 0.62
    if n.kind in ("db", "note") or n.layout == "top" or n.icon is None:
        return n.w - 2 * (PAD - 8)
    return n.w - ICON_BLOCK - 14 - (22 if n.kind in ("pill", "hex") else 0)


def node_shape(n: Node) -> str:
    """The outline as a path or a rect element, filled with the node's gradient."""
    fill = kit.g(n.grad)
    if n.kind == "gate":
        return f'<path d="{outline_d(n)}" fill="{fill}" stroke="#fff" stroke-width="3" stroke-linejoin="round"/>'
    if n.kind == "hex":
        return f'<path d="{outline_d(n)}" fill="{fill}" stroke="#fff" stroke-opacity=".7" stroke-width="2.5" stroke-linejoin="round"/>'
    if n.kind == "db":
        return (f'<path d="{outline_d(n)}" fill="{fill}"/>'
                f'<ellipse cx="{n.cx:g}" cy="{n.y + 16:g}" rx="{n.w / 2:g}" ry="16" fill="#fff" fill-opacity=".22"/>')
    if n.kind == "note":
        return kit.rect(n.x, n.y, n.w, n.h, 14, fill)
    r = n.h / 2 if n.kind == "pill" else 22
    return kit.rect(n.x, n.y, n.w, n.h, r, fill)


def outline_d(n: Node, out: float = 0) -> str:
    x, y, w, h = n.x - out, n.y - out, n.w + 2 * out, n.h + 2 * out
    if n.kind == "gate":
        return f"M{x + w / 2:g} {y:g} L{x + w:g} {y + h / 2:g} L{x + w / 2:g} {y + h:g} L{x:g} {y + h / 2:g} Z"
    if n.kind == "hex":
        k = 30 + out
        return (f"M{x + k:g} {y:g} L{x + w - k:g} {y:g} L{x + w:g} {y + h / 2:g} L{x + w - k:g} {y + h:g} "
                f"L{x + k:g} {y + h:g} L{x:g} {y + h / 2:g} Z")
    if n.kind == "db":
        ry = 16
        return (f"M{x:g} {y + ry:g} A{w / 2:g} {ry} 0 0 1 {x + w:g} {y + ry:g} V{y + h - ry:g} "
                f"A{w / 2:g} {ry} 0 0 1 {x:g} {y + h - ry:g} Z")
    r = (h / 2 if n.kind == "pill" else 14 if n.kind == "note" else 22) + (out if out else 0)
    return (f"M{x + r:g} {y:g} H{x + w - r:g} A{r:g} {r:g} 0 0 1 {x + w:g} {y + r:g} V{y + h - r:g} "
            f"A{r:g} {r:g} 0 0 1 {x + w - r:g} {y + h:g} H{x + r:g} A{r:g} {r:g} 0 0 1 {x:g} {y + h - r:g} "
            f"V{y + r:g} A{r:g} {r:g} 0 0 1 {x + r:g} {y:g} Z")


def node_markup(n: Node) -> str:
    """The shape, icon and text of one node."""
    out = f'<g filter="url(#shadow)">{node_shape(n)}</g>'
    maxw = avail_width(n)
    sizes = [n.tsize if i < n.nt else n.ssize for i in range(len(n.lines))]
    weights = [line_weight(n, i) for i in range(len(n.lines))]
    ops = [None if i < n.nt else .95 for i in range(len(n.lines))]
    th = sum(lh_line(n, i) for i in range(len(n.lines))) + (8 + len(chip_rows(n.chips, maxw)) * 38 if n.chips else 0)

    def lines_at(x: float, top: float, anchor: str) -> str:
        s, y = "", top
        for i, line in enumerate(n.lines):
            lh = lh_line(n, i)
            s += T(x, y + (lh + sizes[i] * .7) / 2, line, sizes[i], n.text, weights[i], anchor, maxw, ops[i])
            y += lh
        if n.chips:
            y += 8
            for row in chip_rows(n.chips, maxw):
                total = sum(w for _, w in row) + 8 * (len(row) - 1)
                cx = x if anchor == "middle" else x + total / 2
                cur = cx - total / 2
                for c, cw in row:
                    s += (kit.rect(cur, y, cw, 30, 15, "#fff", 'fill-opacity=".24"')
                          + T(cur + cw / 2, y + 21.5, c, CSIZE, n.text, 700, "middle", cw - 8))
                    cur += cw + 8
                y += 38
        return s

    if n.kind == "gate":
        top = n.cy - th / 2 + 14
        if n.icon:
            out += f'<circle cx="{n.cx:g}" cy="{top - 20:g}" r="19" fill="#fff" fill-opacity=".22"/>'
            out += kit.icon(n.icon, n.cx - 12, top - 32, 24, n.text, 2.2)
        out += lines_at(n.cx, top, "middle")
    elif n.kind in ("db", "note"):
        top = n.y + (n.h - th) / 2 + (14 if n.kind == "db" else 0)
        out += lines_at(n.cx, top, "middle")
    elif n.layout == "top":
        cx = n.cx
        out += f'<circle cx="{cx:g}" cy="{n.y + 36:g}" r="23" fill="#fff" fill-opacity=".22"/>'
        out += kit.icon(n.icon, cx - 15, n.y + 21, 30, n.text, 2.2) if n.icon else ""
        out += lines_at(cx, n.y + 68, "middle")
    elif n.icon is None:
        out += lines_at(n.cx, n.cy - th / 2, "middle")
    else:
        inset = 22 if n.kind in ("pill", "hex") else 0
        out += f'<circle cx="{n.x + inset + 40:g}" cy="{n.cy:g}" r="25" fill="#fff" fill-opacity=".22"/>'
        out += kit.icon(n.icon, n.x + inset + 40 - 16, n.cy - 16, 32, n.text, 2.2)
        out += lines_at(n.x + inset + ICON_BLOCK, n.cy - th / 2, "start")
    return out


# --- connectors ---------------------------------------------------------------------------

def anchor(spec: Spec, ref: str | tuple) -> tuple[float, float]:
    if isinstance(ref, tuple):
        return ref
    name, _, rest = ref.partition(".")
    side, _, off = rest.partition(":")
    o = float(off) if off else 0.0
    n = next((x for x in spec.nodes if x.id == name), None)
    if n is None:
        g = next(g for g in spec.groups if g.id == name)
        x, y, w, h = g.x, g.y, g.w, g.h
    else:
        x, y, w, h = n.x, n.y, n.w, n.h
    if side in ("td", "bd"):  # a point on the slanted edge of a diamond, `o` px right of its centre
        k = 1 - abs(o) / (w / 2)
        return (x + w / 2 + o, y + h / 2 + (h / 2 * k) * (-1 if side == "td" else 1))
    if side in ("ld", "rd"):  # the same on the left or right slant, `o` px below its centre
        k = 1 - abs(o) / (h / 2)
        return (x + w / 2 + (w / 2 * k) * (-1 if side == "ld" else 1), y + h / 2 + o)
    return {"l": (x, y + h / 2 + o), "r": (x + w, y + h / 2 + o), "t": (x + w / 2 + o, y), "b": (x + w / 2 + o, y + h)}[side]


def route_via(e: Edge, a: tuple[float, float], b: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    """The corners of an orthogonal route: vhv (down, across, down), hvh, hv (across, then down) or vh."""
    (ax, ay), (bx, by) = a, b
    if e.route == "vhv":
        my = e.mid if e.mid is not None else (ay + by) / 2
        return ((ax, my), (bx, my))
    if e.route == "hvh":
        mx = e.mid if e.mid is not None else (ax + bx) / 2
        return ((mx, ay), (mx, by))
    if e.route == "hv":
        return ((bx, ay),)
    if e.route == "vh":
        return ((ax, by),)
    return ()


def edge_points(spec: Spec, e: Edge) -> list[tuple[float, float]]:
    a, b = anchor(spec, e.a), anchor(spec, e.b)
    pts = [a, *(e.via or route_via(e, a, b)), b]
    if e.head:  # stop short of the node the arrow points at
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        d = math.hypot(x1 - x0, y1 - y0) or 1
        pts[-1] = (x1 - (x1 - x0) / d * GAP, y1 - (y1 - y0) / d * GAP)
    return pts


def rounded(pts: list[tuple[float, float]], r: float = 16) -> str:
    d = f"M{pts[0][0]:g} {pts[0][1]:g}"
    for i in range(1, len(pts) - 1):
        (px, py), (cx, cy), (nx, ny) = pts[i - 1], pts[i], pts[i + 1]
        d1, d2 = math.hypot(cx - px, cy - py), math.hypot(nx - cx, ny - cy)
        rr = min(r, d1 / 2, d2 / 2)
        sx, sy = cx + (px - cx) / d1 * rr, cy + (py - cy) / d1 * rr
        ex, ey = cx + (nx - cx) / d2 * rr, cy + (ny - cy) / d2 * rr
        d += f" L{sx:.1f} {sy:.1f} Q{cx:g} {cy:g} {ex:.1f} {ey:.1f}"
    return d + f" L{pts[-1][0]:.1f} {pts[-1][1]:.1f}"


def label_center(pts: list[tuple[float, float]]) -> tuple[float, float]:
    (x0, y0), (x1, y1) = max(itertools.pairwise(pts), key=lambda s: math.hypot(s[1][0] - s[0][0], s[1][1] - s[0][1]))
    return (x0 + x1) / 2, (y0 + y1) / 2


def label_markup(e: Edge, pts: list[tuple[float, float]], panel_dark: str) -> str:
    if not e.label:
        return ""
    cx, cy = e.lpos or label_center(pts)
    lh = lh_of(ESIZE)
    if e.plain:  # a message of a sequence diagram: a dark chip just above its arrow
        wd = max(width_of(s, ESIZE + .5) for s in e.label) + 26
        h = len(e.label) * lh + 10
        top = cy - 9 - h
        out = kit.rect(cx - wd / 2, top, wd, h, 12, panel_dark, 'fill-opacity=".72" stroke="#fff" stroke-opacity=".28" stroke-width="1.5"')
        for i, s in enumerate(e.label):
            out += T(cx, top + 5 + i * lh + (lh + (ESIZE + .5) * .7) / 2, s, ESIZE + .5, "#fff", 700, "middle", wd - 12)
        return out
    wd = max(width_of(s, ESIZE) for s in e.label) + 26
    h = len(e.label) * lh + 12
    color = LABEL_COLORS[e.color]
    out = kit.rect(cx - wd / 2, cy - h / 2, wd, h, min(15, h / 2), "#fff", 'fill-opacity=".96"')
    for i, s in enumerate(e.label):
        out += T(cx, cy - h / 2 + 6 + i * lh + (lh + ESIZE * .7) / 2, s, ESIZE, color, 700, "middle", wd - 12)
    return out


# --- timeline -------------------------------------------------------------------------------

@dataclass
class Plan:
    cycle: float
    scn: list[tuple[float, float]]                       # (start, end) per scenario
    reach: dict[str, list[tuple[float, float, float]]]   # node -> (arrive, scenario end, scenario start)
    dots: dict[str, list[float]]                         # edge -> dot start times
    lit: dict[str, list[tuple[float, float]]]            # edge -> (dot start, scenario end)


def plan(spec: Spec) -> Plan:
    t, scn = 0.0, []
    reach: dict[str, list[tuple[float, float, float]]] = {}
    dots: dict[str, list[float]] = {}
    lit: dict[str, list[tuple[float, float]]] = {}
    for sc in spec.scenarios:
        start = t
        end = start + LEAD + len(sc.steps) * STEP + TAIL
        for nid in sc.start.split():
            reach.setdefault(nid, []).append((start + LEAD, end, start))
        for i, (eids, nids) in enumerate(sc.steps):
            s0 = start + LEAD + i * STEP
            for eid in eids.split():
                dots.setdefault(eid, []).append(s0)
                lit.setdefault(eid, []).append((s0, end))
            for nid in nids.split():
                reach.setdefault(nid, []).append((s0 + DOT, end, start))
        scn.append((start, end))
        t = end
    return Plan(t, scn, reach, dots, lit)


def branch_nodes(spec: Spec, pl: Plan) -> set[str]:
    """Nodes that some scenario reaches and another does not: they dim until their scenario gets there."""
    n = len(spec.scenarios)
    return {nid for nid, r in pl.reach.items() if len({s for _, _, s in r}) < n}


# --- the drawing ------------------------------------------------------------------------------

def build(spec: Spec, ctx: kit.Ctx, pl: Plan) -> str:
    animated = ctx.animated
    dark = PALETTES[spec.palette][0][0]
    out: list[str] = []
    nodes = {n.id: n for n in spec.nodes}
    branch = branch_nodes(spec, pl)

    for g in spec.groups:
        out.append(kit.rect(g.x, g.y, g.w, g.h, 26, g.color, 'fill-opacity=".08" stroke="#fff" stroke-opacity=".38" stroke-width="2"'))
        tx = g.x + 22
        if g.icon:
            out.append(kit.icon(g.icon, g.x + 18, g.y + 14, 30, "#fff", 2.2))
            tx = g.x + 58
        out.append(T(tx, g.y + 36, g.label, 21, "#fff", 700, "start", g.w - (tx - g.x) - 16))
        if g.note:
            out.append(T(tx, g.y + 62, g.note, SSIZE, "#fff", 700 if g.note_bold else 400, "start",
                         maxw=g.w - (tx - g.x) - 16, op=.92))

    for nid in (n.id for n in spec.nodes if n.life):
        n = nodes[nid]
        out.append(f'<line x1="{n.cx:g}" y1="{n.bottom + 4:g}" x2="{n.cx:g}" y2="{spec.lifeline_to:g}" stroke="#fff" '
                   f'stroke-opacity=".4" stroke-width="3" stroke-dasharray="3 9" stroke-linecap="round"/>')

    paths, labels, overlays, dotmarks = {}, [], [], []
    for e in spec.edges:
        pts = edge_points(spec, e)
        d = rounded(pts)
        paths[e.id] = d
        dash = "12 8" if e.dash else None
        if e.color == "white":
            march = ('<animate attributeName="stroke-dashoffset" from="0" to="-11" dur="1s" repeatCount="indefinite"/>'
                     if animated else "")
            da = "12 8" if e.dash else "2 9"
            mk = ' marker-end="url(#ar-white)"' if e.head else ""
            out.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3.5" stroke-linecap="round" '
                       f'stroke-dasharray="{da}"{mk}>{march}</path>')
        else:
            base = kit.arrow(d, e.color, 5, dash, op=1, head=e.head)
            out.append(f'<g opacity="{DIM}">{base}</g>' if animated else base)
            if animated and e.id in pl.lit:
                overlays.append(ctx.show(kit.arrow(d, e.color, 5, dash, op=1, head=e.head), *pl.lit[e.id], fade=.25))
        labels.append(label_markup(e, pts, dark))
        if animated and e.id in pl.dots:
            dc = DOT_COLORS[e.color]
            for s0 in pl.dots[e.id]:
                dotmarks.append(ctx.dot(d, s0, s0 + DOT, dc, 6))
    out.extend(overlays)
    out.extend(labels)

    for n in spec.nodes:
        mk = node_markup(n)
        r = pl.reach.get(n.id, [])
        if animated and n.id in branch:
            mk = ctx.dim(mk, *[(a, b) for a, b, _ in r], lo=DIM)
        out.append(mk)
        if animated and r:
            out.append(ring(ctx, n, ACTIVE, [(a, a + STEP + .5) for a, _, _ in r]))
            if n.ring:
                out.append(ring(ctx, n, RING_COLORS[n.ring], [(a, b) for a, b, _ in r]))
    for g in spec.groups:
        if animated and g.id in pl.reach:
            out.append(ctx.ring(g.x - 4, g.y - 4, g.w + 8, g.h + 8, 28, ACTIVE, *[(a, a + STEP + .5) for a, _, _ in pl.reach[g.id]]))
    out.extend(dotmarks)
    return "\n".join(o for o in out if o)


def ring(ctx: kit.Ctx, n: Node, color: str, spans: list[tuple[float, float]]) -> str:
    if n.kind in ("card", "pill", "note"):
        r = (n.h / 2 if n.kind == "pill" else 14 if n.kind == "note" else 22) + 3
        return ctx.ring(n.x - 4, n.y - 4, n.w + 8, n.h + 8, r, color, *spans)
    return ctx.ring_path(outline_d(n, 4), color, *spans, width=5)


# --- the document -----------------------------------------------------------------------------

def flow_svg(spec: Spec) -> str:
    """The animated SVG for the post body, with a still version for reduced motion."""
    for n in spec.nodes:
        fit(n)
    pl = plan(spec)
    (a, b, c), (g1, g2, g3) = PALETTES[spec.palette]
    motion, still = build(spec, kit.Ctx(pl.cycle), pl), build(spec, kit.Ctx(), pl)
    h = spec.h
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" aria-labelledby="t d">
<title id="t">{html.escape(spec.title)}</title>
<desc id="d">{html.escape(spec.desc)}</desc>
<style>{kit.font_faces()}
.still {{ display: none; }}
@media (prefers-reduced-motion: reduce) {{ .motion {{ display: none; }} .still {{ display: inline; }} }}
</style>
{kit.defs()}
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>
<radialGradient id="b1" cx=".06" cy="1" r=".55"><stop offset="0" stop-color="{g1}" stop-opacity=".45"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>
<radialGradient id="b2" cx=".96" cy=".02" r=".5"><stop offset="0" stop-color="{g2}" stop-opacity=".36"/><stop offset="1" stop-color="{g2}" stop-opacity="0"/></radialGradient>
<radialGradient id="b3" cx=".55" cy=".9" r=".45"><stop offset="0" stop-color="{g3}" stop-opacity=".24"/><stop offset="1" stop-color="{g3}" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.5" fill="#fff" fill-opacity=".16"/></pattern>
<rect width="{W}" height="{h}" rx="28" fill="url(#bg)"/>
<rect width="{W}" height="{h}" rx="28" fill="url(#b1)"/>
<rect width="{W}" height="{h}" rx="28" fill="url(#b2)"/>
<rect width="{W}" height="{h}" rx="28" fill="url(#b3)"/>
<rect width="{W}" height="{h}" rx="28" fill="url(#dots)" opacity=".7"/>
<rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="27" fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="2"/>
<g class="motion">{motion}</g>
<g class="still">{still}</g>
</svg>
"""


# --- layout problems found without a browser -----------------------------------------------------

def layout_problems(spec: Spec) -> list[str]:
    """Boxes that overlap or leave the canvas, edges that point at nothing, scenarios that name unknown ids."""
    bad: list[str] = []
    nodes = [fit(n) for n in spec.nodes]
    ids = {n.id for n in nodes} | {g.id for g in spec.groups}
    for n in nodes:
        if n.x < 8 or n.y < 8 or n.right > W - 8 or n.bottom > spec.h - 8:
            bad.append(f"{n.id} leaves the canvas")
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if a.x < b.right + 10 and b.x < a.right + 10 and a.y < b.bottom + 10 and b.y < a.bottom + 10:
                bad.append(f"{a.id} touches {b.id}")
    edge_ids = {e.id for e in spec.edges}
    for e in spec.edges:
        for ref in (e.a, e.b):
            if isinstance(ref, str) and ref.partition(".")[0] not in ids:
                bad.append(f"edge {e.id}: unknown node in {ref!r}")
    for sc in spec.scenarios:
        for nid in sc.start.split():
            if nid not in ids:
                bad.append(f"scenario start: unknown node {nid}")
        for eids, nids in sc.steps:
            bad += [f"scenario: unknown edge {x}" for x in eids.split() if x not in edge_ids]
            bad += [f"scenario: unknown node {x}" for x in nids.split() if x not in ids]
    return bad


# --- the posts ----------------------------------------------------------------------------------------

def _squash(s: str) -> str:
    """Text with markup, whitespace and subscript digits normalised, to compare a label with a block or a drawing."""
    s = re.sub(r"<br\s*/?>|</?b>", "", s)
    s = SUB_RE.sub(lambda m: "".join(SUB[c] for c in m.group(0)), s)
    return re.sub(r"[\s\U0001F300-\U0001FAFF]+", "", s)


def replace_block(text: str, spec: Spec) -> str:
    """The post's text with the plain mermaid block under the spec's section swapped for its image and caption."""
    image = f"![{spec.alt}]({spec.img_path})"
    if image in text:
        return text
    lines = text.split("\n")
    head = next(i for i, ln in enumerate(lines) if ln.startswith("#") and spec.section in ln)
    start = next(i for i in range(head, len(lines)) if lines[i].startswith("```mermaid"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "```")
    block = "\n".join(lines[start:end + 1])
    missing = [lb for lb in spec.labels if _squash(lb) not in _squash(block)]
    if missing:
        raise ValueError(f"{spec.slug}: the block under {spec.section!r} does not contain {missing}")
    lines[start:end + 1] = [image, spec.caption]
    text = "\n".join(lines)
    if "```mermaid" not in text:  # the front matter flag only loads the mermaid script
        text = re.sub(r"\A(---\n.*?)^mermaid: true\n(.*?^---\n)", r"\1\2", text, count=1, flags=re.M | re.S)
    return text


def apply_to_posts(specs: list[Spec]) -> list[Path]:
    """Rewrite every post that still has the mermaid block of one of the specs; returns the posts changed."""
    changed = []
    for spec in specs:
        post = spec.post_file()
        before = post.read_text()
        after = replace_block(before, spec)
        if after != before:
            post.write_text(after)
            changed.append(post)
    return changed


# --- frames, checks, sheet -------------------------------------------------------------------------

BACKGROUNDS = {"dark": "#1b1b1e", "light": "#ffffff"}

_CHECK_JS = """
() => {
  const bad = [];
  const box = document.documentElement.getBoundingClientRect();
  const rects = [];
  document.querySelectorAll('svg text').forEach(t => {
    const r = t.getBoundingClientRect();
    if (!r.width || getComputedStyle(t.closest('g[class]') || t).display === 'none') return;
    const label = (t.textContent || '').slice(0, 40);
    const maxw = parseFloat(t.dataset.maxw || '0');
    if (maxw && r.width > maxw + 1.5) bad.push(`"${label}" is ${r.width.toFixed(0)}px wide, limit ${maxw}`);
    if (r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1 || r.bottom > box.bottom + 1)
      bad.push(`"${label}" sticks out of the drawing`);
    rects.push([label, r]);
  });
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const [la, a] = rects[i], [lb, b] = rects[j];
    const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left), oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (ox > 3 && oy > 6) bad.push(`"${la}" overlaps "${lb}"`);
  }
  return bad;
}
"""


def frame_times(spec: Spec) -> tuple[float, ...]:
    """Three moments: early in the first scenario, late in it, and late in the last one."""
    pl = plan(spec)
    (s0, e0), e1 = pl.scn[0], pl.scn[-1][1]
    if len(pl.scn) == 1:
        return (round(s0 + (e0 - s0) * .3, 1), round(s0 + (e0 - s0) * .6, 1), round(e0 - 1.0, 1))
    return (round(s0 + (e0 - s0) * .3, 1), round(e0 - 1.0, 1), round(e1 - 1.0, 1))


def render_frames(spec: Spec, out_dir: Path, svg: Path | None = None) -> list[Path]:
    """Screenshot the animation paused at three times, on a dark and a light page background."""
    from playwright.sync_api import sync_playwright
    svg = svg or spec.svg_out
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": spec.h})
        page.goto(svg.resolve().as_uri())
        page.evaluate("document.fonts.ready")
        for theme, color in BACKGROUNDS.items():
            page.evaluate(f"document.documentElement.style.background = '{color}'")
            for t in frame_times(spec):
                page.evaluate(f"(() => {{ const s = document.documentElement; s.pauseAnimations(); s.setCurrentTime({t}); }})()")
                shot = out_dir / f"{spec.slug}-{theme}-{t:05.1f}s.png"
                page.screenshot(path=str(shot))
                shots.append(shot)
        browser.close()
    return shots


def find_problems(spec: Spec, svg: Path | None = None) -> list[str]:
    """Labels wider than their box, text that overlaps other text or leaves the canvas, in the animation and the still."""
    from playwright.sync_api import sync_playwright
    svg = svg or spec.svg_out
    bad: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for mode in ("no-preference", "reduce"):
            page = browser.new_page(viewport={"width": W, "height": spec.h}, reduced_motion=mode)
            page.goto(svg.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            found = page.evaluate(_CHECK_JS)
            bad += [(f"still: {b}" if mode == "reduce" else b) for b in found]
            page.close()
        browser.close()
    return bad


def post_title(spec: Spec) -> str:
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', spec.post_file().read_text(), re.M)
    return m.group(1) if m else spec.post


def contact_sheet(specs: list[Spec], out_dir: Path) -> Path:
    """One page: every diagram beside its post title and section, playing, with a dark/light toggle; SVGs copied next to it."""
    import shutil
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for s in sorted(specs, key=lambda s: s.post_file().name):  # post order (by date); a post's own diagrams keep their order
        shutil.copy(s.svg_out, out_dir / s.svg_out.name)
        cards.append(
            f'<article class="card"><div class="meta"><h2>{html.escape(post_title(s))}</h2>'
            f'<p>Section: <strong>{html.escape(s.section)}</strong></p></div>'
            f'<img src="{s.svg_out.name}" alt="{html.escape(s.alt)}" loading="lazy" width="{W}" height="{s.h}">'
            f'<p class="cap">{html.escape(s.caption.strip("_"))}</p></article>')
    page = f"""<!doctype html>
<html lang="en" data-theme="system"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blog diagrams contact sheet</title><style>
:root {{ --bg:#ffffff; --ink:#1e1b4b; --muted:#5b5780; --card:#f6f4fb; --line:#e4e0f2; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#1b1b1e; --ink:#f1efff; --muted:#a9a4cf; --card:#242428; --line:#38383f; }} }}
:root[data-theme="dark"] {{ --bg:#1b1b1e; --ink:#f1efff; --muted:#a9a4cf; --card:#242428; --line:#38383f; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:'Space Grotesk',system-ui,sans-serif; color:var(--ink); background:var(--bg); }}
header {{ max-width:1000px; margin:0 auto; padding:28px 20px 8px; display:flex; flex-wrap:wrap; gap:14px; align-items:end; justify-content:space-between; }}
h1 {{ margin:0; font-size:clamp(26px,4vw,40px); letter-spacing:-.02em; background:linear-gradient(90deg,#4f46e5,#db2777,#f59e0b);
  -webkit-background-clip:text; background-clip:text; color:transparent; }}
header p {{ margin:6px 0 0; color:var(--muted); }}
.seg {{ display:inline-flex; background:var(--card); border:1px solid var(--line); border-radius:999px; padding:3px; }}
.seg button {{ border:0; background:none; color:var(--muted); font:inherit; font-size:13px; padding:6px 12px; border-radius:999px; cursor:pointer; }}
.seg button[aria-pressed="true"] {{ background:linear-gradient(135deg,#4f46e5,#a855f7); color:#fff; }}
main {{ max-width:1000px; margin:0 auto; padding:12px 20px 64px; display:grid; gap:26px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:18px; animation:rise .5s both; }}
.meta h2 {{ margin:0 0 4px; font-size:19px; }} .meta p {{ margin:0 0 12px; color:var(--muted); font-size:14px; }}
img {{ width:100%; height:auto; display:block; border-radius:14px; }}
.cap {{ margin:10px 2px 0; color:var(--muted); font-size:14px; font-style:italic; }}
@keyframes rise {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:none; }} }}
@media (prefers-reduced-motion: reduce) {{ .card {{ animation:none; }} }}
</style></head><body>
<header><div><h1>Blog diagrams</h1><p>{len(specs)} animated diagrams, each replacing a plain mermaid block. A preview, not committed.</p></div>
<div class="seg" id="theme"><button data-v="system">System</button><button data-v="light">Light</button><button data-v="dark">Dark</button></div></header>
<main>{"".join(cards)}</main>
<script>
const root = document.documentElement, seg = document.getElementById('theme');
const set = v => {{ root.dataset.theme = v; try {{ localStorage.setItem('dg-theme', v); }} catch (e) {{}}
  seg.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === v)); }};
let saved = null; try {{ saved = localStorage.getItem('dg-theme'); }} catch (e) {{}}
set(saved || 'system');
seg.addEventListener('click', e => e.target.dataset.v && set(e.target.dataset.v));
</script></body></html>
"""
    sheet = out_dir / "index.html"
    sheet.write_text(page)
    return sheet


def main(argv: list[str] | None = None) -> int:
    from diagram_specs import SPECS
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", metavar="FRAGMENT", help="only the specs whose slug contains this")
    ap.add_argument("--list", action="store_true", help="print slug, post and section of every spec")
    ap.add_argument("--frames", type=Path, metavar="DIR", help="also screenshot each paused at 3 times on a dark and a light page")
    ap.add_argument("--check", action="store_true", help="render and report labels that overflow, overlap or leave the canvas; exit 1 if any")
    ap.add_argument("--sheet", type=Path, metavar="DIR", help="write index.html (every diagram beside its post) and SVG copies into DIR")
    ap.add_argument("--apply", action="store_true", help="swap each spec's mermaid block in its post for the image and caption")
    args = ap.parse_args(argv)
    specs = [s for s in SPECS if not args.only or args.only in s.slug]
    if args.apply:
        for post in apply_to_posts(specs):
            print(post)
    if args.list:
        for s in specs:
            print(f"{s.slug}\t{s.post}\t{s.section}")
        return 0
    failed = 0
    for s in specs:
        for problem in layout_problems(s):
            print(f"{s.slug}: {problem}")
            failed = 1
        s.svg_out.parent.mkdir(parents=True, exist_ok=True)
        s.svg_out.write_text(flow_svg(s))
        print(s.svg_out)
        if args.check:
            for problem in find_problems(s):
                print(f"{s.slug}: {problem}")
                failed = 1
        if args.frames:
            for shot in render_frames(s, args.frames):
                print(shot)
    if args.sheet:
        print(contact_sheet(specs, args.sheet))
    return failed


if __name__ == "__main__":
    sys.exit(main())
