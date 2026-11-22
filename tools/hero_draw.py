"""The drawn mini-diagrams for the hero cards, one function per post.

Each function takes a `Ctx` and returns SVG markup for a 1100x330 canvas. With a static
Ctx it draws the finished, fully-lit picture (the PNG card). With an animated Ctx it
adds SMIL: highlights, travelling dots and reveals on a looping timeline (the flow SVGs).
Only numbers a post states appear in a diagram, and private projects are never named:
their diagrams show the mechanism only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hero_kit import (AMBER_LIGHT, GREEN, GREEN_LIGHT, INK, MUTED, RED, RED_LIGHT, T, arrow, bar, chip, diamond,  # noqa: E402
                      diamond_path, g, header_panel, icon, lines, node, panel, pill, rect, tile)

W = "#fff"
SPAN_END = 1e9  # "until the end of the loop" (Ctx clamps it)


def badge(x, y, w, h, text, grad="green", size=20) -> str:
    return (f'<g filter="url(#shadow)">{rect(x, y, w, h, h / 2, g(grad))}</g>'
            + T(x + w / 2, y + h / 2 + size * .36, text, size, "#fff", anchor="middle", maxw=w - 20))


# --------------------------------------------------------------------------- kv cache

def kv_cache(ctx) -> str:
    o = [panel(0, 10, 270, 310, 20), T(20, 42, "Every request", 18, maxw=230)]
    o += [rect(18, 58, 234, 78, 14, g("indigo")), T(34, 88, "System + tools", 18, W, maxw=200),
          T(34, 108, "about 23,000 tokens,", 13.5, W, 400, maxw=200), T(34, 125, "same every turn", 13.5, W, 400, maxw=200)]
    o += [rect(18, 148, 234, 62, 14, g("red")), T(34, 174, "Billing header", 17, W, maxw=170),
          T(34, 195, "81 bytes, rotates each turn", 13.5, W, 400, maxw=190), icon("loop", 218, 158, 24, "#fff", 2.4)]
    o += [rect(18, 222, 234, 56, 14, g("slate")), T(34, 248, "New message", 17, W, maxw=200),
          T(34, 267, "a few hundred tokens", 13.5, W, 400, maxw=200)]
    o += [T(135, 306, "cache key = hash of the prefix", 13.5, MUTED, 400, "middle", maxw=240)]
    o += [arrow("M270 85 L324 85"), arrow("M270 245 L324 245")]
    o += [node(330, 30, 240, 110, "orange", "scissors", "1. Strip the header", "prefix becomes byte-stable"),
          node(330, 190, 240, 110, "green", "db", "2. Cache the prefix", "restore KV, prefill the rest")]
    o += [panel(620, 10, 480, 310, 20), T(642, 44, "Warm-turn wall-clock", 18, maxw=430)]
    rows = (("Stock vllm-mlx", 100, "red", "about 100 s"), ("Header stripped only", 70, "amber", "about 70 s"),
            ("Stripped + KV-cache patch", 7.5, "green", "7-8 s"))
    for i, (label, secs, grad, val) in enumerate(rows):
        y = 84 + i * 72
        w = max(secs * 3.0, 22)
        o += [T(642, y, label, 15, INK, 400, maxw=420), bar(642, y + 10, w, 30, grad),
              T(642 + w + 12, y + 32, val, 18, INK, maxw=150)]
    o += [badge(800, 262, 280, 44, "13-15× faster warm turns", "green", 18)]
    return "".join(o)


# --------------------------------------------------------------------------- reranker

def reranker(ctx) -> str:
    o = []
    t = ctx.show
    o += [t(tile(0, 10, 380, 84, "cyan", "doc", "Analyst close-notes", "cite related cases by ID"), (0, SPAN_END), lo=1)]
    o += [arrow("M190 94 L190 119"), ctx.dot("M190 94 L190 119", 1.0, 2.0, "#22d3ee")]
    o += [t(tile(0, 123, 380, 84, "indigo", "link", "Mined pairs", "hard negatives, 33% dupes cut"), (2.0, SPAN_END), lo=.3)]
    o += [arrow("M190 207 L190 232"), ctx.dot("M190 207 L190 232", 3.0, 4.0, "#a78bfa")]
    o += [t(tile(0, 236, 380, 84, "green", "gauge", "Fine-tuned reranker", "same base model, no new labels"),
            (4.0, SPAN_END), lo=.3)]
    o += [arrow("M380 278 C 415 278, 415 250, 450 250"), ctx.dot("M380 278 C 415 278, 415 250, 450 250", 4.8, 5.8, "#34d399")]
    o += [panel(450, 10, 650, 310, 20), T(472, 44, "MRR@10 on a held-out, time-split test set", 18, maxw=600)]
    o += [T(472, 84, "Off-the-shelf bge-reranker-v2-m3", 15, INK, 400, maxw=560),
          ctx.grow(472, 96, 299, 36, "slate", 5.8, 7.0, SPAN_END),
          t(T(757, 121, "0.598", 20, W, anchor="end", maxw=100), (7.0, SPAN_END)),
          T(472, 168, "Fine-tuned on mined pairs", 15, INK, 400, maxw=560),
          ctx.grow(472, 180, 423, 36, "green", 7.4, 9.0, SPAN_END),
          t(T(881, 205, "0.846", 20, W, anchor="end", maxw=100), (9.0, SPAN_END)),
          t(badge(915, 176, 150, 44, "+41%", "green", 24), (9.4, SPAN_END)),
          t(T(472, 252, "The first right case lands near rank 1.7 before, 1.18 after.", 15, MUTED, 400, maxw=600), (9.8, SPAN_END)),
          chip(472, 268, 250, 30, "0 explicit labels collected", "#fef3c7", "#d97706", "#92400e")]
    return "".join(o)


# --------------------------------------------------------------------------- chat template

def chat_template(ctx) -> str:
    o = [tile(0, 10, 410, 84, "red", "tag", "last_query_index", "the marker moves to the newest turn"),
         tile(0, 123, 410, 84, "orange", "loop", "loop.last rewrites", "finished turns get re-rendered"),
         tile(0, 236, 410, 84, "pink", "mask", "Think-suffix injection", "think blocks added or stripped"),
         arrow("M410 52 C 440 52, 440 120, 470 120"), arrow("M410 165 L466 165"), arrow("M410 278 C 440 278, 440 210, 470 210")]
    o += [panel(470, 10, 630, 310, 20), T(492, 44, "Same prefix, two turns", 18, maxw=560)]

    def seg(x, y, w, label, grad, extra=""):
        return rect(x, y, w, 40, 10, g(grad), extra) + T(x + w / 2, y + 26, label, 14.5, W, anchor="middle", maxw=w - 8)

    o += [T(492, 84, "Turn N", 14, MUTED, 400),
          seg(492, 92, 110, "system", "indigo"), seg(608, 92, 130, "tools", "violet"),
          seg(744, 92, 100, "user 1", "slate"), seg(850, 92, 84, "marker", "amber")]
    o += [T(492, 156, "Turn N+1", 14, MUTED, 400),
          seg(492, 164, 110, "system", "indigo"), seg(608, 164, 130, "tools", "violet"),
          seg(744, 164, 100, "user 1", "red", 'stroke="#fff" stroke-width="2.5"'),
          seg(850, 164, 90, "reply", "slate"), seg(946, 164, 100, "user 2", "slate"),
          chip(744, 210, 130, 24, "bytes changed", "#fee2e2", RED, "#991b1b", 13)]
    o += [rect(490, 248, 296, 62, 16, "#fee2e2", f'stroke="{RED}" stroke-width="1.5"'),
          icon("x", 502, 268, 26, RED, 2.2), T(538, 275, "Prefix hash differs", 17, "#991b1b", maxw=240),
          T(538, 296, "cache MISS, full prefill", 13.5, "#991b1b", 400, maxw=240)]
    o += [rect(802, 248, 280, 62, 16, "#dcfce7", f'stroke="{GREEN}" stroke-width="1.5"'),
          icon("check", 814, 268, 26, GREEN, 2.2), T(850, 275, "Check passes: cache HIT", 17, "#166534", maxw=225),
          T(850, 296, "about 13× faster warm turns", 13.5, "#166534", 400, maxw=225)]
    return "".join(o)


# --------------------------------------------------------------------------- AI SOC roles (flow)

SOC_CYCLE = 15.5
_TOP = ((260, "Sentinel", "triage", "cyan", "bolt"), (450, "Tier 2", "investigate", "indigo", "search"),
        (640, "IR Lead", "plan + severity", "pink", "shield"), (830, "Threat Intel", "actor + ATT&CK", "violet", "network"))
_TIMED = ((260, "SOC Manager", "every 8 hours", "teal", "clock"), (450, "Detection Eng.", "weekday mornings", "orange", "code"),
          (640, "Threat Hunter", "twice a day", "amber", "eye"))


def _role(x, y, name, sub, grad, ico) -> str:
    return (panel(x, y, 180, 64, 16) + f'<circle cx="{x + 28}" cy="{y + 32}" r="19" fill="{g(grad)}"/>' + icon(ico, x + 17, y + 21, 22)
            + T(x + 54, y + 29, name, 15, INK, maxw=120) + T(x + 54, y + 48, sub, 13, MUTED, 400, maxw=120))


def soc_roles(ctx) -> str:
    o = [pill(0, 60, 200, "Alert feed", h=44, ico="warn", ico_color="#d97706", size=16),
         arrow("M200 82 C 232 82, 232 170, 262 170"),
         node(0, 150, 200, 160, "blue", "sparkle", "1 local LLM", "eight hats, one model"),
         rect(250, 150, 850, 40, 20, "#fff", 'fill-opacity=".16" stroke="#fff" stroke-opacity=".55" stroke-width="2"'),
         T(1088, 176, "event bus", 15, W, anchor="end", maxw=100)]
    for x, *_ in _TOP:
        o.append(arrow(f"M{x + 90} 84 L{x + 90} 148", head=False, op=.6))
    for x, *_ in _TIMED:
        o.append(arrow(f"M{x + 90} 192 L{x + 90} 232", head=False, op=.6))
    for x, name, sub, grad, ico in _TOP:
        o.append(_role(x, 20, name, sub, grad, ico))
    for x, name, sub, grad, ico in _TIMED:
        o.append(_role(x, 234, name, sub, grad, ico))
    o.append(node(860, 212, 240, 108, "amber", "user", "Human approves", "agents propose, humans execute"))
    o.append(arrow("M985 192 L985 208", head=False, op=.6))
    # one pass of an alert through the cascade
    A = [("M200 82 C 232 82, 232 170, 262 170 L350 170 L350 90", .6, 2.2),
         ("M350 90 L350 170 L540 170 L540 90", 3.4, 5.0),
         ("M540 90 L540 170 L730 170 L730 90", 6.2, 7.8),
         ("M730 90 L730 170 L920 170 L920 90", 9.4, 10.8),
         ("M730 90 L730 170 L985 170 L985 210", 9.4, 11.0)]
    for d, a, b in A:
        o.append(ctx.dot(d, a, b, "#fde047", 6))
    ring = "#fde047"
    for (x, *_), (a, b) in zip(_TOP, ((2.0, 3.6), (4.8, 6.4), (7.6, 9.4), (10.8, 12.4))):
        o.append(ctx.ring(x - 3, 17, 186, 70, 18, ring, (a, b)))
    o.append(ctx.ring(857, 209, 246, 114, 24, ring, (11.0, 13.0)))
    for (x, *_) in _TIMED:
        o.append(ctx.dot(f"M{x + 90} 170 L{x + 90} 232", 12.6, 13.6, "#5eead4", 5))
        o.append(ctx.ring(x - 3, 231, 186, 70, 18, "#5eead4", (13.2, 15.0)))
    o.append(ctx.ring(-3, 57, 206, 50, 25, ring, (.3, 1.8)))
    return "".join(o)


SOC_CAPTIONS = ((.3, 2.9, "An alert lands on the event bus."), (3.1, 5.6, "Sentinel triages it, then Tier 2 investigates."),
                (5.8, 9.4, "IR Lead drafts a plan and proposes containment."),
                (9.6, 13.0, "A human approves or rejects. The agents never execute."),
                (13.1, 15.2, "Timer roles replay the audit log."))


# --------------------------------------------------------------------------- IOC lifecycle

def ioc_gate(ctx) -> str:
    steps = (("L1  Extract", "IPs, domains, hashes", "cyan", "search"), ("L2  Enrich", "worst-wins verdict", "indigo", "db"),
             ("L3  Comment", "structured assessment", "violet", "doc"), ("L4  Hunt", "ready-to-run queries", "teal", "filter"),
             ("L5  Block", "dry run by default", "orange", "lock"))
    o = []
    for i, (title, sub, grad, ico) in enumerate(steps):
        x = i * 227
        o.append(node(x, 4, 190, 104, grad, ico, title, sub, tsize=19))
        if i < 4:
            o.append(arrow(f"M{x + 192} 56 L{x + 224} 56"))
    o.append(pill(0, 122, 1100, "Layer 6: a supervisor routes a small agent team that calls each layer as a plain tool",
                  h=40, size=17, ico="layers", ico_color="#7e22ce"))
    cards = ((0, "indigo", "1  Agent proposes", "bolt", ["Dry run first: full audit,", "zero changes."]),
             (390, "amber", "2  Human authorizes", "user", ["Default is deny: an unattended", "run blocks nothing."]),
             (780, "red", "3  Guard vetoes", "shield", ["Allowlist refuses public resolvers,", "even if a report says malicious."]))
    for x, grad, title, ico, body in cards:
        o.append(header_panel(x, 190, 320, 132, grad, title, ico, size=18))
        o.append(lines(x + 18, 262, body, 15, 22, maxw=290))
    o.append(arrow("M322 256 L386 256"))
    o.append(arrow("M712 256 L776 256"))
    o.append(chip(944, 290, 100, 24, "8.8.8.8 ✕", "#fee2e2", RED, "#991b1b", 13))
    return "".join(o)


# --------------------------------------------------------------------------- detection copilot

def det_copilot(ctx) -> str:
    o = [panel(0, 85, 220, 160, 20), icon("pencil", 18, 99, 26, "#059669", 2.2), T(54, 119, "Plain English", 17, maxw=150)]
    o += [lines(18, 155, ["powershell with an", "encoded command", "spawned from a", "Word macro"], 14.5, 21, MUTED, 400, maxw=190)]
    o += [arrow("M222 165 L262 165")]
    o += [node(266, 105, 150, 120, "green", "sparkle", "Draft", "Sigma or XQL")]
    o += [arrow("M418 150 C 436 150, 436 72, 460 72"), arrow("M418 180 C 436 180, 436 258, 460 258")]
    o += [node(464, 14, 180, 110, "teal", "check", "Lint", "offline, no model"),
          node(464, 206, 180, 110, "cyan", "compare", "Find overlaps", "dedupe vs your catalog")]
    o += [arrow("M646 70 C 668 70, 676 120, 690 140"), arrow("M646 262 C 668 262, 676 210, 690 190")]
    o += [diamond(750, 165, 62, "lime", "gauge")]
    o += [T(750, 252, "Review", 18, W, anchor="middle", maxw=120)]
    o += [arrow("M814 165 L848 165")]
    o += [header_panel(852, 40, 248, 250, "green", "Review verdict", "shield", size=18)]
    for i, row in enumerate(("Quality score", "False-positive risk", "ATT&CK mapping", "Verdict")):
        y = 104 + i * 44
        o += [icon("check", 872, y - 17, 22, GREEN, 2.4), T(902, y, row, 16, INK, maxw=180)]
    return "".join(o)


# --------------------------------------------------------------------------- find-evil

def find_evil(ctx) -> str:
    o = [panel(0, 30, 230, 200, 20), icon("doc", 18, 46, 26, "#b91c1c", 2.2), T(52, 66, "Tool output", 17, maxw=160)]
    for i in range(9):
        wd = (150, 190, 120, 170, 100, 180, 140, 160, 90)[i]
        o.append(rect(18, 90 + i * 14, wd, 7, 3.5, "#e2e8f0"))
    o += [T(115, 252, "50,000 lines", 18, W, anchor="middle", maxw=200), T(115, 272, "to read without guessing", 13.5, W, 400, "middle", maxw=220)]
    o += [arrow("M232 130 L290 130")]
    o += [header_panel(294, 20, 300, 230, "indigo", "MCP server", "box", size=19)]
    for i, (name, sub) in enumerate((("extract_iocs", "re-fang, TLD check, dedup"), ("suggest_hunts", "CQL, XQL, Sigma"),
                                      ("propose_blocks", "dry run only"))):
        y = 96 + i * 50
        o += [rect(310, y - 22, 268, 42, 10, "#eef2ff"), T(324, y - 3, name, 15.5, INK, maxw=240),
              T(324, y + 14, sub, 12.5, MUTED, 400, maxw=240)]
    o += [pill(294, 262, 300, "0 shell verbs exposed", h=40, size=15, ico="lock", ico_color="#b91c1c")]
    o += [arrow("M596 130 L650 130")]
    o += [header_panel(654, 4, 446, 322, "red", "Reconcile: eyeballed vs extracted", "compare", size=17)]
    rows = (("185.220.101.50", "185.220.101.5", "last octet transposed"), ("powershell.exe: malware", "a LOLBin", "benign binary, not the malware"),
            ("no external C2", "C2 in the command line", "proxy hid it from the table"))
    for i, (bad, good, why) in enumerate(rows):
        y = 94 + i * 64
        o += [T(674, y, bad, 15.5, "#991b1b", 400, maxw=190, deco="line-through"), icon("check", 862, y - 17, 22, GREEN, 2.4),
              T(890, y, good, 15.5, "#166534", maxw=200), T(674, y + 20, why, 13, MUTED, 400, maxw=400)]
    o += [badge(674, 272, 400, 40, "1 confirmed C2, 14 unverified", "green", 17)]
    return "".join(o)


# --------------------------------------------------------------------------- threat report

def threat_report(ctx) -> str:
    o = [panel(0, 50, 230, 230, 20), icon("doc", 18, 66, 28, "#b45309", 2.2), T(56, 88, "Threat report", 18, maxw=160),
         chip(18, 106, 130, 26, "CVE advisory", "#fef3c7", "#d97706", "#92400e")]
    for i in range(6):
        o.append(rect(18, 150 + i * 18, (190, 160, 180, 120, 170, 90)[i], 8, 4, "#e2e8f0"))
    o += [arrow("M232 165 L274 165")]
    o += [header_panel(278, 30, 330, 270, "orange", "ATT&CK techniques", "network", size=18)]
    for i, (tid, name, conf, col) in enumerate((("T1190", "Exploit public-facing app", "High", GREEN), ("T1505.003", "Web shell", "High", GREEN),
                                                ("T1059.001", "PowerShell", "Medium", "#d97706"))):
        y = 112 + i * 62
        o += [rect(294, y - 28, 298, 52, 12, "#fff7ed"), T(308, y - 6, tid, 15, "#9a3412", maxw=100),
              T(308, y + 14, name, 14, MUTED, 400, maxw=190), chip(512, y - 16, 70, 26, conf, "#fff", col, col, 13)]
    o += [T(443, 292, "ordered by kill chain", 13, MUTED, 400, anchor="middle", maxw=300)]
    o += [arrow("M610 165 L654 165")]
    for i, (name, sub, grad) in enumerate((("Sigma", "linted in place", "green"), ("YARA", "for payloads", "indigo"),
                                           ("Suricata", "for network C2", "cyan"))):
        o.append(tile(658, 30 + i * 96, 220, 80, grad, "code", name, sub, tsize=18, ssize=13))
    o += [arrow("M880 165 L918 165")]
    for i, (name, sub, grad, ico) in enumerate((("STIX 2.1", "to your TIP", "violet", "box"), ("Navigator", "layer file", "teal", "layers"),
                                                ("Brief", "for the reader", "amber", "doc"))):
        o.append(tile(922, 30 + i * 96, 178, 80, grad, ico, name, sub, tsize=17, ssize=13))
    return "".join(o)


# --------------------------------------------------------------------------- tier split (flow)

TIER_CYCLE = 15.0


def tier_split(ctx) -> str:
    o = [pill(0, 96, 170, "Request", h=40, ico="chat", ico_color="#0369a1", size=16), arrow("M172 116 L214 116"),
         node(220, 60, 190, 110, "sky", "cpu", "Gatherer", "cheap, local model"),
         node(220, 214, 190, 94, "slate", "box", "Tools", "errors as text", tsize=19),
         arrow("M262 172 L262 210"), T(270, 196, "tool call", 13, W, 400, maxw=60),
         arrow("M368 212 L368 174"), T(378, 196, "result", 13, W, 400, maxw=60),
         arrow("M412 115 L516 115"), T(464, 102, "done gathering", 13, W, 400, "middle", maxw=104),
         node(520, 60, 200, 110, "amber", "sparkle", "Composer", "frontier model"),
         arrow("M722 115 L796 115")]
    o += [ctx.show(header_panel(800, 20, 300, 190, "green", "Final answer", "check", size=19), (12.4, SPAN_END), lo=.3)]
    o += [ctx.show(lines(820, 116, ["Written in a couple of", "seconds, not minutes"], 18, 26, maxw=270)
                   + T(820, 190, "same tools, same data", 14, MUTED, 400, maxw=270), (12.4, SPAN_END), lo=.3)]
    o += [panel(440, 236, 660, 84, 18), f'<circle cx="480" cy="278" r="25" fill="{g("amber")}"/>', icon("shield", 466, 264, 28, "#451a03", 2.2),
          T(520, 266, "Structural guard", 17, INK, maxw=520),
          T(520, 289, "Done signalled before any tool call? Nudge once, so the", 14.5, MUTED, 400, maxw=560),
          T(520, 308, "composer never writes an answer from zero data.", 14.5, MUTED, 400, maxw=560)]
    # timeline
    o += [ctx.ring(-3, 93, 176, 46, 23, "#fde047", (.2, 1.6)), ctx.dot("M172 116 L214 116", .4, 1.5, "#fde047"),
          ctx.ring(217, 57, 196, 116, 25, "#fde047", (1.5, 9.2), width=4)]
    for a in (1.8, 4.4, 7.0):
        o += [ctx.dot("M262 172 L262 210", a, a + .8, "#fde047", 5), ctx.ring(217, 211, 196, 100, 22, "#fde047", (a + .6, a + 1.4)),
              ctx.dot("M368 212 L368 174", a + 1.2, a + 2.0, "#5eead4", 5)]
    o += [ctx.ring(437, 233, 666, 90, 22, "#fde047", (9.2, 10.8)), ctx.dot("M412 115 L516 115", 9.4, 10.6, "#fde047"),
          ctx.ring(517, 57, 206, 116, 25, "#fde047", (10.6, 12.6)), ctx.dot("M722 115 L796 115", 12.0, 13.0, "#34d399", 7)]
    return "".join(o)


TIER_CAPTIONS = ((.3, 4.3, "The cheap, local model drives the loop: pick a tool, read the result."),
                 (4.5, 9.0, "Every turn is short, so a busy local GPU copes."),
                 (9.2, 12.2, "Done gathering. A guard checks that a tool was actually called."),
                 (12.4, 14.6, "A frontier model writes the answer: seconds, not minutes."))


# --------------------------------------------------------------------------- case memory

def case_memory(ctx) -> str:
    o = [header_panel(0, 30, 250, 270, "indigo", "Event log", "db", size=19)]
    for i, (a, b) in enumerate((("Every verdict", "with its evidence"), ("Every approval", "who decided, and why"),
                                ("The audit stream", "replayable, append-only"))):
        y = 108 + i * 62
        o += [rect(16, y - 26, 218, 52, 12, "#eef2ff"), T(30, y - 4, a, 15.5, INK, maxw=190), T(30, y + 15, b, 13, MUTED, 400, maxw=190)]
    o += [arrow("M252 165 L300 165"), node(304, 108, 170, 114, "plum", "layers", "Case index", "a read model", tsize=19)]
    cards = ((520, 10, "indigo", "Recall", "search", ["Similar prior cases", "as precedent, flag-gated"]),
             (810, 10, "green", "Proof", "gauge", ["Every verdict scored", "against ground truth"]),
             (520, 174, "amber", "Interrogation", "ask", ["Why did it do that?", "Answered from the trace"]),
             (810, 174, "pink", "Campaigns", "network", ["Clusters of cases on", "shared infrastructure"]))
    for x, y, grad, title, ico, body in cards:
        o.append(header_panel(x, y, 270, 146, grad, title, ico, size=19))
        o.append(lines(x + 18, y + 76, body, 15.5, 25, maxw=240))
    o += [arrow("M476 150 C 500 150, 500 84, 516 84"), arrow("M476 180 C 500 180, 500 246, 516 246")]
    return "".join(o)


# --------------------------------------------------------------------------- witness (flow)

WIT_CYCLE = 18.0
_CLAIMS = ((["rundll32.exe (3720) was", "spawned by PID 1332"], "bound: parent PID = 1332"),
           (["rundll32.exe (3720) was", "spawned by PID 1233"], "bound: parent PID = 1233"),
           (["Code injection was found", "on the clean host"], "needs a malfind scan"))


def witness_gates(ctx) -> str:
    o = [header_panel(0, 20, 270, 290, "indigo", "Claim + bindings", "doc", size=18)]
    for i, (text, bound) in enumerate(_CLAIMS):
        b = i * 6
        block = lines(18, 108, text, 17, 26, maxw=240) + chip(18, 176, 234, 30, bound, "#e0f2fe", "#0284c7", "#075985", 13.5)
        block += T(18, 244, "record + field + value," if i < 2 else "the tool that settles it", 14, MUTED, 400, maxw=240)
        block += T(18, 264, "re-read by plain Python" if i < 2 else "never ran", 14, MUTED, 400, maxw=240)
        o.append(ctx.show(block, (b + .1, b + 5.6)) if ctx.animated else (block if i == 0 else ""))
    o += [arrow("M272 175 L336 175"), arrow("M464 175 L576 175")]
    o += [T(400, 82, "Gate 1", 18, W, anchor="middle", maxw=120), T(400, 101, "does the record say that?", 13.5, W, 400, "middle", maxw=200),
          diamond(400, 175, 62, "indigo", "link")]
    o += [T(640, 82, "Gate 2", 18, W, anchor="middle", maxw=120), T(640, 101, "what would refute it?", 13.5, W, 400, "middle", maxw=190),
          diamond(640, 175, 62, "teal", "search")]
    outs = (("green", "Admitted", "check", "into the ledger and the report", 6, 96, 0), ("amber", "Held", "warn", "the tool never ran: not a pass", 118, 96, 2),
            ("red", "Refused", "x", "logged with the reason it died", 230, 96, 1))
    for grad, title, ico, body, y, h, sc in outs:
        m = header_panel(780, y, 320, h, grad, title, ico, size=19) + T(798, y + 76, body, 15, INK, 400, maxw=290)
        o.append(ctx.dim(m, (sc * 6 + 3.4, sc * 6 + 5.6), lo=.4) if ctx.animated else m)
    paths = ("M702 175 C 740 175, 740 54, 774 54", "M702 175 C 740 175, 740 166, 774 166", "M400 237 L400 278 L774 278")
    for p, col in zip(paths, ("green", "amber", "red")):
        o.append(arrow(p, col, 4, op=.9))
    # scenarios: claim 1 admitted, claim 2 refused at gate 1, claim 3 held at gate 2
    for i in range(3):
        b = i * 6
        o.append(ctx.dot("M272 175 L336 175", b + .4, b + 1.3, "#fde047"))
        g1 = GREEN_LIGHT if i != 1 else RED_LIGHT
        o.append(ctx.ring_path(diamond_path(400, 175, 62), g1, (b + 1.3, b + 3.0)))
        if i == 1:
            o.append(ctx.dot("M400 237 L400 278 L774 278", b + 1.8, b + 3.2, RED_LIGHT, 7))
        else:
            o.append(ctx.dot("M464 175 L576 175", b + 1.8, b + 2.7, "#fde047"))
            o.append(ctx.ring_path(diamond_path(640, 175, 62), GREEN_LIGHT if i == 0 else AMBER_LIGHT, (b + 2.7, b + 4.4)))
            o.append(ctx.dot(paths[0 if i == 0 else 1], b + 3.0, b + 3.8, GREEN_LIGHT if i == 0 else AMBER_LIGHT, 7))
    return "".join(o)


WIT_CAPTIONS = ((.2, 5.7, "Claim 1: the record says exactly that, and nothing refutes it. Admitted."),
                (6.2, 11.7, "Claim 2: one digit changed. The record disagrees. Refused at gate 1."),
                (12.2, 17.5, "Claim 3: the tool that could settle it never ran. Held, never passed."))


# --------------------------------------------------------------------------- jobwatch scoring

def fit_scores(ctx) -> str:
    o = [tile(0, 10, 380, 84, "cyan", "list", "Posting to requirements", "must-have and nice-to-have", tsize=18),
         tile(0, 123, 380, 84, "indigo", "cpu", "A local model judges each", "met, partly or missing, with quotes", tsize=18),
         tile(0, 236, 380, 84, "green", "gauge", "The score is computed in code", "from the verdicts, so it can be checked", tsize=18),
         arrow("M190 94 L190 119"), arrow("M190 207 L190 232")]
    o += [panel(430, 10, 670, 310, 20), T(452, 44, "29 expected verdicts, three models", 18, maxw=600)]
    rows = (("Qwen3.5-9B, 4-bit", 28, "27 s a call, 7.5 GB", "green"), ("Qwen3.5-9B, 6-bit", 27, "36 s a call, 9.7 GB", "slate"),
            ("Gemma 4 12B, 4-bit", 29, "42 s a call, 9.2 GB", "slate"))
    for i, (name, n, sub, grad) in enumerate(rows):
        y = 78 + i * 68
        o += [T(452, y, name, 15.5, INK, maxw=300), T(1080, y, sub, 13.5, MUTED, 400, "end", maxw=260),
              bar(452, y + 10, n / 29 * 520, 30, grad), T(452 + n / 29 * 520 + 14, y + 33, f"{n} / 29", 19, INK, maxw=100)]
    o += [chip(630, 60, 210, 26, "stayed: fastest and smallest", "#dcfce7", GREEN, "#166534", 13)]
    o += [T(452, 292, "A spread of one verdict sits inside the noise.", 15.5, MUTED, 400, maxw=620)]
    return "".join(o)


# --------------------------------------------------------------------------- jobwatch rules

def source_rules(ctx) -> str:
    o = [node(0, 105, 250, 120, "teal", "db", "Public board feeds", "what companies already publish"),
         arrow("M252 165 L304 165")]
    o += [header_panel(308, 10, 480, 310, "indigo", "Rules in code, not in settings", "lock", size=18)]
    rules = (("Honest User-Agent", "one string, defined once"), ("robots.txt can't be read? No.", "when it can't tell, it doesn't read"),
             ("No LinkedIn or Indeed pages", "their job pages are never opened"), ("Never applies for you", "you review and submit"))
    for i, (a, b) in enumerate(rules):
        y = 104 + i * 55
        o += [rect(324, y - 28, 448, 49, 12, "#eef2ff"), icon("lock", 336, y - 18, 22, "#4338ca", 2.2),
              T(370, y - 4, a, 16, INK, maxw=390), T(370, y + 13, b, 13, MUTED, 400, maxw=390)]
    o += [arrow("M790 165 L842 165")]
    o += [node(846, 10, 254, 136, "sky", "list", "Ranked digest", "fit scores, tracked stages"),
          node(846, 184, 254, 136, "orange", "user", "You review and submit", "every application, by hand", tsize=18)]
    o += [arrow("M973 148 L973 180", head=True)]
    o += [badge(0, 244, 250, 34, "21 source types", "indigo", 15), badge(0, 288, 250, 34, "0 applications submitted", "green", 15)]
    return "".join(o)


# --------------------------------------------------------------------------- slidecast

def slidecast(ctx) -> str:
    o = [tile(0, 10, 290, 84, "amber", "code", "HTML slides", "any HTML you like", tsize=19),
         tile(0, 123, 290, 84, "indigo", "film", "Recorded clips", "a cursor that glides", tsize=19),
         tile(0, 236, 290, 84, "pink", "mic", "Narration script", "spoken by a pluggable voice", tsize=19),
         arrow("M290 52 C 335 52, 335 135, 364 135"), arrow("M290 165 L364 165"), arrow("M290 278 C 335 278, 335 195, 364 195")]
    o += [node(370, 100, 210, 130, "violet", "play", "One command", "screenshot, speak, stitch", tsize=21),
          arrow("M582 165 L644 165")]
    o += [rect(648, 10, 452, 250, 24, g("ink"), 'stroke="#fff" stroke-opacity=".5" stroke-width="2"'),
          '<g filter="url(#shadow)"><circle cx="874" cy="112" r="50" fill="#fff"/></g>', '<path d="M858 86 L858 138 L902 112 Z" fill="#7c3aed"/>',
          rect(676, 188, 396, 8, 4, "#fff", 'fill-opacity=".25"'), rect(676, 188, 190, 8, 4, g("pink"))]
    for i in range(34):
        hgt = (6, 14, 22, 10, 18, 26, 12, 20)[i % 8]
        o.append(rect(676 + i * 12, 232 - hgt / 2 - 4, 6, hgt, 3, "#fff", 'fill-opacity=".55"'))
    o += [T(676, 176, "narrated MP4", 14, W, 400, maxw=200)]
    o += [chip(648, 276, 220, 40, "clipped frame fails the build", "#fee2e2", RED, "#991b1b", 13.5),
          chip(882, 276, 218, 40, "rebuild after any change", "#dcfce7", GREEN, "#166534", 13.5)]
    return "".join(o)


# --------------------------------------------------------------------------- taxtrace (flow)

TAX_CYCLE = 13.0


def tax_redaction(ctx) -> str:
    o = [node(0, 10, 230, 100, "teal", "folder", "Your PDFs", "W-2, 1099, K-1"), arrow("M232 60 L286 60"),
         node(290, 10, 230, 100, "green", "laptop", "Read locally", "plain code + local OCR"), arrow("M522 60 L576 60"),
         node(580, 10, 230, 100, "amber", "mask", "Mask", "digits to #, words to *"), arrow("M812 60 L866 60"),
         node(870, 10, 230, 100, "slate", "cloud", "Cloud model", "sees masked text only")]
    raw = lines(18, 222, ["Total depreciation  $9,892.00", "Jordan Quillfeather, 4417 Brambleworth Ct"], 17, 32, INK, maxw=490)
    masked = lines(598, 222, ["Total depreciation  $#,###.##", "****** ************, #### ************ Ct"], 17, 32, INK, maxw=490)
    o += [header_panel(0, 150, 520, 170, "teal", "On your machine", "laptop", size=18), ctx.show(raw, (2.8, SPAN_END)),
          ctx.show(chip(18, 276, 440, 30, "every value keeps its file, page and exact text", "#dcfce7", GREEN, "#166534", 13.5), (8.8, SPAN_END)),
          arrow("M524 235 L576 235"),
          header_panel(580, 150, 520, 170, "amber", "What a model sees", "eye", tcolor="#451a03", size=18), ctx.show(masked, (5.8, SPAN_END))]
    for (x, w), (a, b) in zip(((0, 230), (290, 230), (580, 230), (870, 230)), ((.3, 2.0), (2.2, 4.0), (4.6, 6.2), (7.4, 12.6))):
        o.append(ctx.ring(x - 3, 7, w + 6, 106, 25, "#fde047", (a, b)))
    for d, a, b in (("M232 60 L286 60", 1.2, 2.3), ("M522 60 L576 60", 3.8, 4.9), ("M812 60 L866 60", 6.4, 7.5)):
        o.append(ctx.dot(d, a, b, "#fde047"))
    o.append(ctx.dot("M524 235 L576 235", 5.4, 6.3, "#fde047", 5))
    return "".join(o)


TAX_CAPTIONS = ((.3, 3.0, "Documents are read on your machine by plain code and local OCR, not a model."),
                (3.2, 6.4, "Every digit becomes #, and every unfamiliar word becomes *."),
                (6.6, 12.4, "A cloud model only ever sees the masked text."))
