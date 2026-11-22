#!/usr/bin/env python3
"""Draw the animated confidence-gate flowchart of the questionnaire post.

The post's section "A confidence gate that runs before the LLM" used to carry a plain
mermaid flowchart. This module redraws the same nodes and the same logic as one
self-contained animated SVG, in the family of tools/hero_diagram.py and tools/hero_kit.py:
gradient nodes per stage type, an icon per stage, a diamond gate with a score meter, a
green "yes" path and an amber "no" path, dots flowing along the connectors, and a loop
that lights the green path, then the amber one.

    question -> embed question -> retrieve top-k from evidence store -> gate
    gate: best score above min_confidence?
      no  -> insufficient evidence, NO LLM call
      yes -> rerank (wide window) -> LLM drafts a cited answer -> determination + citations + confidence

SMIL only, no scripts, the font inlined, a still under prefers-reduced-motion, and a
rounded panel with its own background so it reads on both the light and dark theme.

    python tools/hero_gate.py                    # write assets/img/posts/questionnaire-confidence-gate-flow.svg
    python tools/hero_gate.py --frames DIR       # also paused screenshots on a dark and a light page
    python tools/hero_gate.py --check            # render and fail if a label overflows its box
"""
import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402
import hero_kit as kit  # noqa: E402

ROOT = hero.ROOT
SVG_OUT = ROOT / "assets" / "img" / "posts" / "questionnaire-confidence-gate-flow.svg"
IMG_PATH = "/assets/img/posts/questionnaire-confidence-gate-flow.svg"

W, H = 1200, 540
CYCLE = 20.0
SCENARIO = CYCLE / 2          # the loop plays two questions: one clears the gate, one does not
DIM = 0.38                    # opacity of a stage the question has not reached (or never will)

TITLE = "A confidence gate that runs before the LLM"
DESC = (
    "A question is embedded, then the top-k matches are retrieved from the evidence store. A gate asks whether the best "
    "score is above min_confidence. If not, the result is insufficient evidence and the LLM is never called. If so, the "
    "matches are reranked over a wide window and the LLM drafts a cited answer, returned as a determination with "
    "citations and a confidence."
)
ALT = (
    "Animated flowchart: a question is embedded and the top-k are retrieved from the evidence store; a diamond gate asks "
    "whether the best score is above min_confidence; the no path ends at insufficient evidence with no LLM call, and the "
    "yes path goes through rerank with a wide window and an LLM that drafts a cited answer, ending in a determination "
    "with citations and confidence"
)
CAPTION = (
    "_The gate runs before the LLM: a weak best score ends at insufficient evidence with no LLM call; a strong one is "
    "reranked and drafted into a cited answer._"
)

# Story card, one per phase; the lines are as short as the card is narrow.
STORY_PRE = ("Embed the question,", "retrieve top-k from the", "evidence store, and", "score the best match.")
STORY_YES = ("Best score above", "min_confidence: rerank,", "then the LLM drafts", "a cited answer.")
STORY_NO = ("Best score not above", "min_confidence:", "insufficient evidence,", "NO LLM call.")
STORY_STILL = ("Above min_confidence: the", "yes path. Not above:", "insufficient evidence,", "NO LLM call.")

FONT = kit.FONT
GREEN, GREEN_L, AMBER, AMBER_L = kit.GREEN, kit.GREEN_LIGHT, kit.AMBER, kit.AMBER_LIGHT
PANEL = ("#0b1f4d", "#312e81", "#115e59")  # navy, indigo, deep teal

# geometry (absolute canvas coordinates)
ROW1_Y, ROW2_Y, NH = 90, 380, 120          # top of each row, node height
GATE = (798, 150, 108)                     # cx, cy, r
METER_X, METER_W = GATE[0] - 50, 100       # score meter inside the diamond
LEVEL_YES, LEVEL_NO, LEVEL_STILL = 0.86, 0.2, 0.62
THRESHOLD = 0.6


# --- a stage -------------------------------------------------------------------

