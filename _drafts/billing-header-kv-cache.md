---
title: "Why Self-Hosted Claude Code Was 15× Slower Than It Should Be"
description: A debugging story about prefix-KV caches, a rotating billing header, and a vllm-mlx engine that wasn't caching what we thought it was. Two patches together turned 108-second turns into 7-second turns.
date: 2026-05-09 09:00:00 -0400
categories: [LLM, Performance]
tags: [vllm, mlx, claude-code, kv-cache, prefix-cache, prompt-cache, debugging]
---

> Draft — not yet published. Outline below; replace bracketed sections with real screenshots, timings, and code snippets from the patches.

## TL;DR

I was running [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) against a
self-hosted vllm-mlx backend on a Mac Studio. Cold turns took ~108 seconds and follow-ups
weren't getting noticeably faster, even though the system prompt was identical and *every*
inference engine I know of caches a stable prompt prefix.

Two findings, both required to get the speedup:

1. **Claude Code injects a rotating `x-anthropic-billing-header` value into the system block on every turn.** Even though the user-visible system prompt is stable, the bytes the engine hashes for cache lookup change every request. The prefix cache misses 100% of the time. Strip the header at the proxy layer and the cache becomes useful.
2. **vllm-mlx's `SimpleEngine` doesn't actually cache the system prefix the way you'd expect.** Even with the rotating header gone, you need a small patch — a single-slot, hash-keyed system-prefix KV cache — to get hits across turns of a session.

Together: **108-second turns → 7-8 second follow-ups.** A 13-15× speedup, on the same hardware,
with the same model.

## The setup

- Backend: vllm-mlx serving Qwen2.5-Coder-32B-Instruct-8bit on a Mac Studio (96GB).
- Front door: a small Python shim that exposes an Anthropic-compatible `/v1/messages` endpoint
  and translates to the OpenAI-style API vllm-mlx serves.
