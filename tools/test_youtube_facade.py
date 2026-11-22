"""The click-to-play video include (_includes/youtube-facade.html): nothing from YouTube loads before the
click, the only host the script may open is youtube-nocookie, and every post that uses it ships a
real, in-budget thumbnail.

The source and post tests read the repo. The render tests build a one-page stub site with the `jekyll`
on PATH (or $JEKYLL) and skip without one; the page tests read a built site and skip when there is none:
    JEKYLL_ENV=production bundle exec jekyll b        # writes _site/
    python -m pytest tools/test_youtube_facade.py
"""
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from functools import partial
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimize_images as oi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ROOT / "_includes" / "youtube-facade.html"
SCSS = (ROOT / "assets" / "css" / "jekyll-theme-chirpy.scss").read_text()
SITE_DIR = ROOT / "_site"
POSTS = sorted((ROOT / "_posts").glob("*.md"))
EMBED_HOST = "www.youtube-nocookie.com"
JEKYLL = os.environ.get("JEKYLL") or shutil.which("jekyll")
needs_jekyll = pytest.mark.skipif(not JEKYLL, reason="no jekyll on PATH")
needs_site = pytest.mark.skipif(not (SITE_DIR / "index.html").is_file(), reason="no _site build")

TITLE = 'Free labels, +41% MRR@10: "fine-tuning" a reranker'
PARAMS = ('id="abc123XYZ_-" title=\'{title}\' thumb="/assets/img/posts/x-video-thumb.webp" length="3:01" '
          'chapters="0:00 The problem|0:34 What I did|1:16 The result|2:21 How I work" '
          'description="A one-line summary." upload_date="2026-11-21" duration="PT3M1S"')
LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


# ---- the include's source ---------------------------------------------------------------

def test_the_include_has_no_iframe_tag_and_no_script_src():
    # the iframe exists only as a createElement call, so none can load before the click
    src = INCLUDE.read_text()
    assert "<iframe" not in src
    assert not re.search(r"<script[^>]*\ssrc=", src)
    assert "<link" not in src and "<img" not in src


def test_the_only_hosts_the_include_names_are_nocookie_youtu_be_and_schema_org():
    code = re.sub(r"\{%-?\s*comment\s*-?%\}.*?\{%-?\s*endcomment\s*-?%\}", "", INCLUDE.read_text(), flags=re.S)
    hosts = set(re.findall(r"https?://([^/'\"\s?{]+)", code))
    assert hosts == {EMBED_HOST, "youtu.be", "schema.org"}


def test_the_embed_asks_for_the_documented_iframe_permissions():
    src = INCLUDE.read_text()
    assert f"https://{EMBED_HOST}/embed/" in src
    assert "autoplay=1&rel=0" in src
    assert "accelerometer; autoplay; encrypted-media; picture-in-picture" in src
    assert "allowFullscreen=true" in src
    assert "referrerPolicy='strict-origin-when-cross-origin'" in src
    assert "loading='lazy'" in src


def test_the_site_sets_no_content_security_policy_the_embed_would_have_to_fit():
    # no CSP anywhere in the config or head includes; if one is added it must allow
    # frame-src https://www.youtube-nocookie.com
    for path in [ROOT / "_config.yml", *(ROOT / "_includes").glob("*.html"), *(ROOT / "_layouts").glob("*.html")]:
        text = path.read_text()
        if re.search(r"content-security-policy", text, re.I):
            assert EMBED_HOST in text, f"{path.name} sets a CSP without {EMBED_HOST}"


def test_styles_cover_focus_dark_theme_variables_and_reduced_motion():
    block = SCSS[SCSS.index(".yt-facade"):]
    assert ":focus-visible" in block
    assert "prefers-reduced-motion: reduce" in block
    assert "aspect-ratio: 16 / 9" in block
    assert "var(--card-bg)" in block and "var(--text-color)" in block  # follow Chirpy's light and dark palettes
    assert "$brand-grad" in block


# ---- the posts that use it ---------------------------------------------------------------

def uses() -> list[tuple[Path, dict[str, str]]]:
    found = []
    for post in POSTS:
        for tag in re.findall(r"\{%\s*include youtube-facade\.html(.*?)%\}", post.read_text(), re.S):
            found.append((post, dict(re.findall(r'(\w+)="([^"]*)"', tag))))
    return found


def test_a_post_uses_the_facade():
    assert uses()


