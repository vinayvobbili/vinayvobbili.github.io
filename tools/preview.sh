#!/usr/bin/env bash
# Build the Jekyll site exactly like GitHub Pages does and serve it locally,
# without installing Ruby on the host.
#
# Why this exists: the repo builds via GitHub Actions, so there's no host
# toolchain. This runs the real `jekyll build` inside a throwaway ruby:3.3
# container with the repo mounted READ-ONLY (so your working tree / Gemfile.lock
# are never touched), copies the repo inside, builds, and drops _site into
# ./.preview (git-ignored). Then it serves it so you can eyeball changes before
# pushing — instead of publishing blind.
#
# Usage:
#   tools/preview.sh                 # build + serve on :8888
#   tools/preview.sh --port 9000     # build + serve on :9000
#   tools/preview.sh --build-only    # build to ./.preview, don't serve
#   tools/preview.sh --no-build      # serve the existing ./.preview as-is
#
# Then screenshot/inspect any path with tools/shot.py, e.g.:
#   python tools/shot.py http://localhost:8888 /posts/some-post/ /attestq/
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO/.preview"
PORT=8888
DO_BUILD=1
DO_SERVE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --build-only) DO_SERVE=0; shift ;;
    --no-build) DO_BUILD=0; shift ;;
    -h|--help) sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$DO_BUILD" == 1 ]]; then
  command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
  echo ">> building site in ruby:3.3 (repo mounted read-only)..."
  mkdir -p "$OUT"
  docker run --rm -v "$REPO":/src:ro -v "$OUT":/out ruby:3.3 bash -lc "
    cp -r /src /work && cd /work && rm -rf _site .jekyll-cache vendor &&
    bundle install --quiet &&
    JEKYLL_ENV=production bundle exec jekyll build --quiet &&
    rm -rf /out/* && cp -r _site/* /out/ &&
    chown -R $(id -u):$(id -g) /out"
  echo ">> built -> $OUT"
fi

if [[ "$DO_SERVE" == 1 ]]; then
  echo ">> serving $OUT at http://localhost:$PORT  (Ctrl-C to stop)"
  cd "$OUT" && exec python3 -m http.server "$PORT"
fi
