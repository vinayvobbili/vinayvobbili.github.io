---
title: "A Product Video You Can Rebuild with One Command"
image:
  path: /assets/img/posts/slidecast-hero.png
  alt: "slidecast — HTML slides, recorded clips and a script in, a narrated MP4 out"
description: >-
  Screen recordings go stale when the UI changes, and re-recording one by hand is
  tedious. slidecast turns slides, recorded clips and a narration script into
  a narrated MP4, with a drivable recorder that moves a visible cursor and fails
  the build when the frame slices a button in half. The 1.5-minute jobwatch tour is
  built with it, on made-up data, and rebuilt with one command when the UI moves.
date: 2026-11-15 10:00:00 -0500
categories: [Open Source, Python]
tags: [slidecast, video, text-to-speech, kokoro, playwright, ffmpeg, mlx, open-source, python, demo]
accent: coral
---

## TL;DR

A demo video is a document that nobody keeps up to date, because updating it means
re-recording it. [**slidecast**](https://github.com/vinayvobbili/slidecast) treats
the video as a build. You bring HTML slides, optional recorded clips and the
words; it screenshots each slide with a headless browser, speaks the narration
with a pluggable text-to-speech voice, and stitches the result into one MP4 with
ffmpeg. Change a sentence or a screen, run the build again, get a new video.

<div class="tldr-cards">
<div class="tldr-card"><span class="tldr-num">1 script</span><span class="tldr-sub">slides, clips and narration in, one MP4 out</span></div>
<div class="tldr-card"><span class="tldr-num">0 servers</span><span class="tldr-sub">Kokoro runs in-process on Apple Silicon with the <code>mlx</code> extra</span></div>
<div class="tldr-card"><span class="tldr-num">5 voice providers</span><span class="tldr-sub">Kokoro server, Kokoro in-process, gTTS, macOS <code>say</code>, or silence</span></div>
</div>

It's on [PyPI](https://pypi.org/project/slidecast/) and at
[github.com/vinayvobbili/slidecast](https://github.com/vinayvobbili/slidecast).

## What it is, in a few lines

```python
from slidecast import Reel, MLXKokoroTTS

reel = Reel(width=1280, height=720, tts=MLXKokoroTTS(voice="af_heart"))
reel.add("<!doctype html><h1>Hello</h1>", "Hello, and welcome.")
reel.add_clip("scan.webm", "Click Scan, and every question gets a cited draft.")
reel.render("out.mp4", make_poster=True)
```

A slide is any HTML you like: slidecast has no opinion about how it looks. Each
slide is padded to fit its narration exactly when the voice reports a duration. A
recorded clip plays through, and if the narration runs longer, its last frame holds
until the voice finishes; the clip is letterboxed, never stretched. Every piece is
swappable: the voice (anything with `synthesize(text, path)`), the renderer, and
the ffmpeg steps, which take an injectable runner so the command lines can be
tested without running ffmpeg.

## How the jobwatch tour is built

The 1.5-minute tour on [jobwatch](https://vinayvobbili.github.io/jobwatch/)'s home
page is built with slidecast. It's a screen recording of the real `jobwatch ui`,
running on a seeded demo of invented companies (Acme, Globex, Initech, Umbrella,
Hooli). Nothing reads a real watchlist, reaches a job board or calls a model. One
command, `scripts/videos/make-videos`, records and renders it (Kokoro narration
needs Apple Silicon), and `--dry` takes a screenshot after each action to check
framing without making a video.

The story has a fixed shape, which slidecast ships as defaults:

1. A silent three-second title card.
2. The problem, as an animated scene, before the solution.
3. A tagline at the turn from one to the other.
4. The walkthrough, each clip held as long as its narration.
5. The title card again, with the tagline. Never a fade to black.

The "problem" scene is a page of CSS animation. `add_animated` pauses every
animation and steps it frame by frame through the Web Animations API, so the same
page renders identically on every run. A timer-driven script wouldn't, which is why
the animation has to start from CSS.

## The recorder that behaves like a person

The part I like best is `slidecast.recorder.Recorder`. It drives a Playwright page
and shows what a viewer needs: a cursor that glides to each target before it acts,
a ripple on every click, a dotted path for a drag. The overlay is injected into the
page, so it's in the recording and nowhere else.

```python
with Recorder.open(browser, "http://127.0.0.1:8765/#settings", "settings.mp4") as rec:
    rec.click("text=Save settings")      # glide, ripple, click
    rec.type("#name", "Jordan")
    rec.hold_until(8.0)                  # a scene as long as its narration
```

After every action it runs a framing check, `find_clipped(page)`, and raises
`ClippedError` if the edge of the frame slices a visible element in two: a sticky
tab bar cut off after a scroll, a button, an input, a heading. A bad take fails the
build instead of reaching the video, which is the reason a rebuild is safe to run
unattended.

## Checks, captions and a cache

- **`slidecast check out.mp4`** fails if the last half second has black frames, or
  if the first card runs over four seconds before any voice. A reel with a title
  card runs the same check at the end of `render`.
- **Pronunciation is data, not editing.** Kokoro says "PDFs" right when it's written
  as one word but spells out "P D Fs", so slidecast joins a spelled-out plural back
  into its word before speaking it. A `pronunciations` dictionary covers words the
  voice still gets wrong, and the on-screen captions keep what you wrote.
- **A cache.** Narration and built segments are keyed on the text, voice, settings
  and the slide's screenshot, so after editing two slides of a long reel only those
  two are spoken and encoded again.
- **Captions.** jobwatch's build writes a WebVTT file for each video from the
  narration and the length of each rendered segment, spread a sentence at a time
  over the spoken line, at most 80 characters a cue. That lives in jobwatch's
  `scripts/videos/captions.py`, not in slidecast itself.
- **An upload copy.** `slidecast youtube out.mp4` writes a 2x copy (2560x1600 from a
  1280x800 reel) because YouTube re-encodes everything, and a 1280x800 file lands
  in its softer 720p tier. It's Lanczos scaling, so it can't add detail the slides
  don't have; for the sharpest text, design at 2x.

## What I'd take from it

The lesson wasn't about video. It was that a demo you can't regenerate is already
out of date, and that the checks that matter are the boring ones: the frame cuts
nothing in half, the video doesn't end on black, the voice isn't cut off by the
next slide (`slidecast check --min-gap`). Put them in the build and nobody has to watch the video to know.

```bash
pip install 'slidecast[mlx,playwright,yaml]'
playwright install chromium
slidecast render reel.yaml -o out.mp4 --poster
```

You also need ffmpeg on the `PATH`, or the `slidecast[ffmpeg]` extra's bundled binary.

- **Source:** [github.com/vinayvobbili/slidecast](https://github.com/vinayvobbili/slidecast)
- **PyPI:** [pypi.org/project/slidecast](https://pypi.org/project/slidecast/)
- **Used by:** [jobwatch](https://vinayvobbili.github.io/jobwatch/), whose tour and tutorials are built this way