@pytest.mark.parametrize("post,params", uses(), ids=lambda v: v.name if isinstance(v, Path) else "")
def test_every_use_has_its_required_params_and_a_real_thumbnail(post, params):
    for key in ("id", "title", "thumb"):
        assert params.get(key), f"{post.name}: {key} is missing"
    assert re.fullmatch(r"[\w-]{11}", params["id"])
    thumb = ROOT / params["thumb"].lstrip("/")
    assert thumb.is_file(), f"{post.name}: {params['thumb']} is missing"
    assert thumb.name.endswith("-video-thumb.webp")
    assert thumb.stat().st_size <= oi.VIDEO_THUMB_BUDGET
    width, height = Image.open(thumb).size
    assert (width, height) == (oi.VIDEO_THUMB_WIDTH, oi.VIDEO_THUMB_WIDTH * 9 // 16)


@pytest.mark.parametrize("post,params", uses(), ids=lambda v: v.name if isinstance(v, Path) else "")
def test_chapters_are_timestamped_labels_in_order(post, params):
    seconds = []
    for chapter in params.get("chapters", "").split("|"):
        m = re.fullmatch(r"(\d+):([0-5]\d) (\S.*)", chapter)
        assert m, f"{post.name}: bad chapter {chapter!r}"
        seconds.append(int(m[1]) * 60 + int(m[2]))
    assert seconds == sorted(seconds)


def test_the_video_thumb_helper_names_and_budgets_files():
    assert oi.video_thumb_path("demo") == oi.POSTS_IMG / "demo-video-thumb.webp"
    assert oi.VIDEO_THUMB_BUDGET <= 60_000


@pytest.mark.skipif(not shutil.which("cwebp"), reason="cwebp not installed")
def test_video_thumb_command_writes_a_960px_webp(tmp_path, monkeypatch):
    src = tmp_path / "t.png"
    Image.new("RGB", (1280, 720), (10, 120, 160)).save(src)
    monkeypatch.setattr(oi, "POSTS_IMG", tmp_path)
    assert oi.main(["--video-thumb", str(src), "demo"]) == 0
    assert Image.open(tmp_path / "demo-video-thumb.webp").size == (960, 540)


# ---- rendering ---------------------------------------------------------------------------

def render(tmp_path: Path, pages: dict[str, str], baseurl: str = "") -> Path:
    """Build a stub site holding only the include and the given pages; return its _site."""
    site = tmp_path / "stub"
    (site / "_includes").mkdir(parents=True)
    shutil.copy(INCLUDE, site / "_includes" / INCLUDE.name)
    (site / "_config.yml").write_text(f'url: "https://example.test"\nbaseurl: "{baseurl}"\n')
    for name, body in pages.items():
        (site / name).write_text(f"---\n---\n{body}\n")
    subprocess.run([JEKYLL, "build", "-q", "-s", str(site), "-d", str(site / "_site")], check=True,
                   capture_output=True, cwd=site)
    return site / "_site"


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("facade")
    full = "{% include youtube-facade.html " + PARAMS.format(title=TITLE.replace("'", "")) + " %}"
    pages = {
        "full.md": full,
        "bare.md": "{% include youtube-facade.html id=\"abc123XYZ_-\" title=\"T\" thumb=\"/t.webp\" %}",
        "none.md": "{% include youtube-facade.html %}",
        "nothumb.md": "{% include youtube-facade.html id=\"abc123XYZ_-\" title=\"T\" %}",
    }
    return {"site": render(tmp, pages), "based": render(tmp / "b", {"full.md": full}, baseurl="/blog")}


def html(rendered, name: str, key: str = "site") -> str:
    return (rendered[key] / f"{name}.html").read_text()


@needs_jekyll
def test_with_params_it_renders_a_link_over_a_self_hosted_thumbnail_and_nothing_loads(rendered):
    page = html(rendered, "full")
    assert page.count('class="yt-facade"') == 1
    assert "<iframe" not in page and "<img" not in page
    assert not re.search(r"<script[^>]*\ssrc=", page) and "<link" not in page
    assert 'href="https://youtu.be/abc123XYZ_-"' in page
    assert "--yt-thumb: url('/assets/img/posts/x-video-thumb.webp')" in page
    assert "ytimg" not in page and "youtube.com" not in page
    # every absolute URL in the markup (the script's embed host aside) is the watch link or schema.org
    markup = re.sub(r"<script>.*?</script>", "", page, flags=re.S)
    assert set(re.findall(r"https?://([^/'\"\s?]+)", markup)) <= {"youtu.be", "schema.org", "www.youtube-nocookie.com",
                                                                  "example.test"}


@needs_jekyll
def test_the_link_is_labelled_for_screen_readers_and_the_title_is_escaped(rendered):
    page = html(rendered, "full")
    assert 'aria-label="Play video: Free labels, +41% MRR@10: &quot;fine-tuning&quot; a reranker"' in page
    assert 'data-yt-title="Free labels, +41% MRR@10: &quot;fine-tuning&quot; a reranker"' in page
    assert '3:01</span>' in page


@needs_jekyll
def test_chapters_become_links_at_their_second(rendered):
    page = html(rendered, "full")
    for stamp, label, seconds in [("0:00", "The problem", 0), ("0:34", "What I did", 34),
                                  ("1:16", "The result", 76), ("2:21", "How I work", 141)]:
        assert f'href="https://youtu.be/abc123XYZ_-?t={seconds}" data-yt-start="{seconds}"' in page
        assert f'>{stamp}</span> {label}</a>' in page


@needs_jekyll
def test_the_script_opens_only_the_nocookie_embed(rendered):
    script = re.search(r"<script>(.*?)</script>", html(rendered, "full"), re.S)[1]
    assert set(re.findall(r"https?://([^/'\"\s?]+)", script)) == {EMBED_HOST}
    assert "document.createElement('iframe')" in script


@needs_jekyll
def test_video_object_has_the_fields_search_engines_need_and_no_content_url(rendered):
    blocks = [json.loads(b) for b in LD_JSON.findall(html(rendered, "full"))]
    assert len(blocks) == 1
    video = blocks[0]
    assert video["@type"] == "VideoObject"
    assert video["name"] == TITLE.replace("'", "")
    assert video["uploadDate"] == "2026-11-21" and video["duration"] == "PT3M1S"
    assert video["thumbnailUrl"] == "https://example.test/assets/img/posts/x-video-thumb.webp"
    assert video["embedUrl"] == f"https://{EMBED_HOST}/embed/abc123XYZ_-"
    assert "contentUrl" not in video


@needs_jekyll
def test_without_the_optional_params_there_are_no_chapters_and_no_structured_data(rendered):
    page = html(rendered, "bare")
    assert "yt-facade__caption" not in page and "yt-facade__length" not in page
    assert "application/ld+json" not in page
    assert "yt-facade__play" in page


@needs_jekyll
@pytest.mark.parametrize("name", ["none", "nothumb"])
def test_without_the_required_params_nothing_renders(rendered, name):
    assert "yt-facade" not in html(rendered, name)


@needs_jekyll
def test_the_thumbnail_url_honours_the_baseurl(rendered):
    assert "url('/blog/assets/img/posts/x-video-thumb.webp')" in html(rendered, "full", "based")


# ---- the built post ----------------------------------------------------------------------

POST = SITE_DIR / "posts" / "three-phases-of-rag-quality" / "index.html"


@needs_site
def test_the_built_post_has_the_facade_with_no_iframe_and_no_youtube_script():
    page = POST.read_text()
    assert page.count('class="yt-facade"') == 1
    assert "<iframe" not in page
    # the theme's own scripts (jsDelivr, GoatCounter) are not the facade's business
    sources = re.findall(r'<script[^>]*\ssrc="([^"]+)"', page)
    assert not [s for s in sources if re.search(r"youtu|ytimg|google|gstatic", s)]
    types = sorted(b["@type"] for b in map(json.loads, LD_JSON.findall(page)))
    assert types == ["BlogPosting", "VideoObject"]


@needs_site
def test_the_facade_sits_under_the_first_animated_flow_before_the_setup_section():
    page = POST.read_text()
    flow = page.index("reranker-mined-pairs-flow.svg")
    assert flow < page.index("Prefer to watch?") < page.index('class="yt-facade"') < page.index("The setup:")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@needs_site
def test_a_click_swaps_the_thumbnail_for_a_nocookie_iframe_in_both_themes():
    pytest.importorskip("playwright.sync_api")
    import facade_check

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(SITE_DIR)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        problems = facade_check.check(f"http://127.0.0.1:{server.server_port}", "/posts/three-phases-of-rag-quality/")
    except Exception as exc:  # no browser installed
        if "Executable doesn't exist" in str(exc):
            pytest.skip("no Playwright browser")
        raise
    finally:
        server.shutdown()
    assert problems == []
