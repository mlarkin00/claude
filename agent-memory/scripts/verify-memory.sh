#!/usr/bin/env bash
# Health check for the agent memory system.
# Tier 2 checks detect structural failures and prompt the user to run the bootstrap-memory skill.
# Tier 1 checks auto-fix minor drift (broken symlink, missing MEMORY.md) silently.
# Outputs nothing on a healthy system.

REPO="${AGENT_MEMORY_DIR:-$HOME/.agents/agent-memory}"
REPO_SLUG="${AGENT_MEMORY_REPO:-mlarkin00/agent-memory}"
SYMLINK="$HOME/.claude/memory"
TIER2=0

# ── Tier 2 checks — structural failures; prompt bootstrap ─────────────────────

if [[ ! -d "$REPO" ]]; then
  echo "[verify-memory] ⚠ Repo not found at $REPO. Run the bootstrap-memory skill to set up." >&2
  TIER2=1
fi

if [[ "$TIER2" -eq 0 && ! -d "$REPO/.git" ]]; then
  echo "[verify-memory] ⚠ $REPO is not a git repo. Run the bootstrap-memory skill to restore." >&2
  TIER2=1
fi

if [[ "$TIER2" -eq 0 ]]; then
  REMOTE=$(git -C "$REPO" remote get-url origin 2>/dev/null || echo "")
  if [[ "$REMOTE" != *"$REPO_SLUG"* ]]; then
    echo "[verify-memory] ⚠ Remote '$REMOTE' does not match expected repo ($REPO_SLUG). Run the bootstrap-memory skill to restore." >&2
    TIER2=1
  fi
fi

# No check for ~/.claude/agents/memory-{puller,pusher}.md. Those agents were
# removed in 0.3.9 (Antigravity installs plugin agents but cannot invoke them);
# pull and push are the sync-memory skill and the scripts it calls. Stale copies
# left by an old install are harmless and say nothing about system health.

SETTINGS="$HOME/.claude/settings.json"
if [[ -f "$SETTINGS" ]]; then
  if ! python3 - <<'EOF'
import json, sys, os
with open(os.path.expanduser("~/.claude/settings.json")) as f:
    s = json.load(f)
hooks = s.get("hooks", {})
ss = str(hooks.get("SessionStart", []))
pt = str(hooks.get("PostToolUse", []))
ok = "memory-pull" in ss and "memory-push" in pt
sys.exit(0 if ok else 1)
EOF
  then
    echo "[verify-memory] ⚠ Memory sync hooks missing from ~/.claude/settings.json. Run the bootstrap-memory skill to register them." >&2
    TIER2=1
  fi
fi

# Stop here if any Tier 2 failure — no point fixing minor issues on a broken foundation
if [[ "$TIER2" -eq 1 ]]; then
  exit 0
fi

# ── Tier 1 checks — auto-fix silently ────────────────────────────────────────

# Symlink missing or broken
if [[ ! -L "$SYMLINK" || ! -d "$SYMLINK" ]]; then
  ln -sfn "$REPO" "$SYMLINK"
fi

# MEMORY.md missing
if [[ ! -f "$REPO/MEMORY.md" ]]; then
  printf "" > "$REPO/MEMORY.md"
  git -C "$REPO" add MEMORY.md
  git -C "$REPO" commit -m "memory: create MEMORY.md" 2>/dev/null || true
  git -C "$REPO" push origin main 2>/dev/null || true
fi

exit 0
