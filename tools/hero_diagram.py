#!/usr/bin/env python3
"""Render the evidence-grounded questionnaires hero card and its animated flow.

One drawn diagram, two outputs:

  * a 1200x630 static PNG hero (the og:image / social card): vibrant gradient
    background, big headline, and the diagram with both outcomes lit;
  * a self-contained animated SVG for the post body: the same diagram, looping
    through two questions. Evidence documents flow into retrieval, the
    confidence gate scores the match, and the green "answer + cited source" path
    lights up for a supported question while the amber "insufficient evidence"
    path lights up for one the evidence cannot support.

The SVG uses SMIL only (no scripts, no external requests; the font is inlined),
so it works as a plain <img> in the post. With no arguments both files are
written to their committed locations:

    python tools/hero_diagram.py

    python tools/hero_diagram.py --html card.html   # card HTML, no browser needed
    python tools/hero_diagram.py --frames /tmp/f    # also paused screenshots of the SVG

The PNG needs Playwright (same as tools/hero.py); fonts are the self-hosted
Space Grotesk files, so the card matches the site. tools/hero.py is reused for
its geometry, font folder, site name and PNG renderer, and is left unchanged.
"""
import argparse
import base64
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402

ROOT = hero.ROOT
POSTS_IMG = ROOT / "assets" / "img" / "posts"
PNG_OUT = POSTS_IMG / "evidence-grounded-questionnaires-hero.png"
SVG_OUT = POSTS_IMG / "evidence-grounded-questionnaires-flow.svg"

HEADLINE = "Evidence-grounded questionnaires"
SUBTITLE = 'Answers cited from your own evidence, or an honest "insufficient evidence"'
SVG_TITLE = "How a questionnaire answer is grounded in evidence"
SVG_DESC = (
    "Evidence documents (a SOC 2 report, a policy, an audit report) feed a retrieval step. "
    "A confidence gate scores the best match. Strong evidence gives an answer with a cited "
    "source; weak evidence gives an honest insufficient-evidence result instead of a guess."
)

DIAGRAM_W, DIAGRAM_H = 1100, 330
CYCLE = 14  # seconds for the two questions

INK = "#1e1b4b"        # text on the white cards
MUTED = "#5b5780"
GREEN = "#16a34a"
GREEN_LIGHT = "#34d399"
AMBER = "#f59e0b"
AMBER_LIGHT = "#fbbf24"
DIM = 0.3              # opacity of a path that is not the active one

# Question shown in the animated version, then the caption under it.
SCENARIOS = (
    {"question": "Data encrypted at rest?", "level": 0.86,
     "caption": "Strong evidence found: the answer ships with its citation."},
    {"question": "Customer-managed keys?", "level": 0.2,
     "caption": "No supporting evidence: it says so instead of guessing."},
)

FONT = "font-family=\"'Space Grotesk', sans-serif\""


def font_faces() -> str:
    """@font-face rules with the site's Space Grotesk inlined as data URIs."""
    return "\n".join(
        f"@font-face {{ font-family: 'Space Grotesk'; font-weight: {w}; src: url('data:font/woff2;base64,"
        f"{base64.b64encode((hero.FONTS / f'space-grotesk-{w}.woff2').read_bytes()).decode()}') format('woff2'); }}"
        for w in (400, 700)
    )


# --- SMIL helpers ----------------------------------------------------------

def keyframes(points: list[tuple[float, str | float]]) -> tuple[str, str]:
    """(keyTimes, values) for (fraction-of-cycle, value) points; pads to 0 and 1."""
    pts = sorted(points, key=lambda p: p[0])
    if pts[0][0] > 0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < 1:
        pts.append((1.0, pts[-1][1]))
    return ";".join(f"{t:.4f}" for t, _ in pts), ";".join(str(v) for _, v in pts)


def animate(attr: str, points: list[tuple[float, str | float]]) -> str:
    times, values = keyframes(points)
    return (f'<animate attributeName="{attr}" dur="{CYCLE}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{times}" values="{values}"/>')


def window(lo: float, hi: float, start: float, rise: float, fall: float, end: float
           ) -> list[tuple[float, float]]:
    """Opacity points: lo, up to hi between rise and fall, back to lo by end."""
    return [(start, lo), (rise, hi), (fall, hi), (end, lo)]


def merge(*tracks: list[tuple[float, float]], lo: float) -> list[tuple[float, float]]:
    """Join several windows that each start and end at lo into one track."""
    out: list[tuple[float, float]] = []
    for t in tracks:
        out.extend(t)
    out.sort(key=lambda p: p[0])
    return [(0.0, lo)] + out + [(1.0, lo)]


