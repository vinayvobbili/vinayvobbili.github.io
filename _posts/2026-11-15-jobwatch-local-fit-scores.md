---
title: "Scoring Job Fit on a Laptop: A 29-Verdict Check Instead of a Benchmark"
image:
  path: /assets/img/posts/fit-scores-on-a-laptop-hero.png
  alt: "Requirements are judged by a local model and the score is computed in code; three models agreed with 28, 27 and 29 of 29 expected verdicts, so the smallest and fastest stayed"
description: "jobwatch scores job fit with a 9B model on the same Mac. Three models agreed on 28, 27 and 29 of 29 verdicts, so the smallest and fastest stayed."
date: 2026-11-15 09:00:00 -0500
categories: [Open Source, LLM]
tags: [jobwatch, local-llm, mlx, evaluation, fit-scoring, qwen, gemma, open-source, python, apple-silicon]
accent: indigo
---

## TL;DR

A keyword ranker can't tell "uses Kubernetes" from "5+ years running Kubernetes in
production". So [jobwatch](https://vinayvobbili.github.io/jobwatch/) can
fit-score the most relevant new jobs against your resume, and by default it does
that with a small model running on your own machine, so with the local backend
your resume and the postings never leave it. The scoring comes from my separate
[shortlist-ai](https://github.com/vinayvobbili/shortlist-ai) project.

<div class="tldr-cards">
<div class="tldr-card"><span class="tldr-num">29</span><span class="tldr-sub">expected requirement verdicts the three models were checked against</span></div>
<div class="tldr-card"><span class="tldr-num">28 / 27 / 29</span><span class="tldr-sub">verdicts agreed: Qwen3.5-9B 4-bit, 6-bit, Gemma 4 12B</span></div>
<div class="tldr-card"><span class="tldr-num">7.5 GB</span><span class="tldr-sub">peak memory of the one that stayed, also the fastest</span></div>
</div>

## What a score is made of

shortlist-ai does three things per job. It turns the posting into must-have and
nice-to-have requirements. It judges each requirement against the resume, with
quotes that are checked against the resume text. And it lists the must-haves the
resume doesn't show. The model never produces the number: it judges each
requirement as met, partly or missing, and the score is computed in code from
those verdicts, so it can be checked instead of taken on faith.

Every card keeps its reasons. This is the shape of what `jobwatch show` prints
for a made-up posting at Initech (first three of its requirements):

```
Fit 78/100, must-haves 4/6 (scored by Qwen3.5-9B · local)
  met     [must] 5+ years running Kubernetes in production  "Ran 40-node Kubernetes clusters for 6 years at Globex"
  met     [must] Terraform or similar infrastructure as code  "Wrote the Terraform modules behind 120 services"
  partly  [must] Observability (metrics, tracing)  "Set up Prometheus dashboards for the payments team"
```

## Choosing the model: a check, not a benchmark

The question was which local model to suggest for a 16 GB Mac. shortlist-ai has a
held-out set: ten synthetic candidates, three jobs, and 29 expected requirement
verdicts. The set's README says it was committed before any model ran on it, and
git agrees: the verdicts file went in on September 26, hours before the first
results, and hasn't changed since. Three models, each served on the same 16 GB
Apple Silicon Mac, scored it one at a time:

| Model | Verdicts agreeing (of 29) | Per call | Peak memory |
|---|---|---|---|
| Qwen3.5-9B, 4-bit | 28 | 27 s | 7.5 GB |
| Qwen3.5-9B, 6-bit | 27 | 36 s | 9.7 GB |
| Gemma 4 12B, 4-bit | 29 | 42 s | 9.2 GB |

Each run was 90 model calls. Ranking quality was the same for all three: the
right candidate came first every time, and the mean NDCG@3 was between 0.98 and
1.00.

The tempting reading is "Gemma wins, 29 out of 29." The repo's write-up says
otherwise, and I think it's right. The spread is one verdict. An earlier run of
the 4-bit Qwen on this very set scored 29 of 29 in every one of three requirement
orderings, so a one-verdict gap sits inside the noise floor. The 6-bit build was
slower, bigger and agreed on fewer verdicts, so more bits bought nothing. The
fastest and smallest model stayed as the suggestion. Gemma 4 12B is listed as the
"also good" row: the most accurate here, about 50% slower, 1.7 GB more.

Two honest limits are written into the same docs. The set is small and synthetic,
so read it as "no regressions", not a benchmark. And only the 16 GB row was
tested: the 8, 24-32 and 48 GB suggestions in the table are sized by memory, not
measured.

## The less glamorous half: a model you can leave running

The guide says the page is meant to sit close to idle, and fit scores are never
urgent. Scoring a backlog flat out with a multi-gigabyte model resident would work
against that, so the code behaves accordingly:

- **Batches with rests.** `scoring.batch` jobs in a row (default 10), then a rest
  of `scoring.rest` minutes (default 10). A new check for jobs, or a new resume,
  starts the next batch at once.
- **A lower priority.** `jobwatch service install` runs the page at nice 10 with
  low-priority disk access, so scoring waits behind whatever you're doing.
- **A model that leaves.** The model lives in a shared local model server that
  loads it when a request arrives and unloads it when idle, not inside jobwatch.
  With nothing left to score, the page runs no scoring thread.
- **Failures aren't retried in a loop.** A job the scorer failed on isn't tried
  again for three days, remembered across restarts, unless the resume, the
  prompts or the model changes. The card shows the error.
- **Scores are never silently redone.** Each score names the model and where it
  ran ("Qwen3.5-9B · local"). After a fallback stood in, or you edit your resume,
  the old score stays, dimmed as "old score", until you ask for a new one.

That last rule exists because a score made again costs again when a paid backend
is in the chain. `jobwatch score --compare 10 --backend claude` re-scores ten
already-scored jobs with another backend, shows each old and new score and the
mean difference, and saves nothing. You can check that two models grade alike
before you let one replace the other.

## What I'd take from it

Write the expected answers before you run the models. Treat a one-in-29 gap as a
tie and pick the smallest model within it. And budget as much effort for being a
polite long-running process as for the model choice, because the model you'll
actually keep is the one you can leave on.

```bash
uv tool install jobwatch
jobwatch ui          # Settings → Where the AI runs, "On this Mac"
```

- **Home page:** [vinayvobbili.github.io/jobwatch](https://vinayvobbili.github.io/jobwatch/)
- **Source:** [github.com/vinayvobbili/jobwatch](https://github.com/vinayvobbili/jobwatch) (the guide is `docs/guide/fit-scores.md`)
- **PyPI:** [pypi.org/project/jobwatch](https://pypi.org/project/jobwatch/)
- **The scorer and its eval:** [github.com/vinayvobbili/shortlist-ai](https://github.com/vinayvobbili/shortlist-ai)
