#!/usr/bin/env bash
# Provisions the agent memory system on a machine. Idempotent: every step checks
# before it creates, so re-running is safe and reports SKIPPED rather than
# failing. Invoked by the bootstrap-memory skill, which interprets the exit code
# for the user; also runnable by hand.
#
# This was an agent (agents/bootstrap-memory.md) until 0.3.9. Antigravity
# installs plugin agents but cannot invoke them, so the procedure moved here —
# a script runs identically on both runtimes and does not re-derive the steps
# each time it is asked.
#
# Environment overrides:
#   AGENT_MEMORY_REPO  GitHub repo, default mlarkin00/agent-memory
#   AGENT_MEMORY_DIR   local checkout, default ~/.agents/agent-memory
#
# Exit 0 = system ready (possibly with SKIPPED steps). Exit 1 = stopped early;
# the last ✗ line says why.

set -uo pipefail

REPO_SLUG="${AGENT_MEMORY_REPO:-mlarkin00/agent-memory}"
REPO="${AGENT_MEMORY_DIR:-$HOME/.agents/agent-memory}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="$HOME/.claude/settings.json"

ok()      { printf '✓ OK       %s\n' "$1"; }
created() { printf '✓ CREATED  %s\n' "$1"; }
skipped() { printf '→ SKIPPED  %s\n' "$1"; }
fail()    { printf '✗ FAILED   %s\n' "$1" >&2; exit 1; }

echo "Bootstrapping agent memory → $REPO (from $REPO_SLUG)"
echo

# --- Step 1: GitHub CLI auth ------------------------------------------------
# setup-git configures HTTPS auth from the gh token, so the push/fetch in the
# sync hooks work with no SSH key.
if ! command -v gh >/dev/null 2>&1; then
  fail "Step 1 auth: gh is not installed. Install it (https://cli.github.com), then re-run."
fi
if ! gh auth status >/dev/null 2>&1; then
  fail "Step 1 auth: gh is not authenticated. Run 'gh auth login', then re-run."
fi
gh auth setup-git >/dev/null 2>&1 || fail "Step 1 auth: 'gh auth setup-git' failed."
ok "Step 1 auth: gh authenticated and git credential helper configured"

# --- Step 2: clone the repo -------------------------------------------------
if [[ -d "$REPO/.git" ]]; then
  skipped "Step 2 clone: repo already present at $REPO"
else
  mkdir -p "$(dirname "$REPO")" || fail "Step 2 clone: cannot create $(dirname "$REPO")"
  if ! gh repo view "$REPO_SLUG" >/dev/null 2>&1; then
    gh repo create "$REPO_SLUG" --private >/dev/null 2>&1 \
      || fail "Step 2 clone: could not create $REPO_SLUG"
    created "Step 2 clone: created private repo $REPO_SLUG"
  fi
  gh repo clone "$REPO_SLUG" "$REPO" >/dev/null 2>&1 \
    || fail "Step 2 clone: could not clone $REPO_SLUG into $REPO"
  created "Step 2 clone: cloned $REPO_SLUG"
fi

# --- Step 3: MEMORY.md ------------------------------------------------------
# The index every session loads. An empty file is valid; its absence is not.
if [[ -f "$REPO/MEMORY.md" ]]; then
  ok "Step 3 index: MEMORY.md present"
else
  printf "" > "$REPO/MEMORY.md" || fail "Step 3 index: cannot write $REPO/MEMORY.md"
  created "Step 3 index: MEMORY.md"
fi

# --- Step 4: memory symlink -------------------------------------------------
LINK="$HOME/.claude/memory"
if [[ -L "$LINK" && "$(readlink "$LINK")" == "$REPO" ]]; then
  ok "Step 4 symlink: ~/.claude/memory → $REPO"
elif [[ -e "$LINK" && ! -L "$LINK" ]]; then
  fail "Step 4 symlink: $LINK exists and is not a symlink. Move it aside, then re-run."
else
  mkdir -p "$HOME/.claude"
  ln -sfn "$REPO" "$LINK" || fail "Step 4 symlink: cannot link $LINK → $REPO"
  created "Step 4 symlink: ~/.claude/memory → $REPO"
fi

