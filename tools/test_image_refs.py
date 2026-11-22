"""Every image a post or page points at exists, and no image in assets/img/posts is left unreferenced.

Run: python -m pytest tools/test_image_refs.py
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://vinayvobbili.github.io"
POSTS_IMG = ROOT / "assets" / "img" / "posts"
POSTS = sorted((ROOT / "_posts").glob("*.md"))
# Standalone pages: html files outside the Jekyll folders and the vendored libraries.
PAGES = sorted(p for p in ROOT.glob("*/index.html") if p.parent.name not in {"assets", "_site"})


def tracked_text() -> dict[str, str]:
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True,
                           check=True).stdout.split("\n")
    out = {}
    for name in files:
        path = ROOT / name
        if name and path.is_file() and path.suffix in {".md", ".html", ".yml", ".py", ".scss", ".css", ".js", ".json"}:
            if not name.startswith("assets/lib/"):
                out[name] = path.read_text(errors="ignore")
    return out


def local_file(url: str) -> Path:
    """The repo file a site URL or site-relative path refers to."""
    path = url.removeprefix(SITE).split("?")[0].lstrip("/")
    return ROOT / path


def post_image_paths(post: Path) -> list[str]:
    return re.findall(r"^  path: (\S+)$", post.read_text(), re.M)


@pytest.mark.parametrize("post", POSTS, ids=lambda p: p.name)
def test_every_post_front_matter_image_exists(post):
    paths = post_image_paths(post)
    assert paths, f"{post.name} has no image.path"
    for p in paths:
        assert local_file(p).is_file(), f"{post.name}: {p} is missing"


@pytest.mark.parametrize("post", POSTS, ids=lambda p: p.name)
def test_every_image_a_post_body_embeds_exists(post):
    for url in re.findall(r"\]\((/assets/img/[^)\s]+)\)", post.read_text()):
        assert local_file(url).is_file(), f"{post.name}: {url} is missing"


def test_there_are_standalone_pages_to_check():
    assert ROOT / "witness" / "index.html" in PAGES


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_social_image_of_a_page_exists(page):
    tags = re.findall(r'<meta (?:property|name)="(?:og|twitter):image" content="([^"]+)"', page.read_text())
    assert tags, f"{page.name} sets no og:image"
    for url in tags:
        assert url.startswith(SITE + "/"), url
        assert local_file(url).is_file(), f"{page.relative_to(ROOT)}: {url} is missing"


def test_no_image_in_assets_img_posts_is_unreferenced():
    texts = tracked_text()
    orphans = []
    for img in sorted(p for p in POSTS_IMG.iterdir() if p.is_file()):
        if not any(img.name in text for name, text in texts.items() if name != str(img.relative_to(ROOT))):
            orphans.append(img.name)
    assert orphans == [], f"unreferenced images (delete them or use them): {orphans}"
