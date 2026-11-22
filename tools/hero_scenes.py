#!/usr/bin/env python3
"""Draw the illustrated hero card (and, for a few posts, an animated flow) of every post.

Each published post has one `Scene`: a headline and subtitle taken from the post, a
palette from _data/accents.yml (the `card-*` entries), and a drawn mini-diagram of what
the post is actually about (tools/hero_draw.py). A scene becomes

  * a 1200x630 PNG in assets/img/posts/<slug>-hero.png (the og:image / social card), and
  * for the posts where motion explains the mechanism, a self-contained animated SVG
    in assets/img/posts/<slug>-flow.svg (SMIL only, no scripts, the font inlined, and a
    still fallback for prefers-reduced-motion).

    python tools/hero_scenes.py                       # every card and flow
    python tools/hero_scenes.py --only reranker       # one scene, by slug fragment
    python tools/hero_scenes.py --html-dir /tmp/cards # card HTML only, no browser needed
    python tools/hero_scenes.py --frames /tmp/frames  # paused screenshots of each flow
    python tools/hero_scenes.py --list                # post, slug, palette, flow
    python tools/hero_scenes.py --check               # render, and fail if any label overflows its box
    python tools/hero_scenes.py --sheet /tmp/sheet    # a contact sheet page with every card and flow

A standalone page outside _posts (the witness page) has its own card in PAGE_SCENES,
named `<slug>-hero.png` like the rest and used as that page's og:image. A public repository's
link card (the find-evil one for LinkedIn Featured) lives in REPO_SCENES and is uploaded where shown.

The questionnaire post keeps its own drawing in tools/hero_diagram.py; it is listed here
so the registry covers every published post. Private projects are never named on a card:
their posts keep their titles, but the image shows the mechanism only.
"""
import argparse
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hero  # noqa: E402
import hero_diagram as hd  # noqa: E402
import hero_draw as dr  # noqa: E402
import hero_kit as kit  # noqa: E402

ROOT = hero.ROOT
POSTS_IMG = ROOT / "assets" / "img" / "posts"
IMG_URL = "/assets/img/posts"
FLOW_W, FLOW_H = 1200, 470
CAPTION_FONT = 21


@dataclass(frozen=True)
class Flow:
    cycle: float
    captions: tuple[tuple[float, float, str], ...]
    still_caption: str
    title: str
    desc: str
    alt: str            # alt text of the image in the post body
    caption: str        # the one-line italic caption under it


@dataclass(frozen=True)
class Scene:
    slug: str                       # file stem: <slug>-hero.png (and <slug>-flow.svg)
    post: str                       # glob of the post file in _posts
    palette: str                    # key in _data/accents.yml
    headline: str
    subtitle: str
    alt: str                        # image.alt for the post's front matter
    draw: Callable | None           # hero_draw function; None when drawn elsewhere
    hsize: int = 62
    flow: Flow | None = None
    external: bool = False          # drawn by tools/hero_diagram.py, not regenerated here
    page: str = ""                  # a standalone page (not a post) whose og:image this card is
    repo: str = ""                  # a public repository this card is the link preview of

    @property
    def png(self) -> Path:
        return POSTS_IMG / f"{self.slug}-hero.png"

    @property
    def svg(self) -> Path:
        return POSTS_IMG / f"{self.slug}-flow.svg"

    @property
    def hero_path(self) -> str:
        return f"{IMG_URL}/{self.slug}-hero.png"

    @property
    def flow_path(self) -> str:
        return f"{IMG_URL}/{self.slug}-flow.svg"