# --- Step 5: migrate legacy memories ---------------------------------------
# Pre-plugin memories lived per-project under ~/.claude/projects/*/memory/.
# cp -n means the repo copy always wins — migration never clobbers synced state.
MIGRATED=0
shopt -s nullglob
for d in "$HOME"/.claude/projects/*/memory; do
  for f in "$d"/*.md; do
    if [[ ! -e "$REPO/$(basename "$f")" ]]; then
      cp -n "$f" "$REPO/" 2>/dev/null && MIGRATED=$((MIGRATED + 1))
    fi
  done
done
shopt -u nullglob
if [[ "$MIGRATED" -gt 0 ]]; then
  created "Step 5 migrate: copied $MIGRATED legacy memory file(s)"
else
  skipped "Step 5 migrate: no un-migrated legacy memories found"
fi

# --- Step 6: initial commit and push ---------------------------------------
cd "$REPO" || fail "Step 6 push: cannot enter $REPO"
git add . >/dev/null 2>&1
if git diff --cached --quiet; then
  skipped "Step 6 push: nothing to commit"
else
  git commit -q -m "memory: bootstrap @ $(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1 \
    || fail "Step 6 push: commit failed"
  created "Step 6 push: committed local state"
fi
# Push even when this run committed nothing — an earlier run may have left
# commits unpushed, and the hooks below assume the remote is reachable.
git push -q origin main >/dev/null 2>&1 \
  || fail "Step 6 push: push failed. Check 'gh auth status' and network, then re-run."
ok "Step 6 push: remote up to date"

# --- Step 7: register Claude Code hooks ------------------------------------
# Claude Code reads ~/.claude/settings.json; Antigravity gets the same behaviour
# from the plugin's own hooks.json and needs nothing here.
if [[ ! -d "$HOME/.claude" ]]; then
  skipped "Step 7 hooks: no ~/.claude on this machine (Antigravity uses the plugin's hooks.json)"
else
  HOOK_RESULT=$(python3 - "$SETTINGS" <<'PY'
import json, os, sys

path = sys.argv[1]
os.makedirs(os.path.dirname(path), exist_ok=True)

try:
    with open(path) as f:
        settings = json.load(f)
except FileNotFoundError:
    settings = {}
except json.JSONDecodeError as e:
    print(f"FAILED: {path} is not valid JSON ({e}); fix it by hand, then re-run.")
    sys.exit(1)

hooks = settings.setdefault("hooks", {})
pull_cmd = "bash ~/.claude/scripts/memory-pull.sh 2>/dev/null || true"
push_cmd = "bash ~/.claude/scripts/memory-push.sh 2>/dev/null || true"

added = []

session_start = hooks.setdefault("SessionStart", [])
if not any(pull_cmd in str(entry) for entry in session_start):
    session_start.append({"matcher": "*", "hooks": [{"type": "command", "command": pull_cmd}]})
    added.append("SessionStart/memory-pull")

post_tool = hooks.setdefault("PostToolUse", [])
if not any(push_cmd in str(entry) for entry in post_tool):
    post_tool.append({"matcher": "Edit|Write", "hooks": [{"type": "command", "command": push_cmd}]})
    added.append("PostToolUse/memory-push")

if added:
    # Write via a temp file so an interrupted run cannot truncate settings.json.
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp, path)
    print("ADDED: " + ", ".join(added))
else:
    print("PRESENT")
PY
  )
  case "$HOOK_RESULT" in
    ADDED*)   created "Step 7 hooks: ${HOOK_RESULT#ADDED: } registered in settings.json" ;;
    PRESENT)  ok      "Step 7 hooks: already registered in settings.json" ;;
    *)        fail    "Step 7 hooks: ${HOOK_RESULT#FAILED: }" ;;
  esac
fi

# --- Step 8: verify ---------------------------------------------------------
# Sibling lookup, not the three-path search: this script knows where it lives.
VERIFY="$SCRIPT_DIR/verify-memory.sh"
if [[ -x "$VERIFY" || -f "$VERIFY" ]]; then
  VERIFY_OUT=$(bash "$VERIFY" 2>&1)
  if echo "$VERIFY_OUT" | grep -q '⚠'; then
    printf '%s\n' "$VERIFY_OUT" >&2
    fail "Step 8 verify: verify-memory reported problems (above)"
  fi
  ok "Step 8 verify: all checks passed"
else
  skipped "Step 8 verify: verify-memory.sh not found next to this script"
fi

echo
echo "Memory system is ready. Memories are synced from GitHub and persist across"
echo "machines; the latest state is pulled at each session start."
