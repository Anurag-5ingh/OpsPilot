#!/usr/bin/env bash
# Build the GitHub Pages site: the project page at the root and the real
# frontend under app/, running against the in-browser demo backend.
# Usage: demo/build.sh [output-dir]   (default: _site)
set -euo pipefail

cd "$(dirname "$0")/.."
out="${1:-_site}"

rm -rf "$out"
mkdir -p "$out"
cp -R site/. "$out/"
cp -R frontend "$out/app"
cp demo/demo-backend.js "$out/app/demo-backend.js"

# Load the demo backend before the app's own scripts
index="$out/app/index.html"
anchor='<script src="core/constants.js"></script>'
grep -qF "$anchor" "$index" || { echo "build.sh: anchor script tag not found in $index" >&2; exit 1; }
sed "s|$anchor|<script src=\"demo-backend.js\"></script>$anchor|" "$index" > "$index.tmp"
mv "$index.tmp" "$index"
sed 's|<title>[^<]*</title>|<title>OpsPilot Demo</title>|' "$index" > "$index.tmp"
mv "$index.tmp" "$index"

echo "Built $out"