SCENES: tuple[Scene, ...] = (
    Scene("prefix-cache-billing-header", "*billing-header-kv-cache.md", "card-kvcache",
          "108 s turns became 7 s", "An 81-byte rotating header was quietly busting the prefix cache",
          "Warm turns of a self-hosted Claude Code setup dropped from about 100 seconds to 7 to 8: strip a rotating 81-byte billing header, then cache the 23,000-token prefix",
          dr.kv_cache),
    Scene("reranker-mined-pairs", "*three-phases-of-rag-quality.md", "card-reranker",
          "Free labels, +41% MRR@10", "A reranker fine-tuned on pairs mined from analyst close-notes",
          "Analyst close-notes that cite related cases become training pairs; the fine-tuned reranker lifts held-out MRR@10 from 0.598 to 0.846, a 41% uplift",
          dr.reranker,
          flow=Flow(
              12.0, ((.3, 4.5, "Close-notes that cite related cases become free training pairs."),
                     (4.6, 9.4, "The same base model, fine-tuned on them, ranks the right case higher."),
                     (9.5, 11.6, "+41% MRR@10 on a held-out, time-split test set.")),
              "Close-notes become training pairs; held-out MRR@10 rises from 0.598 to 0.846, a 41% uplift.",
              "From analyst close-notes to a fine-tuned reranker",
              "Analyst close-notes that cite related cases are mined into training pairs. A reranker fine-tuned on them "
              "lifts held-out MRR@10 from 0.598 to 0.846, a 41% uplift over the off-the-shelf model.",
              "Animated diagram: analyst close-notes become mined training pairs, a fine-tuned reranker is trained on them, and its held-out MRR@10 bar grows from 0.598 to 0.846, a 41% uplift",
              "_Where the training pairs came from, and what they bought: close-notes in, +41% MRR@10 out._")),
    Scene("chat-template-cache-traps", "*three-chat-template-patterns-kill-prompt-cache.md", "card-template",
          "3 traps that kill your cache", "Check a chat template in five minutes, before you download the weights",
          "Three Jinja2 chat-template patterns rewrite finished turns, so the prefix hash changes every turn and the cache misses; a check passing means a cache hit and about 13 times faster warm turns",
          dr.chat_template, hsize=60),
    Scene("eight-role-ai-soc", "*building-aisoc.md", "card-socroles",
          "One LLM, eight hats", "An AI SOC where the agents propose and humans approve",
          "An alert flows over an event bus through Sentinel, Tier 2, IR Lead and Threat Intel, all played by one local model, with a human approving every proposed action",
          dr.soc_roles,
          flow=Flow(
              dr.SOC_CYCLE, dr.SOC_CAPTIONS,
              "One alert crosses the bus through four agent roles; a human approves any containment.",
              "An alert crossing an AI SOC",
              "An alert lands on an event bus. Sentinel triages it, Tier 2 investigates, IR Lead proposes containment and "
              "Threat Intel adds attribution. A human approves or rejects; the agents never execute. Timer roles replay the audit log.",
              "Animated diagram: an alert travels along an event bus through Sentinel, Tier 2, IR Lead and Threat Intel, a human approves the proposed action, then timer roles replay the audit log",
              "_One alert through the cascade: four reactive roles, a human gate before any action, and three timer roles reading the audit log._")),
    Scene("ioc-lifecycle-human-gate", "*iocflow-agentic-ioc-lifecycle.md", "card-iocgate",
          "The LLM never has the final say", "Plain tools, an agent team, a human gate and a guard that vetoes",
          "Five deterministic layers (extract, enrich, comment, hunt, block) with an agent team on top, and three layers of authority: the agent proposes, a human authorizes, a guard vetoes",
          dr.ioc_gate, hsize=58),
    Scene("detection-copilot-draft-lint-review", "*detflow-detection-engineering-copilot.md", "card-detcopilot",
          "Draft, lint, dedupe, review", "A detection-engineering copilot that degrades instead of breaking",
          "A plain-English description is drafted into a Sigma or XQL rule, linted offline, checked against existing coverage, then reviewed for quality, false-positive risk and ATT&CK mapping",
          dr.det_copilot),
    Scene("forensic-agent-self-correction", "*find-evil-self-correcting-dfir-agent.md", "card-forensic",
          "Catch your own hallucinations", "A forensic agent reconciles its read against a deterministic extractor",
          "A forensic agent hands 50,000-line tool output to an MCP extractor and reconciles what it eyeballed against the extracted indicators, ending with one confirmed C2 and 14 unverified domains",
          dr.find_evil),
    Scene("threat-report-to-detections", "*detflow-threat-report-to-detection-package.md", "card-threatrep",
          "Threat report in, detections out", "ATT&CK techniques, Sigma, YARA and Suricata, and STIX from one call",
          "A raw threat report is mapped to ATT&CK techniques, then to Sigma, YARA and Suricata rules, then exported as STIX 2.1, an ATT&CK Navigator layer or a written brief",
          dr.threat_report),
    Scene("gather-cheap-compose-smart", "*langchain-failover-tier-split-agent.md", "card-tiersplit",
          "Gather cheap, compose smart", "A cheap local model runs the tool loop; a frontier model writes the answer",
          "A cheap local model gathers with tools in a loop, then a frontier model composes the final answer in seconds instead of minutes, behind a guard that stops it answering from zero data",
          dr.tier_split,
          flow=Flow(
              dr.TIER_CYCLE, dr.TIER_CAPTIONS,
              "A cheap model gathers with tools; a frontier model composes the answer.",
              "The gather-then-compose loop",
              "A cheap, local model drives the tool loop. When it signals it is done gathering, a guard checks a tool was "
              "actually called, and a frontier model writes the final answer in seconds instead of minutes.",
              "Animated diagram: a request enters a cheap local gatherer that loops with its tools three times, a guard checks a tool was called, then a frontier composer writes the final answer",
              "_Gather on the cheap model, compose on the strong one: the long final generation never lands on the busy local GPU._")),
    Scene("ai-soc-case-memory", "*aisoc-case-memory.md", "card-memory",
          "Giving an AI SOC a memory", "Recall, proof, interrogation and campaigns, all read from the event log",
          "An append-only event log feeds a case index, a read model that gives agents precedent, scores every verdict against ground truth, answers why from the recorded trace, and clusters campaigns",
          dr.case_memory),
    Scene("evidence-grounded-questionnaires", "*attestq-evidence-grounded-questionnaires.md", "card-questionnaire",
          hd.HEADLINE, hd.SUBTITLE,
          "A questionnaire answer is retrieved from your own evidence documents and passed through a confidence gate: strong evidence gives a cited answer, weak evidence gives an honest insufficient-evidence result",
          None, external=True),
    Scene("prove-it-gates", "*witness-prove-it-or-it-doesnt-go-in-the-report.md", "card-gates",
          "Prove it or leave it out", "Deterministic gates, not a second model: 1,083 claims, 119 attacks",
          "A claim and its bindings pass two deterministic gates: does the record say that, and what would refute it; the result is admitted, held because a tool never ran, or refused with its reason",
          dr.witness_gates,
          flow=Flow(
              dr.WIT_CYCLE, dr.WIT_CAPTIONS,
              "Three claims, two gates: admitted, refused for one changed digit, or held because a tool never ran.",
              "Three claims through two gates",
              "Claim 1 matches the record and nothing refutes it, so it is admitted. Claim 2 has one digit changed and is refused at "
              "gate 1. Claim 3 needs a tool that never ran, so it is held, never passed.",
              "Animated diagram: three claims pass through gate 1, does the record say that, and gate 2, what would refute it; one is admitted, one refused for a changed digit, one held because a tool never ran",
              "_Three claims through the same two gates: one admitted, one refused for a single changed digit, one held because the tool that could settle it never ran._")),
    Scene("fit-scores-on-a-laptop", "*jobwatch-local-fit-scores.md", "card-scoring",
          "Fit scores on a laptop", "A 29-verdict check picked the model: 28, 27 and 29 agreed",
          "Requirements are judged by a local model and the score is computed in code; three models agreed with 28, 27 and 29 of 29 expected verdicts, so the smallest and fastest stayed",
          dr.fit_scores),
    Scene("watcher-that-never-applies", "*jobwatch-source-rules.md", "card-rules",
          "A watcher that never applies", "Honest requests, robots.txt as a hard rule, and a human who submits",
          "Public board feeds pass through rules that live in code, an honest User-Agent, robots.txt and no LinkedIn or Indeed pages, into a ranked digest that you review and submit yourself",
          dr.source_rules),
    Scene("one-command-video-rebuild", "*slidecast-narrated-videos-from-a-script.md", "card-video",
          "One command rebuilds the video", "HTML slides, recorded clips and a script in, a narrated MP4 out",
          "HTML slides, recorded clips and a narration script go through one build command that screenshots, speaks and stitches a narrated MP4, failing the build when a frame clips a button",
          dr.slidecast),
    Scene("mask-the-numbers", "*taxtrace-local-redaction.md", "card-redact",
          "Show the shape, not the numbers", "Digits become #, unfamiliar words become *: only masked text reaches an AI",
          "Tax documents are read locally, then masked so digits become # and unfamiliar words become *; a cloud model only ever sees the masked text",
          dr.tax_redaction, hsize=60,
          flow=Flow(
              dr.TAX_CYCLE, dr.TAX_CAPTIONS,
              "Read locally, masked, then shown: digits become #, unfamiliar words become *.",
              "How a document is masked before an AI sees it",
              "Documents are read on your own machine by plain code and local OCR. Every digit becomes # and every word outside "
              "a tax vocabulary becomes *, so a cloud model only ever sees the masked text.",
              "Animated diagram: a PDF is read locally, a line of text is masked so digits become # and unfamiliar words become *, and only the masked version goes to a cloud model",
              "_The mask in one pass: what stays on your machine, and the masked text a cloud model is allowed to see._")),
)

