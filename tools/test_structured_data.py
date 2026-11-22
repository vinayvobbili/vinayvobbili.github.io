"""Structured data and head tags: BlogPosting has an author and publisher, About has a Person block
with the site's own social links, and no page renders a bare `twitter:site` of "@".

The config tests read the repo; the page tests read a built site and skip when there is none:
    JEKYLL_ENV=production bundle exec jekyll b        # writes _site/
    python -m pytest tools/test_structured_data.py
"""
import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "_site"
CONFIG = yaml.safe_load((ROOT / "_config.yml").read_text())
needs_site = pytest.mark.skipif(not (SITE_DIR / "index.html").is_file(), reason="no _site build")

LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def blocks(html: str) -> list[dict]:
    return [json.loads(m) for m in LD_JSON.findall(html)]


def page(path: str) -> str:
    return (SITE_DIR / path / "index.html").read_text()


def post_pages() -> list[Path]:
    return sorted((SITE_DIR / "posts").glob("*/index.html")) if SITE_DIR.is_dir() else []


# ---- config ------------------------------------------------------------------------------

def test_author_matches_the_social_name_and_the_site_url():
    assert CONFIG["author"]["name"] == CONFIG["social"]["name"]
    assert CONFIG["author"]["url"].startswith(CONFIG["url"] + "/")


def test_there_is_a_logo_for_the_publisher():
    assert (ROOT / CONFIG["logo"].lstrip("/")).is_file()


def test_no_twitter_block_without_a_handle():
    # jekyll-seo-tag prints twitter:site "@" for any `twitter:` key, even one with an empty username
    twitter = CONFIG.get("twitter")
    assert twitter is None or (twitter.get("username") or "").strip(), "empty twitter block renders a bare @"


def test_social_links_include_github_and_linkedin():
    links = CONFIG["social"]["links"]
    assert any("github.com/" in u for u in links) and any("linkedin.com/in/" in u for u in links)


# ---- built pages -------------------------------------------------------------------------

@needs_site
def test_there_are_posts_to_check():
    assert len(post_pages()) >= 10


@needs_site
@pytest.mark.parametrize("path", post_pages(), ids=lambda p: p.parent.name)
def test_every_post_has_a_blogposting_with_author_and_publisher(path):
    posting = [b for b in blocks(path.read_text()) if b.get("@type") == "BlogPosting"]
    assert len(posting) == 1
    author = posting[0]["author"]
    assert author["@type"] == "Person"
    assert author["name"] == CONFIG["social"]["name"]
    assert author["url"] == CONFIG["author"]["url"]
    publisher = posting[0]["publisher"]
    assert publisher["name"] == CONFIG["social"]["name"]
    assert publisher["logo"]["url"].endswith(CONFIG["logo"])


@needs_site
def test_about_page_has_a_person_with_the_configured_links_and_no_email():
    html = page("about")
    people = [b for b in blocks(html) if b.get("@type") == "Person"]
    assert len(people) == 1
    person = people[0]
    assert person["name"] == CONFIG["social"]["name"]
    assert person["sameAs"] == CONFIG["social"]["links"]
    assert person["url"].endswith("/about/")
    assert CONFIG["social"]["email"] not in json.dumps(person)
    assert "@" not in json.dumps(person).replace('"@context"', "").replace('"@type"', "")


@needs_site
def test_no_page_renders_a_bare_twitter_site():
    bad = [str(p.relative_to(SITE_DIR)) for p in SITE_DIR.rglob("*.html")
           if re.search(r'<meta name="twitter:site" content="@?"', p.read_text(errors="ignore"))]
    assert bad == []


@needs_site
def test_the_person_block_is_only_on_the_about_page():
    assert not [b for b in blocks(page("posts/billing-header-kv-cache")) if b.get("@type") == "Person"]
    assert not [b for b in blocks((SITE_DIR / "index.html").read_text()) if b.get("@type") == "Person"]


# ---- built pages: images -----------------------------------------------------------------

@needs_site
@pytest.mark.parametrize("path", post_pages(), ids=lambda p: p.parent.name)
def test_the_post_hero_is_not_lazy_but_the_rest_may_be(path):
    html = path.read_text()
    tag = re.search(r'<a [^>]*class="[^"]*preview-img[^"]*"[^>]*>\s*(<img [^>]*>)', html)
    assert tag, "no hero image in the header"
    assert 'fetchpriority="high"' in tag.group(1)
    assert 'loading="lazy"' not in tag.group(1)


@needs_site
def test_sidebar_avatar_is_the_webp():
    assert re.search(r'<img src="[^"]*/assets/img/avatar\.webp" width="112"', (SITE_DIR / "index.html").read_text())


@needs_site
def test_home_list_serves_webp_thumbnails():
    html = (SITE_DIR / "index.html").read_text()
    imgs = re.findall(r'<img src="([^"]+)"', html.split('id="post-list"', 1)[1])
    assert imgs and all(src.endswith("-hero-640.webp") for src in imgs), imgs