def dot(path: str, start: float, end: float, color: str, r: int = 6) -> str:
    """A glowing dot that travels along `path` between two points of the cycle."""
    e = 0.012
    motion = (f'<animateMotion dur="{CYCLE}s" repeatCount="indefinite" calcMode="linear" '
              f'path="{path}" keyPoints="0;0;1;1" keyTimes="0;{start:.4f};{end:.4f};1"/>')
    fade = animate("opacity", [(0, 0), (start, 0), (start + e, 1), (end - e, 1), (end, 0), (1, 0)])
    return (f'<g opacity="0"><circle r="{r + 5}" fill="{color}" opacity=".35"/>'
            f'<circle r="{r}" fill="#fff"/><circle r="{r - 2.5}" fill="{color}"/>{motion}{fade}</g>')


# --- icons (24x24 line icons, drawn with a stroke) -------------------------

def icon(name: str, x: float, y: float, size: float, stroke: str = "#fff", sw: float = 2) -> str:
    paths = {
        "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
        "doc": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M9.5 12.5h6M9.5 16h6M9.5 9h2"/>',
        "audit": '<rect x="5" y="4.5" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5"/>'
                 '<path d="M8.7 18v-3M12 18v-6M15.3 18v-4"/>',
        "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5.5 5.5"/>',
        "gauge": '<path d="M4.5 16a7.5 7.5 0 0 1 15 0"/><path d="M12 16l3.5-4.5"/><circle cx="12" cy="16" r="1"/>',
        "link": '<path d="M10 14a4 4 0 0 0 5.7 0l2.5-2.5a4 4 0 0 0-5.7-5.7L11 7.3"/>'
                '<path d="M14 10a4 4 0 0 0-5.7 0l-2.5 2.5a4 4 0 0 0 5.7 5.7L13 16.7"/>',
        "warn": '<path d="M12 4l9 16H3z"/><path d="M12 10v4.5"/><circle cx="12" cy="17.2" r=".6"/>',
        "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
        "ask": '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.6 2.2c-.8.5-1.2 1-1.2 1.9"/>'
               '<circle cx="12" cy="17" r=".6"/>',
    }
    return (f'<g transform="translate({x},{y}) scale({size / 24:.4f})" fill="none" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</g>')


# --- the diagram -----------------------------------------------------------

def defs() -> str:
    marker = lambda mid, c: (  # noqa: E731
        f'<marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto"><path d="M1 1l8 4-8 4z" fill="{c}"/></marker>')
    return f"""<defs>
<linearGradient id="gSoc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient>
<linearGradient id="gPol" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0891b2"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>
<linearGradient id="gAud" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#db2777"/><stop offset="1" stop-color="#fb7185"/></linearGradient>
<linearGradient id="gRet" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>
<linearGradient id="gGate" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a855f7"/><stop offset="1" stop-color="#ec4899"/></linearGradient>
<linearGradient id="gGreen" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#15803d"/><stop offset="1" stop-color="#22c55e"/></linearGradient>
<linearGradient id="gAmber" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f59e0b"/><stop offset="1" stop-color="#fcd34d"/></linearGradient>
<linearGradient id="gMeter" gradientUnits="userSpaceOnUse" x1="480" y1="0" x2="640" y2="0">
  <stop offset="0" stop-color="{AMBER_LIGHT}"/><stop offset=".5" stop-color="{AMBER_LIGHT}"/>
  <stop offset=".6" stop-color="{GREEN_LIGHT}"/><stop offset="1" stop-color="{GREEN_LIGHT}"/></linearGradient>
<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="#1e1b4b" flood-opacity=".35"/></filter>
<filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="7"/></filter>
{marker("arW", "#ffffff")}{marker("arG", GREEN_LIGHT)}{marker("arA", AMBER_LIGHT)}
</defs>"""


def doc_card(y: int, grad: str, ico: str, title: str, sub: str) -> str:
    return (f'<g filter="url(#shadow)"><rect x="0" y="{y}" width="226" height="84" rx="18" fill="#fff" fill-opacity=".96"/></g>'
            f'<circle cx="46" cy="{y + 42}" r="27" fill="url(#{grad})"/>'
            f'{icon(ico, 30, y + 26, 32)}'
            f'<text x="86" y="{y + 38}" {FONT} font-weight="700" font-size="20" fill="{INK}">{title}</text>'
            f'<text x="86" y="{y + 61}" {FONT} font-size="14" fill="{MUTED}">{sub}</text>')


