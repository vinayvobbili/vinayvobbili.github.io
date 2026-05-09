---
title: "Three Phases of RAG Quality: Embeddings → Reranking → Fine-Tuned Reranking"
description: How retrieval quality evolved on a 32K+ ticket corpus — from plain dense search, to a stock cross-encoder reranker, to fine-tuning the reranker on our own labeled pairs (+41% MRR@10).
date: 2026-05-09 09:00:00 -0400
categories: [LLM, RAG]
tags: [rag, embeddings, reranker, fine-tuning, bge, vector-search]
---

> Draft — not yet published. Outline below; replace bracketed sections with the real numbers and code from the production system.

## TL;DR

Building RAG over 32K+ historical tickets, retrieval quality didn't get to "good enough"
in one step. It evolved through three phases, each unlocked by the last:

1. **Phase 1 — Embeddings only.** Dense vector search worked, but the top-5 was noisy enough
   that the LLM regularly grounded its answer in a near-miss neighbor instead of the actually
   relevant ticket.
2. **Phase 2 — Stock cross-encoder reranker.** Adding `bge-reranker-v2-m3` on top of the
   top-50 candidates fixed a lot of the noise. Most teams stop here.
3. **Phase 3 — Fine-tuned reranker on our own pairs.** Mining implicit relevance signals from
   ticket history (which tickets analysts linked together) and training the reranker on those
   pairs gave us **+41% MRR@10** over the stock model.

Phase 3 was the highest-ROI change in the entire stack — and it's the phase most teams skip
because they assume reranker fine-tuning is exotic. It isn't.

## The setup

- Corpus: ~32,000 historical XSOAR security tickets (rich text, structured metadata, analyst notes).
- Embedding model: [name]
- Vector store: ChromaDB, persistent on disk.
- Consumer: a SOC investigation agent that answers questions like *"Have we seen this IOC
  pattern before? What did we conclude?"*

The retrieval quality target was simple: when an analyst asks about a current incident,
the agent should ground its answer in *the actual prior ticket* that's most relevant — not
a vector neighbor that happens to share keywords.

## Phase 1: Embeddings only

[Describe the initial setup. Embedding model. Chunking strategy. Top-k retrieval.
What worked, what didn't. Concrete failure mode example: a query about [X] returned [Y]
in the top results because vectors are similar, but a human reading both knew the answer
was buried at rank 12.]

**Why it wasn't enough:** dense retrieval ranks by *semantic similarity*, not *relevance to
the query intent*. For ticket retrieval those overlap a lot, but the long tail of "almost
right" results is where the LLM grounded answers go wrong.

## Phase 2: Add a stock cross-encoder reranker

[Describe the reranker integration. bge-reranker-v2-m3, top-50 candidates from vectors,
rerank to top-5, hand to LLM. Where it ran (mac-m3 → studio1, MPS, ~568M params). Latency cost.]

**The lift:** [describe the qualitative improvement, ideally with a before/after example.
Mention any quantitative measurement if you ran one — even informal.]

This is where most RAG pipelines I see in production stop. It's a real win and it requires
near-zero custom work — just add the model, sort by score, take the top-k.

## Phase 3: Fine-tune the reranker on our own pairs

[The interesting phase. Walk through:
- The hypothesis: the stock reranker is trained on generic web data; our domain has its own
  relevance signal that the model has never seen.
- The labels: how we mined positive/negative pairs from ticket history. Specifically,
  [explain which ticket-to-ticket relationships you used as positive signal — explicitly
  linked tickets, manual analyst references, etc. — and how you sampled negatives.]
- The training setup: framework (sentence-transformers? FlagEmbedding?), loss function
  (MarginRankingLoss / contrastive?), training set size, eval set size, hardware, time-to-train.
- The eval: MRR@10, recall@k, NDCG. The +41% number lands here.]

```python
# Sketch of the training loop — fill in with the actual code path.
# from sentence_transformers import CrossEncoder, InputExample, losses
# ...
```

**The headline result: +41% MRR@10 over the stock bge-reranker-v2-m3.**

[Include eval methodology — held-out queries, how relevance was scored, what the baseline was.]

## What surprised me

[Pick 2-3 surprising findings from the fine-tune phase. E.g.: the smaller training set than
expected was enough, hard-negative mining mattered more than dataset size, the fine-tuned
model generalized to query phrasings outside the training distribution, etc.]

## What I'd do differently

[Honest reflection. E.g.: I should have tried this earlier instead of tweaking embedding
chunking for months. Or: the eval harness should have come first. Or: fine-tuning the
embedding model would have been a more controversial bet.]

## When you should consider doing this

- You have a domain corpus where "relevant" means something specific (legal, medical,
  security tickets, internal company docs).
- You have an implicit relevance signal somewhere in your data (clicks, links, analyst
  references, ticket relationships) that you can mine.
- A stock reranker is already in your pipeline and you've tuned chunking + top-k and are
  out of obvious wins.
- You have a few hundred to a few thousand labeled pairs; you don't need millions.

## Reproducing this

[Link to the public repo if/when the training code is open-sourced. Otherwise describe the
recipe in enough detail that a reader could build their own version.]

---

*If you found this useful or you've tried fine-tuning your own reranker, I'd love to hear
how it went — reach me on [LinkedIn](https://www.linkedin.com/in/vinay-vobbilichetty) or by
[email](mailto:vinayvobbilichetty11@gmail.com).*