def stage(x: float, y: float, w: float, grad: str, ico: str, line1: str, line2: str | None = None, *,
          sub_weight: int = 400, tsize: float = 19, ssize: float = 15, text: str = "#fff") -> str:
    """Gradient card: an icon in a soft disc, then one or two centred lines."""
    cx = x + w / 2
    out = f'<g filter="url(#shadow)">{kit.rect(x, y, w, NH, 22, kit.g(grad))}</g>'
    out += f'<circle cx="{cx:g}" cy="{y + 34:g}" r="22" fill="#fff" fill-opacity=".22"/>'
    out += kit.icon(ico, cx - 15, y + 19, 30, text, 2.2)
    if line2:
        out += kit.T(cx, y + 84, line1, tsize, text, anchor="middle", maxw=w - 16)
        out += kit.T(cx, y + 105, line2, ssize, text, sub_weight, "middle", maxw=w - 16, op=.95)
    else:
        out += kit.T(cx, y + 96, line1, tsize, text, anchor="middle", maxw=w - 16)
    return out


def badge(cx: float, cy: float, n: int) -> str:
    return (f'<circle cx="{cx:g}" cy="{cy:g}" r="13" fill="#fff" stroke="#1e1b4b" stroke-opacity=".25" stroke-width="1.5"/>'
            + kit.T(cx, cy + 5.5, str(n), 15, kit.INK, anchor="middle"))


def tag(cx: float, cy: float, text: str, color: str) -> str:
    return (kit.rect(cx - 23, cy - 13, 46, 26, 13, "#fff") + kit.T(cx, cy + 5, text, 15, color, anchor="middle"))


# --- timeline ---------------------------------------------------------------------

def tl(b: float) -> dict[str, float]:
    """Moments inside one scenario that starts at time b."""
    return {
        "q": b + .1, "d1": b + .5, "emb": b + 1.2, "d2": b + 1.7, "ret": b + 2.4, "d3": b + 2.9,
        "score": b + 3.7, "meter": b + 3.9, "decide": b + 4.7,
        "d_yes": b + 4.7, "rerank": b + 5.5, "d_rl": b + 6.0, "llm": b + 6.7, "d_la": b + 7.2, "ans": b + 7.9,
        "d_no": b + 4.7, "ins": b + 5.5, "end": b + 9.5,
    }


