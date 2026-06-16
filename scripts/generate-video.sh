#!/bin/bash
# Generate a video with Higgsfield from a single prompt.
#
# Usage:
#   scripts/generate-video.sh "a slow push through a neon city at night"
#   scripts/generate-video.sh "..." --model kling3_0 --aspect-ratio 16:9
#   scripts/generate-video.sh "..." --duration 5 --mode pro --sound off
#
# Defaults are tuned for YouTube Shorts (vertical 9:16). Any extra flags after
# the prompt are passed straight through to `higgsfield generate create`, so you
# can set model-specific params. Discover models and their params with:
#   higgsfield model list --video
#   higgsfield model get <model>
set -euo pipefail

# Defaults (override via flags or env vars).
MODEL="${HIGGSFIELD_VIDEO_MODEL:-kling3_0}"
ASPECT="${HIGGSFIELD_ASPECT:-9:16}"

if [ $# -eq 0 ]; then
  echo "Usage: scripts/generate-video.sh \"<prompt>\" [--model M] [extra flags...]" >&2
  exit 1
fi

PROMPT="$1"; shift

# Allow overriding the model with a leading --model flag; collect the rest as
# passthrough flags for the underlying CLI.
PASSTHROUGH=()
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    *) PASSTHROUGH+=("$1"); shift ;;
  esac
done

if ! command -v higgsfield >/dev/null 2>&1; then
  echo "higgsfield CLI not found. The session-start hook installs it; on a fresh" >&2
  echo "session wait for setup, or run: npm install -g @higgsfield/cli" >&2
  exit 1
fi

if ! higgsfield auth token >/dev/null 2>&1; then
  echo "Not authenticated. Run 'higgsfield auth login' (open the URL on your phone)," >&2
  echo "then 'scripts/save-auth.sh' to persist it. See README.md." >&2
  exit 1
fi

echo "Generating video:  model=$MODEL  aspect=$ASPECT"
echo "Prompt: $PROMPT"
echo

# --wait blocks until the job finishes and prints the result URL(s).
higgsfield generate create "$MODEL" \
  --prompt "$PROMPT" \
  --aspect-ratio "$ASPECT" \
  --wait \
  "${PASSTHROUGH[@]}"
