---
title: "Rules a Job-Board Watcher Can't Configure Away"
image:
  path: /assets/img/posts/watcher-that-never-applies-hero.png
  alt: "Public board feeds pass through rules that live in code, an honest User-Agent, robots.txt and no LinkedIn or Indeed pages, into a ranked digest that you review and submit yourself"
description: "jobwatch reads only public board JSON, treats an unreadable robots.txt as a no, skips LinkedIn and Indeed, never applies, and keeps its rules in code."
date: 2026-11-15 08:00:00 -0500
categories: [Open Source, Python]
tags: [jobwatch, robots-txt, web-scraping, mcp, open-source, python, job-boards, human-in-the-loop]
accent: steel
---

## TL;DR

Most tools in this space are built around one idea: **automate the application.**
Scrape every board, fill every form, submit at scale. I think that's the wrong
design, for the people using it and for the sites being read.

[**jobwatch**](https://vinayvobbili.github.io/jobwatch/) is the other design. It
watches the boards of the companies you list, ranks what's new, optionally
fit-scores it against your resume, and tracks where each application stands. It
**never applies for you**: you review and submit every application. And its rules
about *how* it reads the web aren't options. They're code paths with tests pinned
to them.

<div class="tldr-cards">
<div class="tldr-card"><span class="tldr-num">21</span><span class="tldr-sub">source types in the registry: hosted job boards, careers sites, Hacker News, VC portfolio boards</span></div>
<div class="tldr-card"><span class="tldr-num">1</span><span class="tldr-sub">User-Agent string, honest, defined once</span></div>
<div class="tldr-card"><span class="tldr-num">0</span><span class="tldr-sub">applications submitted by the tool, by design</span></div>
</div>

It's on [PyPI](https://pypi.org/project/jobwatch/), in the official MCP Registry
as `io.github.vinayvobbili/jobwatch`, and MIT licensed, with a command line, a local
web page (`jobwatch ui`) and an MCP server.

## Companies already publish this

Most applicant-tracking systems publish a company's open roles as JSON without an
API key, because that is what the careers page is built on. For a fictional
company with the board slug `initech`, one GET returns every open role on
Greenhouse:

```
https://boards-api.greenhouse.io/v1/boards/initech/jobs?content=true
```

`sources.py` registers Greenhouse, Lever, Ashby and Workable that way, as URL
templates. For Workday, Eightfold and the other big-company platforms it reads
the endpoints the careers page itself calls. A role shows up when the company
posts it, not when an aggregator gets around to it.

## Rule 1: introduce yourself honestly

Requests to job boards carry one User-Agent, defined once in `sources.py`:

```python
USER_AGENT = f"jobwatch/{__version__} (+https://github.com/vinayvobbili/jobwatch)"
```

No browser string, no rotation. A site operator who sees jobwatch in their logs can
tell what it is, which version, and where to read its source. A test in
`tests/test_hosted.py` asserts the header actually sent is `sources.USER_AGENT` and
starts with `jobwatch/`. Swapping in something friendlier-looking means a red build.

## Rule 2: if the site says no, the answer is no

Where jobwatch reads anything beyond a board's own feed (a link from a job-alert
email, an Avature portal, a careers site found through its sitemap, Levels.fyi pay
pages), it asks robots.txt first. `alerts.py` has a small RFC 9309 implementation:
the group naming `jobwatch` wins if there is one, otherwise `User-agent: *`; the
longest matching pattern decides; a tie goes to Allow.

The part I care about is the failure mode:

```python
class Robots:
    """Each site's robots.txt, read once. No robots.txt (404) allows everything; one that can't be read (an
    error, a refusal) allows nothing."""
```

A missing file means allowed. A file that errors, or a server that refuses to
serve it, means **not allowed**. When the tool can't tell, it doesn't read. The
test says so in three lines:

```python
assert not robots.allowed("https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/1")
assert robots.allowed("https://none.example.com/job/1")       # no robots.txt: allowed
assert not robots.allowed("https://broken.example.com/job/1")  # can't tell: not read
```

The same stance shows up elsewhere. SmartRecruiters' posting API host is closed to
crawlers by its robots.txt, so jobwatch reads the company's public careers site
instead. On Avature portals the code refuses any link carrying `qtvc=`, which
robots.txt rules out, before a request goes out.

## Rule 3: some sites are simply not read

LinkedIn's robots.txt disallows every page, job postings included. The module that
handles LinkedIn links opens with that fact and draws the consequence: *jobwatch
never reads linkedin.com.* From a LinkedIn link it takes only the numeric posting
id. Company and title come from the person, or from a job-alert email they already
received, and the tool then looks for the same job on the company's own board,
which is where the application goes anyway. Indeed is on the same never-read list.

The rule is enforced, not just stated. `tests/test_linkedin.py` swaps in a fetcher
that fails the test on any request to linkedin.com:

```python
def no_linkedin(fallback):
    """A fetcher that fails the test on any linkedin.com URL, else answers with `fallback`."""
    def fetch(url, *args, **kwargs):
        assert "linkedin.com" not in url, f"jobwatch fetched {url}"
        return fallback(url, *args, **kwargs)
    return fetch
```

Another test asserts the module has no `read` function at all. If someone adds
one, the suite explains why that's not how this project works.

## Rule 4: ask less often than you could

On Greenhouse, Lever, Ashby and Workable it's one request per company per run. A
Workday, Eightfold or Oracle board can list thousands of roles, so jobwatch
searches for the words in your title filters and reads a posting in full only when
its title passes. Eightfold is read one request at a time, with a pause between,
because its pages hold ten roles and parallel requests drew HTTP 429s. A board that
answers 429 or 503 is asked again after a pause: `Retry-After` when the server
sends one, otherwise 2, 4, 8 seconds and on, capped at 30, up to five retries.

## Why "never applies" is the feature

The README gives practical reasons against auto-applying: recruiters recognize mass
applications, some companies cap how many roles one person can apply to, and forms
ask legal questions (work authorization, export control, signatures) that a person
has to answer. So jobwatch finds, ranks and tracks, and stops there. The same
boundary is in the MCP server's instructions, which every connected assistant
reads: *"jobwatch never applies to anything by itself: the person reviews and
submits every application."*

## What I'd take from it

Plenty of tools say they respect robots.txt. The difference is whether that
sentence is a promise or a property of the code: a header defined once, a robots
parser that fails closed, a LinkedIn module with nothing in it to misuse, and
tests that go red the moment any of that drifts. At 0.12.0 the suite collects 2,396
tests, run against canned board responses.

If you're building anything that reads other people's sites, I'd steal the
pattern: **make the careful behavior the only behavior, then write the test that
proves it.**

```bash
uv tool install jobwatch
jobwatch ui
```

- **Home page:** [vinayvobbili.github.io/jobwatch](https://vinayvobbili.github.io/jobwatch/)
- **Source:** [github.com/vinayvobbili/jobwatch](https://github.com/vinayvobbili/jobwatch)
- **PyPI:** [pypi.org/project/jobwatch](https://pypi.org/project/jobwatch/)