# Standalone pages outside _posts that share the posts' card style: kept apart from SCENES so
# the one-scene-per-post checks and the contact sheet stay about posts.
PAGE_SCENES: tuple[Scene, ...] = (
    Scene("witness-page", "", "card-witness-page",
          "Change one digit", "A plain-Python comparison re-reads the tool output and refuses the claim",
          "A finding says a process was spawned by PID 1233; the captured tool output says 1332; a plain comparison, with no language model in the gate, refuses the finding",
          dr.witness_page, page="witness/index.html"),
)

# Link cards of the public GitHub repositories (LinkedIn Featured, a README): a repo has no page of its own
# here, so the PNG is simply uploaded where it is shown. Every word comes from that repo's README.
REPO_SCENES: tuple[Scene, ...] = (
    Scene("find-evil-repo", "", "card-findevil-repo",
          "Stop agents inventing indicators", "An IOC-lifecycle MCP layer for a DFIR agent: text in, dict out",
          "A forensic agent's tool output goes through extract_iocs and the agent's own findings are reconciled against the extracted set, so an indicator that is not in it is flagged; enrich, assess, hunts, a dry-run block plan and STIX follow",
          dr.find_evil_repo, hsize=60, repo="github.com/vinayvobbili/find-evil"),
)

EXTRA_SCENES = PAGE_SCENES + REPO_SCENES   # every card that is not a post's hero

