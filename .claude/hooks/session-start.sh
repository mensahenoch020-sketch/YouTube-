#!/bin/bash
# SessionStart hook: prepares each (ephemeral) Claude Code on the web session
# for Higgsfield video generation.
#
# It runs every time a session starts because the cloud container is wiped
# between sessions, so a one-time `npm install` would not survive. This makes
# the Higgsfield CLI + skills available on every session automatically.
set -euo pipefail

# Only do work in the remote (Claude Code on the web) environment. Locally this
# is a no-op so it doesn't interfere with a normal machine.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

log() { echo "[higgsfield-setup] $*"; }

# 1. Install the official Higgsfield CLI globally (idempotent: npm skips if the
#    same version is already present).
if ! command -v higgsfield >/dev/null 2>&1; then
  log "Installing @higgsfield/cli ..."
  npm install -g @higgsfield/cli >/dev/null 2>&1 || {
    log "WARNING: npm install of @higgsfield/cli failed (network policy?). See README."
  }
else
  log "@higgsfield/cli already installed ($(higgsfield --version 2>/dev/null | head -1))."
fi

# 2. Higgsfield Claude Code skills (adds /higgsfield:*).
#    These are committed to the repo under .agents/skills, so normally nothing
#    to do. Only fetch if they're somehow missing. Best-effort, never blocks.
if [ ! -d "${CLAUDE_PROJECT_DIR:-.}/.agents/skills/higgsfield-generate" ] \
     && command -v npx >/dev/null 2>&1; then
  log "Skills missing; fetching higgsfield-ai/skills ..."
  npx --yes skills add higgsfield-ai/skills >/dev/null 2>&1 \
    || log "Note: could not fetch skills this session (continuing)."
fi

# 3. Restore authentication so you don't have to log in every session.
#    Set a session/environment secret named HIGGSFIELD_CREDENTIALS_JSON to the
#    contents of your credentials file (see scripts/save-auth.sh). The CLI's
#    refresh token keeps it valid over time.
CRED_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/higgsfield"
CRED_FILE="$CRED_DIR/credentials.json"
if [ -n "${HIGGSFIELD_CREDENTIALS_JSON:-}" ]; then
  mkdir -p "$CRED_DIR"
  printf '%s' "$HIGGSFIELD_CREDENTIALS_JSON" > "$CRED_FILE"
  chmod 600 "$CRED_FILE"
  log "Restored saved credentials -> $CRED_FILE"
fi

# 4. Report auth status so the agent/user knows whether a login is needed.
if command -v higgsfield >/dev/null 2>&1; then
  if higgsfield auth token >/dev/null 2>&1; then
    log "Authenticated and ready. Try: scripts/generate-video.sh \"your prompt\""
  else
    log "NOT authenticated. Run 'higgsfield auth login' and open the printed URL"
    log "on your phone, then run scripts/save-auth.sh to persist it for next time."
  fi
fi

exit 0