def build(ctx: kit.Ctx) -> str:
    """The whole drawing on the WxH canvas; ctx decides animated or the lit still."""
    a, n = tl(0.0), tl(SCENARIO)
    gx, gy, gr = GATE
    out: list[str] = []
    animated = ctx.animated
    end_a, end_n = a["end"], n["end"]

    # positions
    q = (30, ROW1_Y, 150)
    emb = (225, ROW1_Y, 170)
    ret = (440, ROW1_Y, 200)
    ins = (966, ROW1_Y, 204)
    rr = (gx - 85, ROW2_Y, 170)
    llm = (rr[0] - 48 - 190, ROW2_Y, 190)
    ans = (llm[0] - 48 - 280, ROW2_Y, 280)
    card = (922, ROW2_Y, 248)

    def mid_y(row_y: float) -> float:
        return row_y + NH / 2

    # --- connectors (under the nodes) -------------------------------------------------
    def base_line(d: str) -> str:
        dash_anim = ('<animate attributeName="stroke-dashoffset" from="0" to="-11" dur="1s" repeatCount="indefinite"/>'
                     if animated else "")
        return (f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3.5" stroke-linecap="round" '
                f'stroke-dasharray="2 9" marker-end="url(#ar-white)">{dash_anim}</path>')

    p_qe = f"M{q[0] + q[2]} {mid_y(ROW1_Y)} L{emb[0] - 6} {mid_y(ROW1_Y)}"
    p_er = f"M{emb[0] + emb[2]} {mid_y(ROW1_Y)} L{ret[0] - 6} {mid_y(ROW1_Y)}"
    p_rg = f"M{ret[0] + ret[2]} {mid_y(ROW1_Y)} L{gx - gr - 6} {gy}"
    p_no = f"M{gx + gr} {gy} L{ins[0] - 6} {gy}"
    p_yes = f"M{gx} {gy + gr} L{gx} {ROW2_Y - 6}"
    p_rl = f"M{rr[0]} {mid_y(ROW2_Y)} L{llm[0] + llm[2] + 6} {mid_y(ROW2_Y)}"
    p_la = f"M{llm[0]} {mid_y(ROW2_Y)} L{ans[0] + ans[2] + 6} {mid_y(ROW2_Y)}"
    for p in (p_qe, p_er, p_rg):
        out.append(base_line(p))

    def lit_line(d: str, color: str, start: float, end: float) -> str:
        line = kit.arrow(d, color, 5, op=1)
        return ctx.dim(line, (start, end), lo=DIM)

    out.append(lit_line(p_yes, "green", a["d_yes"], end_a))
    out.append(lit_line(p_rl, "green", a["d_rl"], end_a))
    out.append(lit_line(p_la, "green", a["d_la"], end_a))
    out.append(lit_line(p_no, "amber", n["d_no"], end_n))

    # --- stages ------------------------------------------------------------------------
    # The first four are always on screen; the rest light up as the question reaches them.
    out.append(stage(*q[:3], "sky", "ask", "question"))
    out.append(stage(*emb[:3], "indigo", "layers", "embed question"))
    out.append(stage(*ret[:3], "teal", "search", "retrieve top-k", "from evidence store"))
    for r_, color, spans in (
        (q, "#fde68a", ((a["q"], a["d1"] + .6), (n["q"], n["d1"] + .6))),
        (emb, "#fde68a", ((a["emb"], a["d2"] + .6), (n["emb"], n["d2"] + .6))),
        (ret, "#fde68a", ((a["ret"], a["d3"] + .6), (n["ret"], n["d3"] + .6))),
    ):
        out.append(ctx.ring(r_[0] - 4, r_[1] - 4, r_[2] + 8, NH + 8, 25, color, *spans))

    # the green stages, dim until the yes path reaches them
    def green_stage(box: tuple, ico: str, l1: str, l2: str | None, grad: str, t_in: float, t_out: float,
                    sub_weight: int = 400) -> str:
        s = stage(*box[:3], grad, ico, l1, l2, sub_weight=sub_weight)
        ring = ctx.ring(box[0] - 4, box[1] - 4, box[2] + 8, NH + 8, 25, GREEN_L, (t_in, t_out))
        return ctx.dim(s, (t_in, t_out), lo=DIM) + ring

    out.append(green_stage(rr, "compare", "rerank", "wide window", "blue", a["rerank"], end_a))
    out.append(green_stage(llm, "sparkle", "LLM drafts a", "cited answer", "violet", a["llm"], end_a, 700))

    # outcome: determination + citations + confidence (a green result card)
    answer = (f'<g filter="url(#shadow)">{kit.rect(ans[0], ans[1], ans[2], NH, 22, kit.g("green"))}</g>'
              f'<circle cx="{ans[0] + 46:g}" cy="{mid_y(ROW2_Y):g}" r="27" fill="#fff" fill-opacity=".22"/>'
              + kit.icon("check", ans[0] + 28, mid_y(ROW2_Y) - 18, 36, "#fff", 2.4)
              + kit.T(ans[0] + 84, mid_y(ROW2_Y) - 4, "determination +", 20, "#fff", maxw=ans[2] - 96)
              + kit.T(ans[0] + 84, mid_y(ROW2_Y) + 22, "citations + confidence", 16.5, "#fff", maxw=ans[2] - 96))
    ans_ring = ctx.ring(ans[0] - 4, ans[1] - 4, ans[2] + 8, NH + 8, 25, GREEN_L, (a["ans"], end_a))
    out.append(ctx.dim(answer, (a["ans"], end_a), lo=DIM) + ans_ring)

    # outcome: insufficient evidence, NO LLM call (an amber card)
    cx_i = ins[0] + ins[2] / 2
    amber = (f'<g filter="url(#shadow)">{kit.rect(ins[0], ins[1], ins[2], NH, 22, kit.g("amber"))}</g>'
             f'<circle cx="{cx_i:g}" cy="{ins[1] + 34:g}" r="22" fill="#451a03" fill-opacity=".14"/>'
             + kit.icon("warn", cx_i - 15, ins[1] + 19, 30, "#451a03", 2.2)
             + kit.T(cx_i, ins[1] + 80, "insufficient evidence", 17.5, "#451a03", anchor="middle", maxw=ins[2] - 16)
             + kit.rect(cx_i - 56, ins[1] + 90, 112, 24, 12, "#451a03")
             + kit.T(cx_i, ins[1] + 107, "NO LLM call", 14.5, "#fde68a", anchor="middle", maxw=100))
    ins_ring = ctx.ring(ins[0] - 4, ins[1] - 4, ins[2] + 8, NH + 8, 25, AMBER_L, (n["ins"], end_n))
    out.append(ctx.dim(amber, (n["ins"], end_n), lo=DIM) + ins_ring)

    # yes / no tags on the branches
    out.append(tag(gx, (gy + gr + ROW2_Y) / 2, "yes", "#15803d"))
    out.append(tag((gx + gr + ins[0]) / 2, gy - 24, "no", "#b45309"))

    # --- the gate -----------------------------------------------------------------------
    d = kit.diamond_path(gx, gy, gr)
    glow = (f'<path d="{d}" fill="{GREEN_L}" filter="url(#glow)" opacity=".8"/>')
    glow_n = (f'<path d="{d}" fill="{AMBER_L}" filter="url(#glow)" opacity=".8"/>')
    out.append(ctx.show(glow, (a["decide"], end_a), fade=.4))
    out.append(ctx.show(glow_n, (n["decide"], end_n), fade=.4))
    out.append(f'<g filter="url(#shadow)"><path d="{d}" fill="{kit.g("plum")}" stroke="#fff" stroke-width="3" '
               f'stroke-linejoin="round"/></g>')
    out.append(f'<circle cx="{gx}" cy="{gy - 40}" r="19" fill="#fff" fill-opacity=".22"/>{kit.icon("gauge", gx - 14, gy - 54, 28, sw=2.2)}')
    out.append(kit.T(gx, gy + 4, "best score above", 16.5, "#fff", anchor="middle", maxw=150))
    out.append(kit.T(gx, gy + 24, "min_confidence?", 16.5, "#fff", anchor="middle", maxw=150))
    # score meter: track, fill, threshold tick
    my = gy + 38
    out.append(kit.rect(METER_X, my, METER_W, 12, 6, "#1e1b4b", 'fill-opacity=".4"'))
    if animated:
        pts: list[tuple[float, float]] = [(0, 0)]
        for t, level, end in ((a, LEVEL_YES, end_a), (n, LEVEL_NO, end_n)):
            pts += [(t["meter"] - .01, 0), (t["meter"] + .9, METER_W * level), (end, METER_W * level), (end + .4, 0)]
        fill = (f'<rect x="{METER_X}" y="{my}" width="0" height="12" rx="6" fill="url(#gMeter)">'
                f'{ctx.animate("width", sorted(pts))}</rect>')
    else:
        fill = f'<rect x="{METER_X}" y="{my}" width="{METER_W * LEVEL_STILL:g}" height="12" rx="6" fill="url(#gMeter)"/>'
    out.append(fill)
    out.append(kit.rect(METER_X + METER_W * THRESHOLD - 2, my - 5, 4, 22, 2, "#fff"))
    out.append(ctx.ring_path(d, GREEN_L, (a["decide"], end_a)))
    out.append(ctx.ring_path(d, AMBER_L, (n["decide"], end_n)))
    out.append(ctx.ring_path(d, "#fde68a", (a["score"], a["decide"]), (n["score"], n["decide"]), width=5))

    # step numbers: 1-4 along the top row, 5-7 along the bottom row
    for (x, y, _w), num in ((q, 1), (emb, 2), (ret, 3)):
        out.append(badge(x + 4, y + 4, num))
    out.append(badge(gx - 56, gy - 56, 4))
    for (x, y, w), num in ((rr, 5), (llm, 6), (ans, 7)):
        out.append(badge(x + w - 4, y + 4, num))

    # --- travelling dots ------------------------------------------------------------------
    for t, end in ((a, end_a), (n, end_n)):
        out.append(ctx.dot(p_qe, t["d1"], t["d1"] + .9, "#7dd3fc", 5))
        out.append(ctx.dot(p_er, t["d2"], t["d2"] + .9, "#a5b4fc", 5))
        out.append(ctx.dot(p_rg, t["d3"], t["d3"] + .9, "#5eead4", 5))
    out.append(ctx.dot(p_yes, a["d_yes"], a["d_yes"] + .8, GREEN_L, 7))
    out.append(ctx.dot(p_rl, a["d_rl"], a["d_rl"] + .7, GREEN_L, 7))
    out.append(ctx.dot(p_la, a["d_la"], a["d_la"] + .7, GREEN_L, 7))
    out.append(ctx.dot(p_no, n["d_no"], n["d_no"] + .8, AMBER_L, 7))

    # --- story card ---------------------------------------------------------------------
    cx0, cy0, cw = card
    out.append(f'<g filter="url(#shadow)">{kit.rect(cx0, cy0, cw, NH, 18, "#0b1f4d", "fill-opacity=\".55\"")}</g>')
    out.append(kit.rect(cx0, cy0, cw, NH, 18, "none", 'stroke="#fff" stroke-opacity=".28" stroke-width="1.5"'))
    phases = (
        (STORY_PRE, "#7dd3fc", ((a["q"], a["score"] + .5), (n["q"], n["score"] + .5))),
        (STORY_YES, GREEN_L, ((a["decide"] + .1, end_a),)),
        (STORY_NO, AMBER_L, ((n["decide"] + .1, end_n),)),
    )
    if animated:
        for lines_, color, spans in phases:
            body = kit.rect(cx0, cy0 + 16, 5, NH - 32, 2.5, color) + "".join(
                kit.T(cx0 + 20, cy0 + 31 + i * 24, ln, 16.5, "#fff", 400, maxw=cw - 30) for i, ln in enumerate(lines_))
            out.append(ctx.show(body, *spans, fade=.3))
    else:
        out.append(kit.rect(cx0, cy0 + 16, 5, NH - 32, 2.5, "#7dd3fc"))
        out.extend(kit.T(cx0 + 20, cy0 + 31 + i * 24, ln, 16.5, "#fff", 400, maxw=cw - 30)
                   for i, ln in enumerate(STORY_STILL))
    return "\n".join(o for o in out if o)


