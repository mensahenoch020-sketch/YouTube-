#!/bin/bash
# Persist your Higgsfield login across sessions.
#
# The cloud container is wiped between sessions, so the credentials written by
# `higgsfield auth login` disappear. Run this once AFTER logging in: it prints
# the credentials JSON so you can save it as an environment secret named
# HIGGSFIELD_CREDENTIALS_JSON in your Claude Code on the web environment
# settings. The session-start hook then restores it automatically every time.
set -euo pipefail

CRED_FILE="${HIGGSFIELD_CREDENTIALS_PATH:-${XDG_CONFIG_HOME:-$HOME/.config}/higgsfield/credentials.json}"

if [ ! -f "$CRED_FILE" ]; then
  echo "No credentials found at: $CRED_FILE" >&2
  echo "Run 'higgsfield auth login' first (open the printed URL on your phone)." >&2
  exit 1
fi

echo "Copy the single line below and save it as an environment secret named:"
echo
echo "    HIGGSFIELD_CREDENTIALS_JSON"
echo
echo "--------------------------------------------------------------------------"
# Print as one compact line so it pastes cleanly into a secret field.
tr -d '\n' < "$CRED_FILE"
echo
echo "--------------------------------------------------------------------------"
echo
echo "Do NOT commit this value. Once saved, future sessions auto-authenticate."
