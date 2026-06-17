#!/usr/bin/env bash
# Pushes local memory changes to GitHub after a Write or Edit tool call.
# Called by the PostToolUse hook in hooks/hooks.json.
# Only stages .md files so plugin/script changes don't leak into memory commits.

set -euo pipefail

REPO="$HOME/.agents/agent-memory"

if [[ ! -d "$REPO/.git" ]]; then
  echo "[memory-push] SKIP: repo not found at $REPO" >&2
  exit 0
fi

cd "$REPO"
git add -- *.md 2>/dev/null || true

if git diff --cached --quiet; then
  exit 0
fi

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
CHANGED=$(git diff --cached --name-only | head -3 | xargs -n1 basename | paste -sd, -)
git commit -m "memory: $CHANGED @ $TIMESTAMP" 2>&1 \
  || { echo "[memory-push] WARNING: commit failed" >&2; exit 0; }
git push origin main 2>&1 \
  || echo "[memory-push] WARNING: push failed — local write preserved, will sync next session" >&2