BY_SLUG = {s.slug: s for s in SCENES + EXTRA_SCENES}


# --- the card -----------------------------------------------------------------

def _rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def palette_of(scene: Scene) -> dict[str, str]:
    return hero.load_palette(scene.palette)


def card_html(scene: Scene) -> str:
    """The static 1200x630 card: gradient background, headline, subtitle, diagram, footer."""
    p = palette_of(scene)
    e = html.escape
    body = kit.defs() + scene.draw(kit.Ctx())
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
{kit.font_faces()}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {hero.WIDTH}px; height: {hero.HEIGHT}px; }}
body {{
  font-family: 'Space Grotesk', sans-serif; color: #fff; position: relative; overflow: hidden;
  background:
    radial-gradient(circle at 6% 104%, {_rgba(p["glowa"], .60)} 0, transparent 46%),
    radial-gradient(circle at 96% 100%, {_rgba(p["glowb"], .40)} 0, transparent 40%),
    radial-gradient(circle at 78% 40%, {_rgba(p["glowc"], .42)} 0, transparent 46%),
    linear-gradient(125deg, {p["cardfrom"]} 0%, {p["cardvia"]} 48%, {p["cardto"]} 100%);
}}
.dots {{ position: absolute; inset: 0; opacity: .5;
  background-image: radial-gradient(rgba(255,255,255,.22) 1.5px, transparent 1.6px); background-size: 28px 28px;
  -webkit-mask-image: linear-gradient(180deg, #000 0, transparent 55%); mask-image: linear-gradient(180deg, #000 0, transparent 55%); }}
.headline {{ position: absolute; left: 50px; top: 38px; font-weight: 700; font-size: {scene.hsize}px; line-height: 1.05;
  letter-spacing: -0.015em; white-space: nowrap; }}
.headline span {{ background: linear-gradient(90deg, #fff 0%, {p["headto"]} 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.sub {{ position: absolute; left: 52px; top: 118px; font-size: 27px; line-height: 1.25; color: #f5f3ff; white-space: nowrap; }}
svg.diagram {{ position: absolute; left: 50px; top: 196px; }}
.site {{ position: absolute; right: 50px; bottom: 20px; font-weight: 700; font-size: 23px; color: #fff; opacity: .95;
  text-shadow: 0 1px 8px rgba(0,0,0,.35); }}
</style></head><body>
<div class="dots"></div>
<div class="headline"><span>{e(scene.headline)}</span></div>
<div class="sub">{e(scene.subtitle)}</div>
<svg class="diagram" width="{hd.DIAGRAM_W}" height="{hd.DIAGRAM_H}" viewBox="0 0 {hd.DIAGRAM_W} {hd.DIAGRAM_H}" xmlns="http://www.w3.org/2000/svg">
{body}
</svg>
<div class="site">{hero.SITE}</div>
</body></html>
"""


# --- the animated flow --------------------------------------------------------

def flow_svg(scene: Scene) -> str:
    """The animated SVG for the post body, with a still version for reduced motion."""
    flow = scene.flow
    p = palette_of(scene)
    motion = scene.draw(kit.Ctx(flow.cycle))
    still = scene.draw(kit.Ctx())
    ctx = kit.Ctx(flow.cycle)
    captions = ""
    for a, b, text in flow.captions:
        captions += ctx.show(kit.T(600, 424, text, CAPTION_FONT, "#fff", anchor="middle", maxw=1000), (a, b), fade=.3)
    pill = kit.rect(100, 392, 1000, 48, 24, "#1e1b4b", 'fill-opacity=".38"')
    still_caption = kit.T(600, 424, flow.still_caption, CAPTION_FONT, "#fff", anchor="middle", maxw=1000)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FLOW_W} {FLOW_H}" width="{FLOW_W}" height="{FLOW_H}" role="img" aria-labelledby="t d">
<title id="t">{html.escape(flow.title)}</title>
<desc id="d">{html.escape(flow.desc)}</desc>
<style>{kit.font_faces()}
.still {{ display: none; }}
@media (prefers-reduced-motion: reduce) {{ .motion {{ display: none; }} .still {{ display: inline; }} }}
</style>
{kit.defs()}
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["cardfrom"]}"/><stop offset=".5" stop-color="{p["cardvia"]}"/><stop offset="1" stop-color="{p["cardto"]}"/></linearGradient>
<radialGradient id="b1" cx=".1" cy="1" r=".6"><stop offset="0" stop-color="{p["glowa"]}" stop-opacity=".55"/><stop offset="1" stop-color="{p["glowa"]}" stop-opacity="0"/></radialGradient>
<radialGradient id="b2" cx=".92" cy=".05" r=".5"><stop offset="0" stop-color="{p["glowb"]}" stop-opacity=".4"/><stop offset="1" stop-color="{p["glowb"]}" stop-opacity="0"/></radialGradient>
<rect width="{FLOW_W}" height="{FLOW_H}" rx="28" fill="url(#bg)"/>
<rect width="{FLOW_W}" height="{FLOW_H}" rx="28" fill="url(#b1)"/>
<rect width="{FLOW_W}" height="{FLOW_H}" rx="28" fill="url(#b2)"/>
{pill}
<g class="motion"><g transform="translate(50,40)">{motion}</g>{captions}</g>
<g class="still"><g transform="translate(50,40)">{still}</g>{still_caption}</g>
</svg>
"""


# --- frames, outputs ----------------------------------------------------------

def flow_frame_times(flow: Flow) -> list[float]:
    """A time late in each caption, when that stage's result is lit, to check every stage by eye."""
    return [round(a + .7 * (b - a), 2) for a, b, _ in flow.captions]


def render_frames(scene: Scene, out_dir: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": FLOW_W, "height": FLOW_H})
        page.goto(scene.svg.resolve().as_uri())
        page.evaluate("document.fonts.ready")
        for t in flow_frame_times(scene.flow):
            page.evaluate(f"(() => {{ const s = document.documentElement; s.pauseAnimations(); s.setCurrentTime({t}); }})()")
            shot = out_dir / f"{scene.slug}-flow-{t:05.2f}s.png"
            page.screenshot(path=str(shot))
            shots.append(shot)
        browser.close()
    return shots


def render_cards(scenes: list[Scene]) -> list[Path]:
    """Render every card to its PNG with one browser."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright not found. `pip install playwright && playwright install chromium`")
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": hero.WIDTH, "height": hero.HEIGHT})
        for s in scenes:
            page.set_content(card_html(s), wait_until="load")
            page.evaluate("document.fonts.ready")
            s.png.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(s.png), clip={"x": 0, "y": 0, "width": hero.WIDTH, "height": hero.HEIGHT})
            out.append(s.png)
        browser.close()
    return out


# Runs in the page: every <text> against its own data-maxw and against the drawing's edges.
_OVERFLOW_JS = """
(edge) => {
  const bad = [];
  const svg = document.querySelector('svg.diagram') || document.documentElement;
  const box = svg.getBoundingClientRect();
  document.querySelectorAll('svg text').forEach(t => {
    const r = t.getBoundingClientRect();
    if (!r.width) return;                      // not rendered (the still group)
    const label = (t.textContent || '').slice(0, 40);
    const maxw = parseFloat(t.dataset.maxw || '0');
    if (maxw && r.width > maxw + 1.5) bad.push(`"${label}" is ${r.width.toFixed(0)}px wide, limit ${maxw}`);
    if (r.left < box.left - 1 || r.right > box.right + 1 || r.top < box.top - 1 || r.bottom > box.bottom + 1)
      bad.push(`"${label}" sticks out of the drawing`);
  });
  for (const sel of ['.headline span', '.sub', '.site']) {
    const el = document.querySelector(sel);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (r.left < 0 || r.right > edge) bad.push(`${sel} runs outside the card (${r.left.toFixed(0)}..${r.right.toFixed(0)})`);
  }
  return bad;
}
"""


def find_overflow(scenes: list[Scene], include_flows: bool = True) -> dict[str, list[str]]:
    """Render each card (and flow) and list every label that is wider than its box or off the drawing."""
    from playwright.sync_api import sync_playwright
    problems: dict[str, list[str]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": hero.WIDTH, "height": hero.HEIGHT})
        for s in scenes:
            page.set_content(card_html(s), wait_until="load")
            page.evaluate("document.fonts.ready")
            bad = page.evaluate(_OVERFLOW_JS, hero.WIDTH - 40)
            if include_flows and s.flow:
                flow_page = browser.new_page(viewport={"width": FLOW_W, "height": FLOW_H})
                flow_page.goto(s.svg.resolve().as_uri())
                flow_page.evaluate("document.fonts.ready")
                bad += [f"flow: {b}" for b in flow_page.evaluate(_OVERFLOW_JS, FLOW_W)]
                flow_page.close()
            if bad:
                problems[s.slug] = bad
        browser.close()
    return problems


def post_title(scene: Scene) -> str:
    """The title line of the scene's post front matter (YAML double-quote escapes undone)."""
    post = next((ROOT / "_posts").glob(scene.post))
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', post.read_text(), re.M)
    return m.group(1).replace('\\"', '"') if m else post.stem


def contact_sheet(out_dir: Path) -> Path:
    """One page with every hero beside its post title and every flow playing; images are copied next to it."""
    import shutil
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for s in SCENES:
        png = s.png
        shutil.copy(png, out_dir / png.name)
        flow = ""
        if s.flow or s.external:
            svg = s.svg if s.flow else hd.SVG_OUT
            shutil.copy(svg, out_dir / svg.name)
            flow = (f'<figure class="flow"><img src="{svg.name}" alt="" loading="lazy">'
                    f'<figcaption>Animated flow, plays on a loop</figcaption></figure>')
        p = palette_of(s)
        cards.append(
            f'<article class="card" style="--a:{p["cardfrom"]};--b:{p["cardvia"]};--c:{p["cardto"]}">'
            f'<div class="meta"><h2>{html.escape(post_title(s))}</h2>'
            f'<p><code>{html.escape(s.post.lstrip("*"))}</code><span class="tag">{html.escape(s.palette)}</span></p></div>'
            f'<img class="hero" src="{png.name}" alt="{html.escape(s.alt)}" loading="lazy">{flow}</article>')
    page = f"""<!doctype html>
<html lang="en" data-theme="system" data-width="standard"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blog hero contact sheet</title><style>
:root {{ --bg:#f6f4fb; --ink:#1e1b4b; --muted:#5b5780; --card:#fff; --line:#e4e0f2; --max:1280px; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#12101f; --ink:#f1efff; --muted:#a9a4cf; --card:#1c1930; --line:#2f2b4d; }} }}
:root[data-theme="dark"] {{ --bg:#12101f; --ink:#f1efff; --muted:#a9a4cf; --card:#1c1930; --line:#2f2b4d; }}
:root[data-width="wide"] {{ --max:1720px; }} :root[data-width="full"] {{ --max:none; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:'Space Grotesk',system-ui,sans-serif; color:var(--ink); background:
  radial-gradient(900px 500px at 8% -5%, rgba(124,58,237,.18), transparent 60%),
  radial-gradient(800px 500px at 100% 0%, rgba(6,182,212,.16), transparent 60%), var(--bg); }}
header {{ max-width:var(--max); margin:0 auto; padding:32px 24px 8px; display:flex; flex-wrap:wrap; gap:16px; align-items:end; justify-content:space-between; }}
h1 {{ margin:0; font-size:clamp(28px,4vw,44px); letter-spacing:-.02em; background:linear-gradient(90deg,#4f46e5,#db2777,#f59e0b);
  -webkit-background-clip:text; background-clip:text; color:transparent; }}
header p {{ margin:6px 0 0; color:var(--muted); }}
.controls {{ display:flex; gap:10px; flex-wrap:wrap; }}
.seg {{ display:inline-flex; background:var(--card); border:1px solid var(--line); border-radius:999px; padding:3px; }}
.seg button {{ border:0; background:none; color:var(--muted); font:inherit; font-size:13px; padding:6px 12px; border-radius:999px; cursor:pointer; }}
.seg button[aria-pressed="true"] {{ background:linear-gradient(135deg,#4f46e5,#a855f7); color:#fff; }}
main {{ max-width:var(--max); margin:0 auto; padding:16px 24px 64px; display:grid; gap:28px; grid-template-columns:repeat(auto-fit,minmax(min(100%,560px),1fr)); }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:22px; padding:18px; position:relative; overflow:hidden;
  box-shadow:0 14px 40px -18px rgba(30,27,75,.35); animation:rise .6s both; transition:transform .25s, box-shadow .25s; }}
.card::before {{ content:""; position:absolute; inset:0 0 auto 0; height:6px; background:linear-gradient(90deg,var(--a),var(--b),var(--c)); }}
.card:hover {{ transform:translateY(-4px); box-shadow:0 22px 50px -18px rgba(30,27,75,.5); }}
.meta h2 {{ margin:6px 0 4px; font-size:19px; line-height:1.25; }}
.meta p {{ margin:0 0 12px; color:var(--muted); font-size:13px; display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
code {{ font-size:12px; }} .tag {{ padding:2px 10px; border-radius:999px; color:#fff; background:linear-gradient(135deg,var(--a),var(--c)); font-size:12px; }}
img {{ width:100%; height:auto; display:block; border-radius:14px; }}
.flow {{ margin:14px 0 0; }} .flow figcaption {{ color:var(--muted); font-size:12px; margin-top:6px; }}
@keyframes rise {{ from {{ opacity:0; transform:translateY(14px); }} to {{ opacity:1; transform:none; }} }}
@media (prefers-reduced-motion: reduce) {{ .card {{ animation:none; transition:none; }} }}
</style></head><body>
<header><div><h1>Blog hero cards</h1><p>{len(SCENES)} posts, {sum(1 for s in SCENES if s.flow or s.external)} animated flows. Not committed: a preview.</p></div>
<div class="controls"><div class="seg" data-key="theme"><button data-v="system">System</button><button data-v="light">Light</button><button data-v="dark">Dark</button></div>
<div class="seg" data-key="width"><button data-v="standard">Standard</button><button data-v="wide">Wide</button><button data-v="full">Full</button></div></div></header>
<main>{"".join(cards)}</main>
<script>
const root = document.documentElement;
for (const seg of document.querySelectorAll('.seg')) {{
  const key = seg.dataset.key;
  const set = v => {{ root.dataset[key] = v; try {{ localStorage.setItem('hs-' + key, v); }} catch (e) {{}}
    seg.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === v)); }};
  let saved = null; try {{ saved = localStorage.getItem('hs-' + key); }} catch (e) {{}}
  set(saved || root.dataset[key]);
  seg.addEventListener('click', e => e.target.dataset.v && set(e.target.dataset.v));
}}
</script></body></html>
"""
    sheet = out_dir / "contact-sheet.html"
    sheet.write_text(page)
    return sheet


def pick(only: str | None) -> list[Scene]:
    scenes = [s for s in SCENES + EXTRA_SCENES if not s.external]
    if only:
        scenes = [s for s in scenes if only in s.slug]
        if not scenes:
            raise SystemExit(f"no scene matches {only!r}; known: {', '.join(s.slug for s in SCENES + EXTRA_SCENES)}")
    return scenes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", help="draw only scenes whose slug contains this text")
    ap.add_argument("--html-dir", type=Path, help="write each card's HTML here instead of rendering PNGs (no browser)")
    ap.add_argument("--frames", type=Path, metavar="DIR", help="also screenshot each flow paused at a few times into DIR")
    ap.add_argument("--list", action="store_true", help="list the scenes and exit")
    ap.add_argument("--sheet", type=Path, metavar="DIR",
                    help="write contact-sheet.html (every hero beside its post title, flows playing) and copies of the images into DIR")
    ap.add_argument("--check", action="store_true", help="render and report any label that overflows its box; exit 1 if any")
    args = ap.parse_args(argv)

    if args.list:
        for s in SCENES + EXTRA_SCENES:
            print(f"{s.slug:40} {s.palette:20} {'flow' if (s.flow or s.external) else '':5} {s.post or s.page or s.repo}")
        return 0
    if args.sheet:
        print(contact_sheet(args.sheet))
        return 0
    scenes = pick(args.only)
    if args.check:
        problems = find_overflow(scenes)
        for slug, bad in problems.items():
            for b in bad:
                print(f"{slug}: {b}")
        return 1 if problems else 0
    if args.html_dir:
        args.html_dir.mkdir(parents=True, exist_ok=True)
        for s in scenes:
            f = args.html_dir / f"{s.slug}.html"
            f.write_text(card_html(s))
            print(f)
        return 0
    for s in scenes:
        if s.flow:
            s.svg.write_text(flow_svg(s))
            print(s.svg)
    for png in render_cards(scenes):
        print(png)
    if args.frames:
        for s in scenes:
            if s.flow:
                for shot in render_frames(s, args.frames):
                    print(shot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
