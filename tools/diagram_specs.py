"""One `Spec` per post diagram that used to be a plain mermaid block (see tools/diagram_flows.py).

Each spec keeps the nodes, wording and logic of the original block: `labels` lists that wording, and the test
checks every piece is drawn. A line of a label may be wrapped onto two lines here; nothing is added or renamed
except where a spec's `notes` says so. Private project names never appear: where the original block named one,
the spec uses a neutral word and says so in `notes`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diagram_flows import Edge as E, Group, Node as N, Scenario, Spec  # noqa: E402

SPECS: list[Spec] = []


def add(spec: Spec) -> Spec:
    SPECS.append(spec)
    return spec


def S(start: str, *steps: tuple[str, str]) -> Scenario:
    return Scenario(start, steps)


# 1. billing header and the prefix KV cache: "The setup" -------------------------------------------------------

def billing_setup() -> Spec:
    cli = N("cli", ("Claude Code CLI",), "sky", "laptop").at(60, 62)
    router = N("router", ("claude-code-router",), "indigo", "network").at(640, 62)
    shim = N("shim", ("Shim", "(1) strips", "x-anthropic-billing-header", "(2) buffers tool-call streams"),
             "blue", "filter", bold=(1, 2)).at(cx=router.cx, y=250)
    se = N("se", ("SimpleEngine", "(3) system-prefix KV cache", "HIT: skip prefill", "MISS: prefill + snapshot"),
           "orange", "db", bold=(1,)).at(60, 475)
    vllm = N("vllm", ("vllm-mlx server",), "teal", "cpu").at(cx=shim.cx, cy=se.cy)
    return Spec(
        slug="billing-header-kv-cache-setup-flow", post="billing-header-kv-cache", section="The setup",
        title="The self-hosted Claude Code setup and where each fix sits",
        desc=("Claude Code CLI sends a request through claude-code-router to a shim. The shim strips the "
              "x-anthropic-billing-header and buffers tool-call streams, so the system prefix is byte-stable for the "
              "vllm-mlx server. Its SimpleEngine keeps a system-prefix KV cache: a hit skips prefill, a miss prefills "
              "and takes a snapshot. Tokens stream back to the CLI."),
        alt=("Animated flowchart: Claude Code CLI sends /v1/messages through claude-code-router to a shim that strips the "
             "billing header and buffers tool-call streams, then a byte-stable system prefix reaches the vllm-mlx server "
             "and its SimpleEngine system-prefix KV cache, which skips prefill on a hit and prefills and snapshots on a "
             "miss, and tokens stream back to the CLI"),
        caption="_Three fixes on one path: the shim strips the rotating header and buffers tool calls, and the engine keeps the system-prefix cache._",
        h=670, palette="ember",
        nodes=[cli, router, shim, vllm, se],
        edges=[
            E("e-req", "cli.r", "router.l", label=("/v1/messages", "system + tools + msgs", "+ rotating cch=...")),
            E("e-shim", "router.b", "shim.t"),
            E("e-vllm", "shim.b", "vllm.t", label=("byte-stable", "system prefix"), lpos=(520, 455)),
            E("e-eng", "vllm.l", "se.r"),
            E("e-out", "se.t:-55", "cli.b", color="green", label=("stream tokens",), lpos=(330, 340)),
        ],
        scenarios=[S("cli", ("e-req", "router"), ("e-shim", "shim"), ("e-vllm", "vllm"), ("e-eng", "se"), ("e-out", "cli"))],
        labels=("Claude Code CLI", "claude-code-router", "Shim", "(1) strips x-anthropic-billing-header",
                "(2) buffers tool-call streams", "vllm-mlx server", "SimpleEngine", "(3) system-prefix KV cache",
                "HIT: skip prefill", "MISS: prefill + snapshot", "/v1/messages", "system + tools + msgs",
                "+ rotating cch=...", "byte-stable", "system prefix", "stream tokens"),
    )


add(billing_setup())


# 2. three phases of RAG quality: "The setup: embedder + reranker" -----------------------------------------------

def rag_setup() -> Spec:
    q = N("q", ("User query",), "sky", "ask").at(60, 60)
    emb = N("emb", ("Embedder", "Qwen3-Embedding-8B", "4-bit DWQ"), "cyan", "layers").at(q.right + 130, 60)
    top50 = N("top50", ("Top-50 by", "cosine similarity"), "teal", "list").at(emb.right + 130, 60)
    rr = N("rr", ("Reranker", "bge-reranker-v2-m3", "fine-tuned"), "blue", "compare", bold=(2,)).at(cx=top50.cx, y=300)
    top5 = N("top5", ("Top-5 ranked", "by joint scoring"), "indigo", "filter").at(cy=rr.cy, x=rr.x - 130 - 270)
    llm = N("llm", ("LLM grounds", "answer"), "green", "sparkle").at(cy=rr.cy, x=top5.x - 130 - 250)
    return Spec(
        slug="three-phases-of-rag-quality-setup-flow", post="three-phases-of-rag-quality",
        section="The setup: embedder + reranker",
        title="Embedder and reranker in one retrieval pipeline",
        desc=("A user query goes to the Qwen3-Embedding-8B embedder (4-bit DWQ), which gives the top 50 by cosine "
              "similarity. The fine-tuned bge-reranker-v2-m3 reranks them into the top 5 by joint scoring, and the LLM "
              "grounds its answer on those."),
        alt=("Animated flowchart: a user query goes to an embedder, the top 50 by cosine similarity go to a fine-tuned "
             "reranker, the top 5 ranked by joint scoring go to an LLM that grounds the answer"),
        caption="_Two stages before the LLM: the embedder keeps the top 50 by cosine similarity, and the fine-tuned reranker narrows them to the top 5._",
        h=480, palette="ocean",
        nodes=[q, emb, top50, rr, top5, llm],
        edges=[
            E("e-qe", "q.r", "emb.l"), E("e-et", "emb.r", "top50.l"),
            E("e-tr", "top50.b", "rr.t"), E("e-rt", "rr.l", "top5.r"), E("e-tl", "top5.l", "llm.r"),
        ],
        scenarios=[S("q", ("e-qe", "emb"), ("e-et", "top50"), ("e-tr", "rr"), ("e-rt", "top5"), ("e-tl", "llm"))],
        labels=("User query", "Embedder", "Qwen3-Embedding-8B", "4-bit DWQ", "Top-50 by", "cosine similarity",
                "Reranker", "bge-reranker-v2-m3", "fine-tuned", "Top-5 ranked", "by joint scoring", "LLM grounds", "answer"),
    )


add(rag_setup())


# 3. chat-template patterns: "Why prefix caching is fragile" ---------------------------------------------------

def prefix_cache() -> Spec:
    t1 = N("t1", ("Turn 1", "system + tools + user₁"), "sky", "chat").at(40, 60)
    kv1 = N("kv1", ("KV state", "after system+tools"), "indigo", "layers").at(660, 60)
    cache = N("cache", ("Cache", "hash(system+tools) → KV"), "blue", kind="db").at(cx=kv1.cx, y=300)
    t2 = N("t2", ("Turn 2", "system + tools + user₁", "+ asst₁ + user₂"), "sky", "chat").at(40, cy=cache.cy)
    kv2 = N("kv2", ("Skip system+tools prefill", "only prefill suffix"), "orange", "bolt").at(cx=cache.cx, y=cache.bottom + 110)
    return Spec(
        slug="three-chat-template-patterns-prefix-cache-flow", post="three-chat-template-patterns-kill-prompt-cache",
        section="Why prefix caching is so fragile",
        title="How a prefix cache is filled on turn 1 and hit on turn 2",
        desc=("Turn 1 prefills all tokens of system, tools and the first user message into a KV state after system and "
              "tools. That state is snapshotted into a cache keyed by a hash of system and tools. Turn 2 hashes system and "
              "tools, looks the cache up, and on a hit restores the snapshot, so it skips the system and tools prefill and "
              "only prefills the suffix."),
        alt=("Animated flowchart: turn 1 prefills all tokens into a KV state after system and tools, which is snapshotted "
             "into a cache keyed by a hash of system and tools; turn 2 hashes system and tools and looks it up, and a hit "
             "restores the snapshot so only the suffix is prefilled"),
        caption="_The cache is keyed on the system and tools prefix: turn 2 restores the snapshot and prefills only what is new._",
        h=640, palette="plum",
        nodes=[t1, kv1, cache, t2, kv2],
        edges=[
            E("e-prefill", "t1.r", "kv1.l", label=("prefill all tokens",)),
            E("e-snap", "kv1.b", "cache.t", label=("snapshot",)),
            E("e-lookup", "t2.r", "cache.l", label=("hash system+tools", "look up")),
            E("e-hit", "cache.b", "kv2.t", color="green", label=("HIT: restore snapshot",)),
        ],
        scenarios=[S("t1", ("e-prefill", "kv1"), ("e-snap", "cache"), ("", "t2"), ("e-lookup", "cache"), ("e-hit", "kv2"))],
        labels=("Turn 1", "system + tools + user₁", "KV state", "after system+tools", "Cache", "hash(system+tools) → KV",
                "Turn 2", "system + tools + user₁ + asst₁ + user₂", "Skip system+tools prefill", "only prefill suffix",
                "prefill all tokens", "snapshot", "hash system+tools", "look up", "HIT: restore snapshot"),
    )


add(prefix_cache())


# 7. detflow copilot: "What it looks like" ----------------------------------------------------------------------

def copilot_pipeline() -> Spec:
    nl = N("nl", ("plain English",), "sky", "pencil", kind="pill").at(30, 70)
    rule = N("rule", ("Sigma / XQL rule",), "indigo", "code").at(nl.right + 130, 70)
    lint = N("lint", ("schema +", "best-practice", "findings"), "teal", "audit", nt=3).at(rule.right + 100, 70)
    ov = N("ov", ("catalog dedup",), "cyan", "layers").at(cx=rule.cx, y=300)
    rev = N("rev", ("review",), "violet", "eye", kind="hex").at(cx=lint.cx, cy=ov.cy)
    v = N("v", (), "green", "check", kind="pill", chips=("quality", "FP risk", "ATT&CK", "verdict"), w=640).at(120, 520)
    return Spec(
        slug="detection-copilot-draft-lint-review-flow", post="detflow-detection-engineering-copilot",
        section="What it looks like",
        title="From plain English to a reviewed detection rule",
        desc=("Plain English is drafted into a Sigma or XQL rule. The rule is linted for schema and best-practice "
              "findings and checked with find_overlaps for catalog dedup. Both feed a review step that ends in a "
              "verdict covering quality, false-positive risk and ATT&CK."),
        alt=("Animated flowchart: plain English is drafted into a Sigma or XQL rule, which is linted for schema and "
             "best-practice findings and checked for catalog overlaps; both go to a review that gives quality, "
             "false-positive risk, ATT&CK and a verdict"),
        caption="_One rule, two checks: lint and catalog dedup both feed the review, which returns the verdict._",
        h=660, palette="indigo",
        nodes=[nl, rule, lint, ov, rev, v],
        edges=[
            E("e-draft", "nl.r", "rule.l", label=("draft",)),
            E("e-lint", "rule.r", "lint.l", label=("lint",)),
            E("e-overlap", "rule.b", "ov.t", label=("find_overlaps",)),
            E("e-lr", "lint.b", "rev.t"),
            E("e-or", "ov.r", "rev.l"),
            E("e-rv", "rev.b", "v.r", route="vh", color="green"),
        ],
        scenarios=[S("nl", ("e-draft", "rule"), ("e-lint e-overlap", "lint ov"), ("e-lr e-or", "rev"), ("e-rv", "v"))],
        labels=("plain English", "draft", "Sigma / XQL rule", "lint", "schema + best-practice findings",
                "find_overlaps", "catalog dedup", "review", "quality", "FP risk", "ATT&CK", "verdict"),
    )


add(copilot_pipeline())


# 9. detflow: threat report to detection package ------------------------------------------------------------------

def report_to_package() -> Spec:
    r = N("r", ("threat report",), "sky", "doc", kind="pill").at(30, 70)
    a = N("a", ("ATT&CK techniques", "+ confidence"), "violet", "shield").at(r.right + 170, 70)
    rules = N("rules", ("Sigma /", "YARA /", "Suricata"), "teal", "code", nt=3).at(a.right + 100, 70)
    lint = N("lint", ("linted in place",), "green", "check").at(cx=rules.cx, y=320)
    exp = N("exp", ("exports",), "orange", "box", kind="hex").at(cx=a.cx, cy=lint.cy)
    stix = N("stix", ("STIX 2.1",), "blue", "network", kind="pill").at(cx=250, y=560)
    nav = N("nav", ("Navigator layer",), "indigo", "layers", kind="pill").at(cx=650, y=560)
    md = N("md", ("Markdown brief",), "pink", "doc", kind="pill").at(cx=1030, y=560)
    return Spec(
        slug="threat-report-to-detection-package-flow", post="detflow-threat-report-to-detection-package",
        section="What it looks like",
        title="From a threat report to a detection package",
        desc=("A threat report is analyzed into ATT&CK techniques with confidence. Those become Sigma, YARA and Suricata "
              "rules, and lint_sigma lints them in place. The techniques and the linted rules feed the exports: STIX 2.1, "
              "a Navigator layer and a Markdown brief."),
        alt=("Animated flowchart: a threat report is analyzed into ATT&CK techniques with confidence, which become Sigma, "
             "YARA and Suricata rules that lint_sigma lints in place; the techniques and the linted rules feed the exports, "
             "STIX 2.1, a Navigator layer and a Markdown brief"),
        caption="_The report becomes techniques and rules, and the exports fan out to STIX, a Navigator layer and a brief._",
        h=700, palette="teal",
        nodes=[r, a, rules, lint, exp, stix, nav, md],
        edges=[
            E("e-analyze", "r.r", "a.l", label=("analyze",)),
            E("e-rules", "a.r", "rules.l"),
            E("e-lint", "rules.b", "lint.t", label=("lint_sigma",)),
            E("e-aexp", "a.b", "exp.t"),
            E("e-lexp", "lint.l", "exp.r"),
            E("e-stix", "exp.b", "stix.t", route="vhv", color="green"),
            E("e-nav", "exp.b", "nav.t", route="vhv", color="green"),
            E("e-md", "exp.b", "md.t", route="vhv", color="green"),
        ],
        scenarios=[S("r", ("e-analyze", "a"), ("e-rules e-aexp", "rules exp"), ("e-lint", "lint"), ("e-lexp", "exp"),
                     ("e-stix e-nav e-md", "stix nav md"))],
        labels=("threat report", "analyze", "ATT&CK techniques + confidence", "Sigma / YARA / Suricata", "lint_sigma",
                "linted in place", "exports", "STIX 2.1", "Navigator layer", "Markdown brief"),
    )


add(report_to_package())


# 10. langchain failover: tier split ------------------------------------------------------------------------------------

def tier_split() -> Spec:
    q = N("q", ("user request",), "sky", "ask", layout="top").at(40, 100)
    g = N("g", ("gatherer", "cheap/local"), "teal", "search", layout="top").at(q.right + 110, 100)
    c = N("c", ("composer", "frontier"), "violet", "sparkle", layout="top").at(g.right + 290, 100)
    a = N("a", ("final answer",), "green", "check", layout="top").at(c.right + 110, 100)
    t = N("t", ("tools",), "orange", "bolt", layout="top").at(cx=g.cx, y=340)
    return Spec(
        slug="langchain-failover-tier-split-flow", post="langchain-failover-tier-split-agent",
        section="Tier-split",
        title="A cheap gatherer loops with tools, then a frontier composer answers",
        desc=("A user request goes to the gatherer, a cheap local model. The gatherer makes tool calls to the tools and "
              "gets results back. When it is done gathering, the composer, a frontier model, writes the final answer."),
        alt=("Animated flowchart: a user request goes to a cheap, local gatherer that calls tools and gets results back; "
             "when it is done gathering, a frontier composer writes the final answer"),
        caption="_The gatherer loops with its tools on the cheap tier; once it is done gathering, the frontier composer writes the answer._",
        h=520, palette="forest",
        nodes=[q, g, c, a, t],
        edges=[
            E("e-req", "q.r", "g.l"),
            E("e-call", "g.b:-40", "t.t:-40", color="sky", label=("tool call",), lpos=(g.cx - 120, 300)),
            E("e-result", "t.t:40", "g.b:40", color="sky", label=("result",), lpos=(g.cx + 105, 300)),
            E("e-done", "g.r", "c.l", color="green", label=("done gathering",)),
            E("e-ans", "c.r", "a.l"),
        ],
        scenarios=[S("q", ("e-req", "g"), ("e-call", "t"), ("e-result", "g"), ("e-done", "c"), ("e-ans", "a"))],
        labels=("user request", "gatherer", "cheap/local", "tools", "tool call", "result", "done gathering", "composer",
                "frontier", "final answer"),
    )


add(tier_split())


# 11. case memory: the read model --------------------------------------------------------------------------------------

def case_memory_model() -> Spec:
    v = N("v", ("verdicts.sqlite", "role, reason,", "evidence, confidence"), "indigo", "db", w=300).at(60, 135)
    h = N("h", ("hitl.sqlite", "who approved, why"), "violet", "user", w=300).at(60, v.bottom + 22)
    au = N("au", ("soc.audit stream", "every event, replayable"), "orange", "wave", w=300).at(60, h.bottom + 22)
    log = Group("log", "Event log", 30, 40, 360, au.bottom + 28 - 40, icon="folder", note="(already existed in v1)")
    idx = N("idx", ("Case index", "case_memory.sqlite"), "plum", "db", layout="top").at(cx=560, cy=log.y + log.h / 2)
    rs = []
    for i, (name, sub, grad, ico) in enumerate((
            ("recall_similar", "precedent for an agent", "teal", "search"),
            ("compute_trends", "accuracy and cost rollup", "blue", "gauge"),
            ("get_case_reasoning", "full trace for one case", "green", "list"),
            ("find_campaign_clusters", "cross-incident infra", "pink", "network"))):
        rs.append(N(f"r{i + 1}", (name, sub), grad, ico, w=400).at(770, 40 + i * 140))
    edges = [E("e-log", "log.r", "idx.l")]
    edges += [E(f"e-r{i + 1}", "idx.r", f"r{i + 1}.l", route="hvh", mid=690) for i in range(4)]
    return Spec(
        slug="ai-soc-case-memory-read-model-flow", post="aisoc-case-memory", section="The unlock: memory is a read model, not a new database",
        title="Case memory: an event log indexed into four read tools",
        desc=("The event log already existed in v1: verdicts, who approved and why, and the audit stream of every "
              "event, replayable. It is indexed into a case memory database, which serves four tools: recall_similar, "
              "compute_trends, get_case_reasoning and find_campaign_clusters."),
        alt=("Animated flowchart: an event log of verdicts, human approvals and a replayable audit stream is indexed "
             "into a case index database, which serves four tools: recall_similar, compute_trends, get_case_reasoning "
             "and find_campaign_clusters"),
        caption="_One index over the existing event log, four ways to read it: precedent, trends, one case's reasoning, and campaign clusters._",
        h=int(max(log.y + log.h, rs[-1].bottom) + 40), palette="rose",
        nodes=[v, h, au, idx, *rs], groups=[log], edges=edges,
        scenarios=[S("log v h au", ("e-log", "idx"), ("e-r1", "r1"), ("e-r2", "r2"), ("e-r3", "r3"), ("e-r4", "r4"))],
        labels=("Event log (already existed in v1)", "verdicts.sqlite", "role, reason, evidence, confidence", "hitl.sqlite",
                "who approved, why", "soc.audit stream", "every event, replayable", "Case index", "case_memory.sqlite",
                "recall_similar", "precedent for an agent", "compute_trends", "accuracy and cost rollup",
                "get_case_reasoning", "full trace for one case", "find_campaign_clusters", "cross-incident infra"),
    )


add(case_memory_model())


# 12. witness: the two gates -------------------------------------------------------------------------------------------

def two_gates() -> Spec:
    e = N("e", ("memory", "image"), "sky", "folder", kind="pill").at(40, 50)
    c = N("c", ("read-only", "collector"), "teal", "lock").at(e.right + 60, 50)
    s = N("s", ("hash-chained", "records"), "indigo", kind="db").at(c.right + 60, 50)
    f = N("f", ("claim", "+ bindings"), "violet", "link").at(s.right + 60, 50)
    g1 = N("g1", ("gate 1", "does the record", "say that?"), "plum", "search", kind="gate").at(cx=f.cx, y=250)
    g2 = N("g2", ("gate 2", "what would", "refute it?"), "plum", "bolt", kind="gate").at(0, 0)  # fitted, then placed
    g2.at(g1.x - 150 - g2.w, cy=g1.cy)
    l = N("l", ("ledger", "and report"), "green", "audit", ring="green").at(40, cy=g2.cy)
    x = N("x", ("refused, and logged", "with the reason it died"), "red", "stop", ring="red").at(cx=(g1.cx + g2.cx) / 2, y=g1.bottom + 90)
    return Spec(
        slug="witness-two-gates-flow", post="witness-prove-it-or-it-doesnt-go-in-the-report", section="Gate 1: bind the field, not the document",
        title="A claim passes gate 1 and gate 2 or is refused and logged",
        desc=("A memory image goes through a read-only collector into hash-chained records. A claim with bindings meets "
              "gate 1: does the record say that? If yes it meets gate 2: what would refute it? A corroborated claim goes "
              "to the ledger and report. A claim that fails gate 1, or is refuted or unavailable at gate 2, is refused "
              "and logged with the reason it died."),
        alt=("Animated flowchart: a memory image goes through a read-only collector into hash-chained records; a claim "
             "with bindings meets gate 1, does the record say that, then gate 2, what would refute it; corroborated "
             "claims reach the ledger and report, and the rest are refused and logged with the reason they died"),
        caption="_Two gates between a claim and the report: the record must say it, and nothing that could refute it may stand._",
        h=int(x.bottom + 50), palette="navy",
        nodes=[e, c, s, f, g1, g2, l, x],
        edges=[
            E("e-ec", "e.r", "c.l"), E("e-cs", "c.r", "s.l"), E("e-sf", "s.r", "f.l"),
            E("e-fg1", "f.b", "g1.t"),
            E("e-yes", "g1.l", "g2.r", color="green", label=("yes",)),
            E("e-corr", "g2.l", "l.r", color="green", label=("corroborated",)),
            E("e-no", "g1.b", "x.r", route="vh", color="red", label=("no",)),
            E("e-ref", "g2.b", "x.l", route="vh", color="red", label=("refuted or unavailable",)),
        ],
        scenarios=[
            S("e", ("e-ec", "c"), ("e-cs", "s"), ("e-sf", "f"), ("e-fg1", "g1"), ("e-yes", "g2"), ("e-corr", "l")),
            S("e", ("e-ec", "c"), ("e-cs", "s"), ("e-sf", "f"), ("e-fg1", "g1"), ("e-no", "x")),
            S("e", ("e-ec", "c"), ("e-cs", "s"), ("e-sf", "f"), ("e-fg1", "g1"), ("e-yes", "g2"), ("e-ref", "x")),
        ],
        labels=("memory image", "read-only collector", "hash-chained records", "claim + bindings", "gate 1",
                "does the record say that?", "yes", "gate 2", "what would refute it?", "corroborated",
                "ledger and report", "no", "refused, and logged with the reason it died", "refuted or unavailable"),
    )


add(two_gates())


# 6. iocflow: the multi-agent team --------------------------------------------------------------------------------------

def agent_team() -> Spec:
    cx = 560
    sup = N("sup", ("supervisor", "routes next step"), "plum", "network", kind="gate").at(cx=cx, y=230)
    start = N("start", ("report text",), "sky", "doc", kind="pill").at(30, 30)
    hu = N("hu", ("hunter", "L4 queries"), "violet", "eye").at(cx=cx, y=20)
    ex = N("ex", ("extractor", "L1 entities"), "teal", "scissors").at(40, cy=sup.cy)
    en = N("en", ("enricher", "L2 + L3 assessment"), "blue", "layers").at(1160 - 280, cy=sup.cy)
    re_ = N("re", ("responder", "L5 dry-run → propose"), "orange", "bolt").at(cx=cx, y=sup.bottom + 120)
    gate = N("gate", ("ApprovalGate", "human authorizes"), "amber", "user", kind="hex", text="#451a03").at(1160 - 300, cy=re_.cy)
    end = N("end", ("Case",), "green", "check", kind="pill").at(cx=1019, cy=70)
    sx = sup.cx
    edges = [
        E("e-start", "start.r", "sup.td:-135", route="hv"),
        E("e-done", "sup.td:130", "end.l", route="vh", color="green", label=("all done",)),
        E("e-respond", "sup.bd:-40", "re.t:-40", color="sky", label=("respond",), lpos=(sx - 40 - 60, (sup.bottom + re_.y) / 2 + 10)),
        E("e-live", "re.t:40", "sup.bd:40", color="red", label=("live block",), lpos=(sx + 40 + 75, (sup.bottom + re_.y) / 2 + 10)),
        E("e-prop", "re.r:-22", "gate.l:-22", color="amber", dash=True, label=("proposal",)),
        E("e-appr", "gate.l:22", "re.r:22", color="green", dash=True, label=("approved",)),
    ]
    edges += [E("e-extract", "sup.ld:-22", "ex.r:-22", color="sky", label=("extract",)),
              E("e-extract-back", "ex.r:22", "sup.ld:22", color="green"),
              E("e-enrich", "sup.rd:-22", "en.l:-22", color="sky", label=("enrich",)),
              E("e-enrich-back", "en.l:22", "sup.rd:22", color="green"),
              E("e-hunt", "sup.td:-30", "hu.b:-30", color="sky", label=("hunt",), lpos=(sx - 30 - 55, (hu.bottom + sup.y) / 2 + 10)),
              E("e-hunt-back", "hu.b:30", "sup.td:30", color="green")]
    return Spec(
        slug="ioc-lifecycle-multi-agent-team-flow", post="iocflow-agentic-ioc-lifecycle",
        section="The capstone: a small multi-agent team",
        title="A supervisor routes a report through four agents and a human gate",
        desc=("A report text goes to a supervisor that routes the next step. It sends work to an extractor (L1 entities), "
              "an enricher (L2 and L3 assessment), a hunter (L4 queries) and a responder (L5 dry-run, then propose); the "
              "first three report back to the supervisor. The responder's proposal goes to an ApprovalGate where a human "
              "authorizes it, and once approved the live block returns to the supervisor. When all is done, the result is a case."),
        alt=("Animated flowchart: report text enters a supervisor that routes to an extractor, an enricher, a hunter and a "
             "responder; the responder's dry-run proposal goes to an approval gate where a human authorizes it, the approved "
             "live block returns to the supervisor, and when all is done the result is a case"),
        caption="_One supervisor, four specialists and a human gate: the responder only blocks live after an approval._",
        h=int(re_.bottom + 70), palette="plum",
        nodes=[start, sup, hu, ex, en, re_, gate, end], edges=edges,
        scenarios=[S("start", ("e-start", "sup"), ("e-extract", "ex"), ("e-extract-back", "sup"), ("e-enrich", "en"),
                     ("e-enrich-back", "sup"), ("e-hunt", "hu"), ("e-hunt-back", "sup"), ("e-respond", "re"),
                     ("e-prop", "gate"), ("e-appr", "re"), ("e-live", "sup"), ("e-done", "end"))],
        labels=("report text", "supervisor", "routes next step", "extract", "extractor", "L1 entities", "enrich",
                "enricher", "L2 + L3 assessment", "hunt", "hunter", "L4 queries", "respond", "responder",
                "L5 dry-run → propose", "proposal", "ApprovalGate", "human authorizes", "approved", "live block",
                "all done", "Case"),
    )


add(agent_team())


# 8. find-evil: the fix and its boundary --------------------------------------------------------------------------------

def find_evil_boundary() -> Spec:
    m1 = N("m1", ("extract_iocs",), "teal", "search", chips=("re-fang", "TLD check", "dedup", "LOLBin-aware"), w=480).at(660, 170)
    m4 = N("m4", ("suggest_hunts",), "violet", "eye", chips=("CQL", "XQL", "Sigma"), w=480).at(660, m1.bottom + 18)
    m5 = N("m5", ("propose_blocks", "DRY-RUN only, no execute path"), "orange", "lock", w=480, bold=(1,)).at(660, m4.bottom + 18)
    mcp = Group("mcp", "find-evil MCP server (typed, stdio)", 640, 90, 520, m5.bottom + 26 - 90, icon="shield",
                note="ARCHITECTURAL boundary", note_bold=True, color="#34d399")
    tools = N("tools", ("SIFT forensic tools",), "slate", "folder", chips=("plaso", "Volatility", "YARA", "Sleuth Kit"),
              w=380).at(40, 0)
    agent = N("agent", ("Protocol SIFT", "= Claude Code agent", "baseline: eyeballs dumps", "→ hallucinates",
                        "find-evil: calls MCP,", "then reconciles"), "indigo", "cpu", nt=2, w=380).at(40, cy=mcp.y + mcp.h / 2)
    tools.at(40, agent.y - 50 - tools.h)
    out = N("out", ("Reconciled report", "+ hunts + dry-run block plan"), "green", "check", w=480).at(660, mcp.y + mcp.h + 40)
    recon = N("recon", ("Self-correction:", "reconcile eyeballed", "vs ground truth"), "pink", "loop", chips=("correct", "flag hallucinations", "add misses"), w=380).at(40, cy=out.cy)
    return Spec(
        slug="forensic-agent-self-correction-boundary-flow", post="find-evil-self-correcting-dfir-agent",
        section="The fix: hand the reading to a deterministic parser",
        title="The agent calls typed MCP tools, then reconciles against ground truth",
        desc=("SIFT forensic tools (plaso, Volatility, YARA, Sleuth Kit) feed the Protocol SIFT agent, a Claude Code agent. "
              "Baseline, it eyeballs dumps and hallucinates; with find-evil it calls the MCP server and then reconciles. "
              "The typed stdio MCP server is an architectural boundary with extract_iocs, suggest_hunts and propose_blocks, "
              "which is dry-run only with no execute path. Raw text goes in, structured IOCs come back, and the agent "
              "reconciles what it eyeballed against ground truth to produce a reconciled report, hunts and a dry-run block plan."),
        alt=("Animated flowchart: SIFT forensic tools feed an agent that sends raw text across a typed MCP server boundary "
             "and gets structured IOCs back; the server exposes extract_iocs, suggest_hunts and a dry-run-only "
             "propose_blocks; the agent then reconciles what it eyeballed against ground truth into a reconciled report, "
             "hunts and a dry-run block plan"),
        caption="_The agent reads raw text only through typed tools, and the tool that proposes blocks has no execute path._",
        h=int(max(out.bottom, recon.bottom) + 50), palette="forest",
        nodes=[tools, agent, m1, m4, m5, recon, out], groups=[mcp],
        edges=[
            E("e-ta", "tools.b", "agent.t"),
            E("e-raw", "agent.r:-35", "mcp.l:-35", color="sky", label=("raw text",)),
            E("e-struct", "mcp.l:35", "agent.r:35", color="green", label=("structured IOCs",)),
            E("e-ar", "agent.b", "recon.t"),
            E("e-ro", "recon.r", "out.l", color="green"),
        ],
        scenarios=[S("tools", ("e-ta", "agent"), ("e-raw", "mcp"), ("", "m1"), ("", "m4"), ("", "m5"),
                     ("e-struct", "agent"), ("e-ar", "recon"), ("e-ro", "out"))],
        labels=("SIFT forensic tools", "plaso", "Volatility", "YARA", "Sleuth Kit", "Protocol SIFT",
                "= Claude Code agent", "baseline: eyeballs dumps → hallucinates", "find-evil: calls MCP, then reconciles",
                "find-evil MCP server (typed, stdio)", "ARCHITECTURAL boundary", "extract_iocs", "re-fang", "TLD check",
                "dedup", "LOLBin-aware", "suggest_hunts", "CQL", "XQL", "Sigma", "propose_blocks",
                "DRY-RUN only, no execute path", "raw text", "structured IOCs", "Self-correction:",
                "reconcile eyeballed vs ground truth", "correct", "flag hallucinations", "add misses",
                "Reconciled report + hunts + dry-run block plan"),
        notes="the dash in the group title (find-evil MCP server (typed, stdio) — ARCHITECTURAL boundary) became two lines",
    )


add(find_evil_boundary())


# 4a. aisoc: architecture at a glance -----------------------------------------------------------------------------------

def soc_architecture() -> Spec:
    gx = 500
    bar_x, bar_w = gx + 60, 220
    strg = N("strg", ("soc.triage",), "blue", w=bar_w, h=110).at(bar_x, 190)
    saud = N("saud", ("soc.audit",), "orange", w=bar_w, h=140).at(bar_x, strg.bottom + 60)
    scas = N("scas", ("soc.cases",), "teal", w=bar_w, h=240).at(bar_x, saud.bottom + 60)
    bus = Group("bus", "Redis Streams bus", gx, strg.y - 74, 340, scas.bottom + 30 - (strg.y - 74), icon="wave")
    sentinel = N("sentinel", ("Sentinel / Tier 1", "alert triage"), "indigo", "eye").at(30, cy=strg.cy)
    feed = N("feed", ("Alert feed",), "sky", "flag").at(30, 0)
    feed.at(30, sentinel.y - 50 - feed.h)
    timers = []
    for i, (lines, grad, ico) in enumerate((
            (("SOC Manager", "shift summaries", "every 8 hours"), "cyan", "clock"),
            (("Detection Engineer", "rule tuning", "weekday mornings"), "lime", "tag"),
            (("Threat Hunter", "pattern sweeps", "twice a day"), "plum", "bug"))):
        timers.append(N(("socmgr", "deteng", "hunter")[i], lines, grad, ico, w=320).at(30, saud.y - 10 + i * 160))
    rx = 880
    tier2 = N("tier2", ("Tier 2 Analyst", "deeper investigation"), "violet", "search", w=300).at(rx, 240)
    ir = N("ir", ("IR Lead", "SEV + containment plan"), "pink", "shield", w=300).at(rx, 420)
    flask = N("flask", ("Flask HITL pages", "/soc-hitl/decide", "/soc-hitl/audit"), "amber", "user", w=300,
              text="#451a03", bold=(1, 2)).at(rx, cy=scas.cy)
    chat = N("chat", ("Chat card buttons",), "sky", "chat", w=300).at(rx, flask.bottom + 55)
    ti = N("ti", ("Threat Intel", "actor + MITRE"), "teal", "network").at(cx=scas.cx, y=bus.y + bus.h + 55)
    edges = [
        E("e-feed", "feed.b", "sentinel.t"),
        E("e-sent", "sentinel.r", "strg.l"),
        E("e-triage", "strg.r", "tier2.l:-25", route="hvh", mid=800),
        E("e-t2", "tier2.l:25", "scas.r:-110", route="hvh", mid=820),
        E("e-ir", "scas.r:-60", "ir.l:-22", route="hvh", mid=840),
        E("e-ir-back", "ir.l:22", "scas.r:-30", route="hvh", mid=860),
        E("e-hitl", "ir.b", "flask.t", color="amber", dash=True, label=("HITL action proposed",)),
        E("e-click", "chat.t", "flask.b", color="sky", dash=True, label=("click",)),
        E("e-flask", "flask.l", "scas.r"),
        E("e-ti", "scas.b:-45", "ti.t:-45", color="sky"),
        E("e-ti-back", "ti.t:45", "scas.b:45", color="green"),
        E("e-m1", "strg.b", "saud.t", color="amber", dash=True, label=("mirror",)),
        E("e-m2", "scas.t", "saud.b", color="amber", dash=True, label=("mirror",)),
    ]
    for i, t in enumerate(timers):
        edges.append(E(f"e-replay{i + 1}", f"saud.l:{-45 + 45 * i}", f"{t.id}.r", route="hvh", mid=455 + 15 * i, color="sky",
                       dash=True, label=("replay",), lpos=(395, t.cy)))
    return Spec(
        slug="eight-role-ai-soc-architecture-flow", post="building-aisoc", section="Architecture at a glance",
        title="Eight roles around a Redis Streams bus, with a human gate",
        desc=("An alert feed goes to Sentinel, Tier 1 alert triage, which writes to the soc.triage stream. Tier 2 Analyst "
              "investigates and writes to soc.cases, where the IR Lead makes a severity and containment plan. The IR Lead "
              "proposes a human-in-the-loop action to the Flask pages, a chat card button click reaches the same pages, and "
              "the decision returns to soc.cases. Threat Intel adds actor and MITRE context. soc.triage and soc.cases mirror "
              "into soc.audit, which the SOC Manager, the Detection Engineer and the Threat Hunter replay on a schedule."),
        alt=("Animated architecture flowchart: an alert feed goes to Sentinel, then through the soc.triage, soc.cases and "
             "soc.audit streams of a Redis Streams bus; Tier 2 Analyst, IR Lead and Threat Intel work on the cases stream, "
             "the IR Lead proposes an action to Flask approval pages that chat card buttons also reach, and the SOC Manager, "
             "Detection Engineer and Threat Hunter replay the audit stream"),
        caption="_Reactive roles hand work along the streams, a human approves any action, and three timer roles replay the audit log._",
        h=int(ti.bottom + 50), palette="indigo",
        nodes=[feed, sentinel, strg, saud, scas, *timers, tier2, ir, flask, chat, ti], groups=[bus], edges=edges,
        scenarios=[S("feed", ("e-feed", "sentinel"), ("e-sent", "strg"), ("e-triage e-m1", "tier2 saud"), ("e-t2", "scas"),
                     ("e-ir", "ir"), ("e-ir-back", "scas"), ("e-hitl", "flask"), ("", "chat"), ("e-click", "flask"),
                     ("e-flask", "scas"), ("e-ti", "ti"), ("e-ti-back", "scas"), ("e-m2", "saud"),
                     ("e-replay1 e-replay2 e-replay3", "socmgr deteng hunter"))],
        labels=("Alert feed", "Sentinel / Tier 1", "alert triage", "Redis Streams bus", "soc.triage", "soc.cases",
                "soc.audit", "Tier 2 Analyst", "deeper investigation", "IR Lead", "SEV + containment plan",
                "HITL action proposed", "Flask HITL pages", "/soc-hitl/decide", "/soc-hitl/audit", "Chat card buttons",
                "click", "Threat Intel", "actor + MITRE", "replay", "SOC Manager", "shift summaries", "every 8 hours",
                "Detection Engineer", "rule tuning", "weekday mornings", "Threat Hunter", "pattern sweeps", "twice a day",
                "mirror"),
    )


add(soc_architecture())


# sequence diagrams: participants across the top, a lifeline under each, one message per row ------------------------------

def message(mid: str, xs: list[float], i: int, j: int, y: float, label: tuple[str, ...], color: str = "sky",
            dash: bool = False) -> E:
    return E(mid, (xs[i], y), (xs[j], y), color=color, dash=dash, label=label, plain=True, lpos=((xs[i] + xs[j]) / 2, y))


# 4b. aisoc: the human-in-the-loop gate ---------------------------------------------------------------------------------

def hitl_sequence() -> Spec:
    xs = [105 + 190 * i for i in range(6)]

    def who(i: int, pid: str, lines: tuple[str, ...], grad: str, ico: str) -> N:
        return N(pid, lines, grad, ico, layout="top", w=172, tsize=20, life=True).at(cx=xs[i], y=30)

    ir = who(0, "ir", ("IR Lead", "(LLM agent)"), "pink", "shield")
    bus = who(1, "bus", ("Redis Streams",), "teal", "wave")
    chat = who(2, "chat", ("Team-chat", "card", "(SOC bot)"), "sky", "chat")
    chat.nt = 2
    human = who(3, "human", ("Approver",), "violet", "user")
    flask = who(4, "flask", ("Flask HITL", "page"), "amber", "lock")
    flask.text = "#451a03"
    sql = who(5, "sql", ("hitl.sqlite",), "indigo", "db")
    y0 = max(p.bottom for p in (ir, bus, chat, human, flask, sql)) + 120
    ys = [y0, y0 + 95, y0 + 190, y0 + 285, y0 + 400, y0 + 485, y0 + 565, y0 + 665]
    note = N("note", ("v2 future: executor agent", "consumes approved decisions"), "amber", kind="note", nt=0, bold=(0, 1),
             text="#451a03").at(cx=xs[1], y=ys[-1] + 55)
    edges = [
        message("m1", xs, 0, 1, ys[0], ("IRPlan + ActionProposed", '(approver_role="IR Lead On-Call")')),
        message("m2", xs, 0, 2, ys[1], ("Card with 2 buttons", "(Action.OpenUrl)")),
        message("m3", xs, 2, 3, ys[2], ('Banner: "Action required', 'from: IR Lead On-Call"')),
        message("m4", xs, 3, 4, ys[3], ("Click Approve", "or Reject")),
        message("m5", xs, 4, 3, ys[4], ("Confirmation page", "(login_required,", "DEMO MODE banner)")),
        message("m6", xs, 3, 4, ys[5], ("Submit decision",)),
        message("m7", xs, 4, 5, ys[6], ("Persist decision",)),
        message("m8", xs, 4, 1, ys[7], ("ActionDecision", "(approved|rejected, dummy=True)"), color="green"),
    ]
    return Spec(
        slug="eight-role-ai-soc-hitl-gate-flow", post="building-aisoc", section="The HITL gate",
        title="A human approves an action through a chat card and a web page",
        desc=("The IR Lead agent puts an IRPlan and an ActionProposed event, with an approver role, on the Redis Streams "
              "bus and posts a team-chat card with two buttons. The chat banner tells the approver an action is required. "
              "The approver clicks Approve or Reject, gets a confirmation page on the Flask HITL page, submits the "
              "decision, which is persisted in hitl.sqlite, and an ActionDecision goes back on the bus. A later version "
              "adds an executor agent that consumes approved decisions."),
        alt=("Animated sequence diagram: the IR Lead agent proposes an action on the bus and posts a chat card; the "
             "approver clicks Approve or Reject, confirms on a web page and submits; the decision is saved in a database "
             "and an ActionDecision returns to the bus, where a future executor agent will consume approved decisions"),
        caption="_One approval, step by step: the card links to a page, the decision is stored, and only then does a decision event reach the bus._",
        h=int(note.bottom + 60), palette="rose", lifeline_to=note.y - 14,
        nodes=[ir, bus, chat, human, flask, sql, note], edges=edges,
        scenarios=[S("ir", ("m1", "bus"), ("m2", "chat"), ("m3", "human"), ("m4", "flask"), ("m5", "human"),
                     ("m6", "flask"), ("m7", "sql"), ("m8", "bus"), ("", "note"))],
        labels=("IR Lead", "(LLM agent)", "Redis Streams", "Team-chat card", "(SOC bot)", "Approver", "Flask HITL page",
                "hitl.sqlite", "IRPlan + ActionProposed", '(approver_role="IR Lead On-Call")', "Card with 2 buttons",
                "(Action.OpenUrl)", 'Banner: "Action required from: IR Lead On-Call"', "Click Approve or Reject",
                "Confirmation page", "(login_required, DEMO MODE banner)", "Submit decision", "Persist decision",
                "ActionDecision (approved|rejected, dummy=True)", "v2 future: executor agent",
                "consumes approved decisions"),
        notes="the banner's target emoji is not drawn (the font has no glyph for it); the Flask-to-SQLite 'Persist decision' step keeps its order",
    )


add(hitl_sequence())


# 5. aisoc case memory: interrogating a case ------------------------------------------------------------------------------

def interrogation_sequence() -> Spec:
    xs = [200, 600, 1000]
    user = N("user", ("Reviewer question", "(why contain host", "X on case N?)"), "sky", "ask", layout="top", life=True, w=260).at(cx=xs[0], y=30)
    mem = N("mem", ("Case memory", "(deterministic)"), "teal", "db", layout="top", life=True, w=260).at(cx=xs[1], y=30)
    llm = N("llm", ("Narrator LLM", "(grounded)"), "violet", "sparkle", layout="top", life=True, w=260).at(cx=xs[2], y=30)
    y0 = user.bottom + 100
    ys = [y0, y0 + 110, y0 + 340, y0 + 440]
    n1 = N("n1", ("Web panel stops here,", "pure render, no model"), "amber", kind="note", nt=0, bold=(0, 1),
           text="#451a03").at(cx=xs[1], y=ys[1] + 60)
    n2 = N("n2", ("Cannot invent a reason", "that is not in the trace"), "amber", kind="note", nt=0, bold=(0, 1),
           text="#451a03").at(cx=xs[2], y=ys[3] + 60)
    edges = [
        message("m1", xs, 0, 1, ys[0], ("get_case_reasoning(case_id)",)),
        message("m2", xs, 1, 0, ys[1], ("Recorded trace, verdicts,", "evidence, HITL decision, timeline"), color="green", dash=True),
        message("m3", xs, 0, 2, ys[2], ("trace plus rule, answer ONLY from this record",)),
        message("m4", xs, 2, 0, ys[3], ("Containment reason cited from the trace,", "with approver and time"), color="green", dash=True),
    ]
    return Spec(
        slug="ai-soc-case-memory-interrogation-flow", post="aisoc-case-memory", section="Interrogation: explain the decision from the record",
        title="Asking why a host was contained: a recorded trace, then a grounded narrator",
        desc=("A reviewer asks why a host was contained on a case. The case memory, which is deterministic, returns the "
              "recorded trace, verdicts, evidence, HITL decision and timeline for get_case_reasoning; the web panel stops "
              "there, as a pure render with no model. The trace plus a rule, to answer only from this record, go to the "
              "grounded narrator LLM, which returns the containment reason cited from the trace with the approver and "
              "time. It cannot invent a reason that is not in the trace."),
        alt=("Animated sequence diagram: a reviewer question calls get_case_reasoning on a deterministic case memory, which "
             "returns the recorded trace and stops there for the web panel with no model; the trace and a rule to answer "
             "only from this record go to a grounded narrator LLM, which returns the containment reason cited from the "
             "trace, with approver and time, and cannot invent a reason that is not in the trace"),
        caption="_Two ways to read a case: the deterministic trace alone, or a narrator that may only answer from that trace._",
        h=int(n2.bottom + 60), palette="teal", lifeline_to=n2.y - 14,
        nodes=[user, mem, llm, n1, n2], edges=edges,
        scenarios=[S("user", ("m1", "mem"), ("m2", "user"), ("", "n1"), ("m3", "llm"), ("m4", "user"), ("", "n2"))],
        labels=("Reviewer question", "(why contain host X on case N?)", "Case memory", "(deterministic)", "Narrator LLM",
                "(grounded)", "get_case_reasoning(case_id)", "Recorded trace, verdicts, evidence, HITL decision, timeline",
                "Web panel stops here, pure render, no model", "trace plus rule, answer ONLY from this record",
                "Containment reason cited from the trace, with approver and time",
                "Cannot invent a reason that is not in the trace"),
    )


add(interrogation_sequence())