def diagram(animated: bool) -> str:
    """The pipeline drawn on a 1100x330 canvas. Static = everything lit."""
    # y of the three document cards, then the paths between nodes.
    docs = (10, 123, 236)
    p_docs = [f"M226 {y + 42} C 262 {y + 42}, 262 165, 296 165" for y in docs]
    p_q = "M370 84 L370 108"
    p_ret = "M456 165 L494 165"
    p_green = "M624 165 C 662 165, 662 80, 700 80"
    p_amber = "M624 165 C 662 165, 662 255, 700 255"

    out = [defs()]

    # flow lines first so the nodes sit on top
    for p in p_docs:
        out.append(f'<path d="{p}" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="3.5" '
                   f'stroke-linecap="round" stroke-dasharray="2 9" marker-end="url(#arW)"/>')
    out.append(f'<path d="{p_q}" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="3.5" '
               f'stroke-linecap="round" marker-end="url(#arW)"/>')
    out.append(f'<path d="{p_ret}" fill="none" stroke="#fff" stroke-opacity=".85" stroke-width="3.5" '
               f'stroke-linecap="round" marker-end="url(#arW)"/>')

    # per-scenario timing (fractions of the cycle)
    def sc(i: int) -> dict[str, float]:
        b = i * 0.5
        return {"b": b, "docs": b + 0.02, "ret": b + 0.10, "gate": b + 0.15, "meter": b + 0.19,
                "decide": b + 0.26, "show": b + 0.31, "hold": b + 0.45, "end": b + 0.49}

    s1, s2 = sc(0), sc(1)
    lit_green = merge(window(DIM, 1, s1["decide"], s1["show"], s1["hold"], s1["end"]), lo=DIM)
    lit_amber = merge(window(DIM, 1, s2["decide"], s2["show"], s2["hold"], s2["end"]), lo=DIM)
    out.append(
        f'<path d="{p_green}" fill="none" stroke="{GREEN_LIGHT}" stroke-width="5" stroke-linecap="round" '
        f'marker-end="url(#arG)">{animate("opacity", lit_green) if animated else ""}</path>')
    out.append(
        f'<path d="{p_amber}" fill="none" stroke="{AMBER_LIGHT}" stroke-width="5" stroke-linecap="round" '
        f'marker-end="url(#arA)">{animate("opacity", lit_amber) if animated else ""}</path>')
    # yes / no tags on the branches
    for (cx, cy, c, txt) in ((660, 118, GREEN, "yes"), (660, 212, "#b45309", "no")):
        out.append(f'<rect x="{cx - 21}" y="{cy - 12}" width="42" height="24" rx="12" fill="#fff"/>'
                   f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" {FONT} font-weight="700" '
                   f'font-size="14" fill="{c}">{txt}</text>')

    # --- question pill -------------------------------------------------
    pill = (f'<rect x="270" y="44" width="246" height="40" rx="20" fill="#fff" fill-opacity=".96" filter="url(#shadow)"/>'
            f'{icon("ask", 282, 52, 24, "#7c3aed", 2.2)}')
    if animated:
        for i, s in enumerate(SCENARIOS):
            q = sc(i)
            a = animate("opacity", merge(window(0, 1, q["b"], q["b"] + 0.015, q["hold"], q["end"]), lo=0))
            pill += (f'<text x="314" y="70" {FONT} font-weight="700" font-size="15" fill="{INK}" opacity="0">'
                     f'{html.escape(s["question"])}{a}</text>')
    else:
        pill += f'<text x="314" y="70" {FONT} font-weight="700" font-size="16" fill="{INK}">Questionnaire item</text>'
    out.append(pill)

    # --- documents -----------------------------------------------------
    out.append(doc_card(docs[0], "gSoc", "shield", "SOC 2 report", "Type II controls"))
    out.append(doc_card(docs[1], "gPol", "doc", "Policy", "Access, encryption"))
    out.append(doc_card(docs[2], "gAud", "audit", "Audit report", "Findings, evidence"))
    if animated:  # each document lights up as its text is picked up
        for i, y in enumerate(docs):
            pts: list[tuple[float, float]] = []
            for s in (s1, s2):
                t = s["docs"] + 0.012 * i
                pts += window(0, 1, t, t + 0.015, t + 0.06, t + 0.08)
            out.append(f'<rect x="-3" y="{y - 3}" width="232" height="90" rx="21" fill="none" stroke="#fde68a" '
                       f'stroke-width="4" opacity="0">{animate("opacity", merge(pts, lo=0))}</rect>')

    # --- retrieval node ------------------------------------------------
    out.append('<g filter="url(#shadow)"><rect x="296" y="108" width="160" height="114" rx="22" fill="url(#gRet)"/></g>')
    out.append(f'<circle cx="376" cy="148" r="25" fill="#fff" fill-opacity=".2"/>{icon("search", 358, 130, 36, sw=2.2)}')
    out.append(f'<text x="376" y="195" text-anchor="middle" {FONT} font-weight="700" font-size="21" fill="#fff">Retrieve</text>'
               f'<text x="376" y="214" text-anchor="middle" {FONT} font-size="13.5" fill="#fff" fill-opacity=".92">best matching chunks</text>')
    if animated:
        pts = []
        for s in (s1, s2):
            pts += window(0, 1, s["ret"], s["ret"] + 0.02, s["ret"] + 0.07, s["ret"] + 0.10)
        out.append(f'<rect x="296" y="108" width="160" height="114" rx="22" fill="none" stroke="#fff" stroke-width="4" '
                   f'opacity="0">{animate("opacity", merge(pts, lo=0))}</rect>')

    # --- confidence gate -----------------------------------------------
    gcx, gcy, gr = 560, 165, 66
    diamond = f"M{gcx} {gcy - gr} L{gcx + gr} {gcy} L{gcx} {gcy + gr} L{gcx - gr} {gcy} Z"
    out.append(f'<g filter="url(#shadow)"><path d="{diamond}" fill="url(#gGate)" stroke="#fff" stroke-width="3" stroke-linejoin="round"/></g>')
    out.append(f'<circle cx="{gcx}" cy="{gcy}" r="25" fill="#fff" fill-opacity=".22"/>{icon("gauge", gcx - 20, gcy - 20, 40, sw=2.2)}')
    if animated:
        for s, c in ((s1, GREEN_LIGHT), (s2, AMBER_LIGHT)):
            out.append(f'<path d="{diamond}" fill="none" stroke="{c}" stroke-width="7" stroke-linejoin="round" opacity="0">'
                       f'{animate("opacity", merge(window(0, 1, s["decide"] - 0.03, s["decide"], s["hold"], s["end"]), lo=0))}</path>')
    out.append(f'<text x="{gcx}" y="262" text-anchor="middle" {FONT} font-weight="700" font-size="19" fill="#fff">Confidence gate</text>')
    # score meter: track, fill (animated), threshold tick
    out.append('<rect x="480" y="274" width="160" height="14" rx="7" fill="#1e1b4b" fill-opacity=".35"/>')
    if animated:
        w = lambda lvl: f"{160 * lvl:.1f}"  # noqa: E731
        pts = [(0.0, "0")]
        for s, sc_ in ((s1, SCENARIOS[0]), (s2, SCENARIOS[1])):
            pts += [(s["meter"], "0"), (s["meter"] + 0.05, w(sc_["level"])), (s["hold"], w(sc_["level"])), (s["end"], "0")]
        out.append(f'<rect x="480" y="274" width="0" height="14" rx="7" fill="url(#gMeter)">{animate("width", pts)}</rect>')
    else:
        out.append('<rect x="480" y="274" width="104" height="14" rx="7" fill="url(#gMeter)"/>')
    out.append('<rect x="567" y="269" width="4" height="24" rx="2" fill="#fff"/>')
    out.append(f'<text x="{gcx}" y="314" text-anchor="middle" {FONT} font-size="14" fill="#fff" fill-opacity=".95">min confidence to answer</text>')

    # --- outcome 1: answer + cited source ------------------------------
    g_pts = merge(window(DIM, 1, s1["decide"], s1["show"], s1["hold"], s1["end"]), lo=DIM)
    gopen = f'<g opacity="1">{animate("opacity", g_pts)}' if animated else '<g>'
    out.append(gopen)
    out.append('<g filter="url(#shadow)"><rect x="700" y="4" width="400" height="152" rx="20" fill="#fff"/></g>')
    out.append('<path d="M700 24a20 20 0 0 1 20-20h360a20 20 0 0 1 20 20v22H700z" fill="url(#gGreen)"/>')
    out.append(f'{icon("check", 716, 13, 26, sw=2.2)}<text x="752" y="33" {FONT} font-weight="700" font-size="20" fill="#fff">Answer + cited source</text>')
    out.append(f'<text x="718" y="78" {FONT} font-weight="700" font-size="17" fill="{INK}">Yes. Customer data at rest is</text>'
               f'<text x="718" y="100" {FONT} font-weight="700" font-size="17" fill="{INK}">encrypted with AES-256.</text>')
    out.append(f'<rect x="718" y="114" width="236" height="30" rx="15" fill="#dcfce7" stroke="{GREEN}" stroke-width="1.5"/>'
               f'{icon("link", 727, 120, 18, GREEN, 2.4)}'
               f'<text x="752" y="134" {FONT} font-weight="700" font-size="14.5" fill="#166534">SOC 2 Type II, p. 14</text>')
    out.append(f'<text x="1082" y="134" text-anchor="end" {FONT} font-size="14" fill="{MUTED}">confidence</text>'
               f'<text x="1082" y="102" text-anchor="end" {FONT} font-weight="700" font-size="30" fill="{GREEN}">0.86</text>')
    out.append('</g>')

    # --- outcome 2: insufficient evidence ------------------------------
    a_pts = merge(window(DIM, 1, s2["decide"], s2["show"], s2["hold"], s2["end"]), lo=DIM)
    aopen = f'<g opacity="1">{animate("opacity", a_pts)}' if animated else '<g>'
    out.append(aopen)
    out.append('<g filter="url(#shadow)"><rect x="700" y="184" width="400" height="142" rx="20" fill="#fff"/></g>')
    out.append('<path d="M700 204a20 20 0 0 1 20-20h360a20 20 0 0 1 20 20v22H700z" fill="url(#gAmber)"/>')
    out.append(f'{icon("warn", 716, 192, 26, "#451a03", 2.2)}<text x="752" y="213" {FONT} font-weight="700" font-size="20" fill="#451a03">Insufficient evidence</text>')
    out.append(f'<text x="718" y="258" {FONT} font-weight="700" font-size="17" fill="{INK}">Nothing in the evidence backs</text>'
               f'<text x="718" y="280" {FONT} font-weight="700" font-size="17" fill="{INK}">this one, so it does not guess.</text>')
    out.append(f'<rect x="718" y="292" width="236" height="28" rx="14" fill="#fef3c7" stroke="#d97706" stroke-width="1.5"/>'
               f'<text x="836" y="311" text-anchor="middle" {FONT} font-weight="700" font-size="14.5" fill="#92400e">No model call. Gap flagged.</text>')
    out.append('</g>')

    # --- travelling dots -----------------------------------------------
    if animated:
        for s in (s1, s2):
            for i, p in enumerate(p_docs):
                t = s["docs"] + 0.012 * i
                out.append(dot(p, t, t + 0.07, "#f472b6" if i == 2 else "#22d3ee" if i == 1 else "#a78bfa"))
            out.append(dot(p_q, s["b"] + 0.02, s["b"] + 0.07, "#facc15", 5))
            out.append(dot(p_ret, s["gate"] - 0.02, s["gate"] + 0.03, "#22d3ee"))
        out.append(dot(p_green, s1["decide"], s1["show"] + 0.02, GREEN_LIGHT, 7))
        out.append(dot(p_amber, s2["decide"], s2["show"] + 0.02, AMBER_LIGHT, 7))
    return "\n".join(out)