# --- the document ---------------------------------------------------------------------

def defs() -> str:
    gx = METER_X
    meter = (f'<linearGradient id="gMeter" gradientUnits="userSpaceOnUse" x1="{gx}" y1="0" x2="{gx + METER_W}" y2="0">'
             f'<stop offset="0" stop-color="{AMBER_L}"/><stop offset="{THRESHOLD - .02:g}" stop-color="{AMBER_L}"/>'
             f'<stop offset="{THRESHOLD + .02:g}" stop-color="{GREEN_L}"/><stop offset="1" stop-color="{GREEN_L}"/></linearGradient>')
    return kit.defs().replace("</defs>", meter + "\n</defs>")


def flow_svg() -> str:
    """The animated SVG for the post body, with a still version for reduced motion."""
    a, b, c = PANEL
    motion, still = build(kit.Ctx(CYCLE)), build(kit.Ctx())
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">{html.escape(TITLE)}</title>
<desc id="d">{html.escape(DESC)}</desc>
<style>{kit.font_faces()}
.still {{ display: none; }}
@media (prefers-reduced-motion: reduce) {{ .motion {{ display: none; }} .still {{ display: inline; }} }}
</style>
{defs()}
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>
<radialGradient id="b1" cx=".08" cy="1" r=".6"><stop offset="0" stop-color="#22d3ee" stop-opacity=".5"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
<radialGradient id="b2" cx=".95" cy=".02" r=".5"><stop offset="0" stop-color="#f59e0b" stop-opacity=".38"/><stop offset="1" stop-color="#f59e0b" stop-opacity="0"/></radialGradient>
<radialGradient id="b3" cx=".55" cy=".85" r=".45"><stop offset="0" stop-color="#34d399" stop-opacity=".25"/><stop offset="1" stop-color="#34d399" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.5" fill="#fff" fill-opacity=".16"/></pattern>
<rect width="{W}" height="{H}" rx="28" fill="url(#bg)"/>
<rect width="{W}" height="{H}" rx="28" fill="url(#b1)"/>
<rect width="{W}" height="{H}" rx="28" fill="url(#b2)"/>
<rect width="{W}" height="{H}" rx="28" fill="url(#b3)"/>
<rect width="{W}" height="{H}" rx="28" fill="url(#dots)" opacity=".7"/>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="27" fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="2"/>
<g class="motion">{motion}</g>
<g class="still">{still}</g>
</svg>
"""


# --- frames and checks ------------------------------------------------------------------

FRAME_TIMES = (2.2, 8.6, 18.0)  # question flowing to the gate, green path lit, amber path lit
BACKGROUNDS = {"dark": "#1b1b1e", "light": "#ffffff"}  # the blog's dark page and a light page

_OVERFLOW_JS = """
() => {
  const bad = [];
  const box = document.documentElement.getBoundingClientRect();
  document.querySelectorAll('svg text').forEach(t => {
    const r = t.getBoundingClientRect();
    if (!r.width) return;
    const label = (t.textContent || '').slice(0, 40);
    const maxw = parseFloat(t.dataset.maxw || '0');
    if (maxw && r.width > maxw + 1.5) bad.push(`"${label}" is ${r.width.toFixed(0)}px wide, limit ${maxw}`);
    if (r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1 || r.bottom > box.bottom + 1)
      bad.push(`"${label}" sticks out of the drawing`);
  });
  return bad;
}
"""


def render_frames(svg: Path, out_dir: Path, times: tuple[float, ...] = FRAME_TIMES) -> list[Path]:
    """Screenshot the animation paused at each time, on a dark and a light page background."""
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto(svg.resolve().as_uri())
        page.evaluate("document.fonts.ready")
        for theme, color in BACKGROUNDS.items():
            page.evaluate(f"document.documentElement.style.background = '{color}'")
            for t in times:
                page.evaluate(f"(() => {{ const s = document.documentElement; s.pauseAnimations(); s.setCurrentTime({t}); }})()")
                shot = out_dir / f"gate-{theme}-{t:05.2f}s.png"
                page.screenshot(path=str(shot))
                shots.append(shot)
        browser.close()
    return shots


def find_overflow(svg: Path) -> list[str]:
    """Every label wider than its box, in the animation and (separately) in the reduced-motion still."""
    from playwright.sync_api import sync_playwright
    bad: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for mode in ("no-preference", "reduce"):
            page = browser.new_page(viewport={"width": W, "height": H}, reduced_motion=mode)
            page.goto(svg.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            if mode == "no-preference":  # every story line and stage at its fullest
                bad += page.evaluate(_OVERFLOW_JS)
            else:
                bad += [f"still: {b}" for b in page.evaluate(_OVERFLOW_JS)]
            page.close()
        browser.close()
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--svg", type=Path, default=SVG_OUT, help="where to write the SVG (default: the post's image)")
    ap.add_argument("--frames", type=Path, metavar="DIR", help="also screenshot it paused at 3 times on a dark and a light page")
    ap.add_argument("--check", action="store_true", help="report any label that overflows its box; exit 1 if any")
    args = ap.parse_args(argv)

    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(flow_svg())
    print(args.svg)
    if args.check:
        bad = find_overflow(args.svg)
        for b in bad:
            print(b)
        return 1 if bad else 0
    if args.frames:
        for shot in render_frames(args.svg, args.frames):
            print(shot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