- Client: Claude Code (the CLI), pointed at the shim via [`claude-code-router`](https://github.com/musistudio/claude-code-router).
- Goal: a self-hosted Claude Code experience that keeps source code, tickets, and customer
  data on premises.

The architecture worked end-to-end. Tool calling worked. Streaming worked. The model output was
fine. It was just *slow*. Painfully slow on every turn, including ones where the system prompt
should have been cached.

## What I expected vs what I saw

[Insert side-by-side: expected behavior — long cold turn, then fast follow-ups thanks to
prefix-KV cache; observed behavior — every turn took ~100s regardless of conversation depth.]

For context: Claude Code's prompts are large. The system block, tool definitions, and prior
turns add up to 30K+ tokens easily. With a working prefix cache, only the new user message
needs to be processed — typically a few hundred tokens. Without one, the engine reprocesses
the whole prefix every turn.

## Finding #1: the rotating billing header

The first clue came from diffing the raw bytes of two consecutive `/v1/messages` requests
from Claude Code. Almost everything was identical — system prompt, tool list, conversation
history. But there was one block that changed:

```
"system": [
  {"type": "text", "text": "..."},
  {"type": "text", "text": "<x-anthropic-billing-header>cch=...</x-anthropic-billing-header>"},
  ...
]
```

Claude Code injects an `x-anthropic-billing-header` system block. The `cch=` value rotates on
every turn — it's used by Anthropic's API for billing/usage tracking. On the hosted Anthropic
API, this is fine; the cache is keyed on a normalized form that ignores it.

But on a self-hosted backend that just hashes the prompt as-is, the rotating value busts the
cache key. **Every turn looks like a brand-new prompt to the engine, because every turn is a
brand-new prompt.**

The fix at the shim layer is one filter:

```python
# Sketch — pull the actual implementation from deployment/claude_router_shim.py
def strip_billing_header(messages):
    for msg in messages:
        if msg.get("role") == "system" and isinstance(msg.get("content"), list):
            msg["content"] = [
                block for block in msg["content"]
                if not _is_billing_header_block(block)
            ]
    return messages
```

[Show the actual filter code from `deployment/claude_router_shim.py`.]

Note: vllm-mlx's PR #277 quietly does the same fix for the `/v1/messages` endpoint. If
you're on a recent build of vllm-mlx and using its native Anthropic adapter, you may not
need to do this at the shim layer. I was running my own shim (for tool-call buffering on
the Coder alias), so I had to strip the header myself.

## Finding #2: SimpleEngine wasn't caching what I thought

After stripping the billing header, I expected a giant speedup on the second turn. I got
a *modest* speedup — a few seconds shaved — but follow-ups still took most of a minute.

Profiling the engine showed the prefill stage was running on the full prefix on every turn.
The cache hit rate was effectively zero.

The reason: vllm-mlx's `SimpleEngine` (the lightweight server path, not the full vLLM core)
doesn't carry over a previous session's KV cache to the next request. Each request gets a
fresh KV state. The "prefix cache" in vllm-mlx's full engine isn't wired into SimpleEngine
the same way.

[Walk through what SimpleEngine does on each request, and why a stable prefix doesn't
auto-cache. Reference the actual file paths in the upstream vllm-mlx repo.]

The fix: a small patch that adds a **single-slot, hash-keyed system-prefix KV cache** to
SimpleEngine. On each request, hash the prefix; if it matches the slot, reuse the KV state
and skip prefill for the matched tokens; if it doesn't, recompute and overwrite the slot.

```diff
[Excerpt from deployment/vllm_mlx_patches/system_kv_cache_for_simple_engine.patch — show
the smallest meaningful diff: hash computation, slot check, KV reuse path.]
```

Single-slot is intentional: a Claude Code session has one conversation at a time, so a
multi-slot cache is overkill. Hashing the prefix tokens (not the full prompt — just the
stable system + tools prefix) makes the cache survive new user messages on the tail end.

## The numbers

[Insert real timing screenshots / table.]

| State | Cold turn | Warm turn |
|---|---|---|
| Stock vllm-mlx, no shim | 108s | 102s |
| Shim strips billing header, stock vllm-mlx | 105s | 70s |
| Shim strips header + SimpleEngine KV-cache patch | 108s | **7-8s** |

The cold turn doesn't change — there's no cache to hit on first request. The warm-turn
delta is what matters: **13-15× faster** on every turn after the first, on the same
hardware, with the same model.

## What I'd do differently

[Honest reflection. E.g.: the first thing I should have done was diff two consecutive
requests at the byte level — that would have caught the rotating header in 5 minutes. I
spent a lot longer staring at engine internals before I checked the *input*.]

## When you'd hit this

You'd hit this if you:
- Self-host an Anthropic-compatible LLM backend (vllm-mlx, llama.cpp's Anthropic adapter,
  or any custom shim).
- Point Claude Code or another Anthropic-protocol client at it.
- Notice that warm turns aren't faster than cold turns even though your system prompt is
  stable.

If you're going through the official Anthropic API, none of this applies — Anthropic's
caching layer handles the billing header transparently.

## Reproducing this

[Link to the public repo where the patches live. Specifically:
- `deployment/claude_router_shim.py` — billing header strip + tool-call buffering
- `deployment/vllm_mlx_patches/apply.sh` — idempotent patch installer
- `deployment/vllm_mlx_patches/system_kv_cache_for_simple_engine.patch` — the SimpleEngine patch]

The patches are small enough to read in five minutes. If you're running vllm-mlx and you
care about Claude Code latency, they're worth the read.

## Credits

vllm-mlx PR #277 found the billing-header issue independently for the `/v1/messages`
endpoint and is the right upstream fix if you're using vllm-mlx's native Anthropic adapter.
The SimpleEngine prefix-cache patch is mine; happy to upstream if there's interest.

---

*If you've hit this too, or your self-hosted Claude Code setup is slow for a different
reason I haven't found yet, I'd love to hear about it — reach me on
[LinkedIn](https://www.linkedin.com/in/vinay-vobbilichetty) or by
[email](mailto:vinayvobbilichetty11@gmail.com).*