# --- outputs ---------------------------------------------------------------

def flow_svg() -> str:
    """The animated SVG for the post body: its own gradient panel, no scripts."""
    w, h = 1200, 470
    captions = ""
    for i, s in enumerate(SCENARIOS):
        b = i * 0.5
        a = animate("opacity", merge(window(0, 1, b, b + 0.02, b + 0.45, b + 0.49), lo=0))
        captions += (f'<text x="600" y="425" text-anchor="middle" {FONT} font-weight="700" font-size="22" '
                     f'fill="#fff" opacity="0">{html.escape(s["caption"])}{a}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">
<title id="t">{html.escape(SVG_TITLE)}</title>
<desc id="d">{html.escape(SVG_DESC)}</desc>
<style>{font_faces()}</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3730a3"/><stop offset=".5" stop-color="#7c3aed"/><stop offset="1" stop-color="#be185d"/></linearGradient>
<radialGradient id="b1" cx=".1" cy="1" r=".6"><stop offset="0" stop-color="#06b6d4" stop-opacity=".55"/><stop offset="1" stop-color="#06b6d4" stop-opacity="0"/></radialGradient>
<radialGradient id="b2" cx=".92" cy=".05" r=".5"><stop offset="0" stop-color="#f59e0b" stop-opacity=".35"/><stop offset="1" stop-color="#f59e0b" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{w}" height="{h}" rx="28" fill="url(#bg)"/>
<rect width="{w}" height="{h}" rx="28" fill="url(#b1)"/>
<rect width="{w}" height="{h}" rx="28" fill="url(#b2)"/>
<g transform="translate(50,40)">
{diagram(True)}
</g>
<rect x="250" y="394" width="700" height="46" rx="23" fill="#1e1b4b" fill-opacity=".35"/>
{captions}
</svg>
"""


def card_html() -> str:
    """The static 1200x630 hero: gradient background, headline, diagram."""
    e = html.escape
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
{font_faces()}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {hero.WIDTH}px; height: {hero.HEIGHT}px; }}
body {{
  font-family: 'Space Grotesk', sans-serif; color: #fff; position: relative; overflow: hidden;
  background:
    radial-gradient(circle at 6% 104%, rgba(6,182,212,.60) 0, transparent 46%),
    radial-gradient(circle at 96% 100%, rgba(245,158,11,.38) 0, transparent 40%),
    radial-gradient(circle at 78% 40%, rgba(236,72,153,.42) 0, transparent 46%),
    linear-gradient(125deg, #3730a3 0%, #6d28d9 48%, #be185d 100%);
}}
.dots {{ position: absolute; inset: 0; opacity: .5;
  background-image: radial-gradient(rgba(255,255,255,.22) 1.5px, transparent 1.6px); background-size: 28px 28px;
  -webkit-mask-image: linear-gradient(180deg, #000 0, transparent 55%); mask-image: linear-gradient(180deg, #000 0, transparent 55%); }}
.headline {{ position: absolute; left: 50px; top: 38px; font-weight: 700; font-size: 62px; line-height: 1.05;
  letter-spacing: -0.015em; white-space: nowrap; }}
.headline span {{ background: linear-gradient(90deg, #fff 0%, #fde68a 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.sub {{ position: absolute; left: 52px; top: 118px; font-size: 27px; line-height: 1.25; color: #f5f3ff; white-space: nowrap; }}
svg.diagram {{ position: absolute; left: 50px; top: 196px; }}
.site {{ position: absolute; right: 50px; bottom: 20px; font-weight: 700; font-size: 23px; color: #fff; opacity: .92; }}
</style></head><body>
<div class="dots"></div>
<div class="headline"><span>{e(HEADLINE)}</span></div>
<div class="sub">{e(SUBTITLE)}</div>
<svg class="diagram" width="{DIAGRAM_W}" height="{DIAGRAM_H}" viewBox="0 0 {DIAGRAM_W} {DIAGRAM_H}" xmlns="http://www.w3.org/2000/svg">
{diagram(False)}
</svg>
<div class="site">{hero.SITE}</div>
</body></html>
"""


FRAME_TIMES = (1.0, 2.6, 5.0, 9.0, 12.0)  # docs flow, gate scoring, green lit, quiet, amber lit


def render_frames(svg: Path, out_dir: Path, times: tuple[float, ...] = FRAME_TIMES) -> list[Path]:
    """Screenshot the animated SVG paused at each time, to check every state by eye."""
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 470})
        page.goto(svg.resolve().as_uri())
        page.evaluate("document.fonts.ready")
        for t in times:
            page.evaluate(f"(() => {{ const s = document.documentElement; s.pauseAnimations(); s.setCurrentTime({t}); }})()")
            shot = out_dir / f"flow-{t:05.2f}s.png"
            page.screenshot(path=str(shot))
            shots.append(shot)
        browser.close()
    return shots


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--png", type=Path, default=PNG_OUT, help="static hero PNG (default: the post's hero)")
    ap.add_argument("--svg", type=Path, default=SVG_OUT, help="animated flow SVG (default: the post's flow)")
    ap.add_argument("--html", type=Path, help="write only the hero card's HTML to this file (no browser)")
    ap.add_argument("--frames", type=Path, metavar="DIR",
                    help="also screenshot the animated SVG paused at a few times into DIR")
    args = ap.parse_args(argv)

    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(card_html())
        print(args.html)
        return 0
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(flow_svg())
    print(args.svg)
    args.png.parent.mkdir(parents=True, exist_ok=True)
    hero.render_png(card_html(), args.png)
    print(args.png)
    if args.frames:
        for shot in render_frames(args.svg, args.frames):
            print(shot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
