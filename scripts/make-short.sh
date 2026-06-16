#!/bin/bash
# Convenience wrapper: make a vertical 9:16 Short from a story script.
#
# Usage:
#   scripts/make-short.sh stories/sample.txt
#   scripts/make-short.sh stories/sample.txt "rain,city,night"   # b-roll keywords
#
# For long-form (16:9) use make_video.py directly:
#   python3 scripts/make_video.py --script stories/sample.txt --format long
set -euo pipefail
cd "$(dirname "$0")/.."

SCRIPT="${1:-stories/sample.txt}"
KEYWORDS="${2:-}"

exec python3 scripts/make_video.py --script "$SCRIPT" --format shorts --keywords "$KEYWORDS"
