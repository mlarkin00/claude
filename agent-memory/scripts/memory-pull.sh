#!/usr/bin/env bash
# Pulls the latest memory state from GitHub. Remote always wins.
# Called by the SessionStart hook wired into ~/.claude/settings.json by bootstrap-memory.
# The fetch runs over HTTPS authenticated by the gh CLI token (`gh auth setup-git`,
# configured during bootstrap) — no SSH key required.

set -euo pipefail

REPO="$HOME/.agents/agent-memory"

if [[ ! -d "$REPO/.git" ]]; then
  echo "[memory-pull] SKIP: repo not found at $REPO" >&2
  exit 0
fi

cd "$REPO"
git fetch origin 2>&1 || { echo "[memory-pull] WARNING: fetch failed" >&2; exit 0; }
git reset --hard origin/main 2>&1 || { echo "[memory-pull] WARNING: reset failed" >&2; exit 0; }
