#!/usr/bin/env bash
# PreInvocation hook (Antigravity) — the once-per-session work that runs on
# SessionStart under Claude Code.
#
# Antigravity has no SessionStart event. Its nearest hook, PreInvocation, fires
# before EVERY model call and blocks the agent loop while it runs, so pulling on
# each one would put a network round-trip in front of every turn. This gates on
# `conversationId` from the hook payload: the first invocation of a conversation
# does the pull, every later one returns immediately. That reproduces Claude's
# once-per-session semantics on an event that has none.
#
# Deliberately does NOT run install-symlinks.sh. That script links into
# ~/.claude/, so running it from the Antigravity copy would repoint Claude
# Code's symlinks at this plugin directory — the two installs would fight over
# the same links. Nothing here needs them: the commands below are relative to
# the plugin root, which is the working directory Antigravity guarantees.
#
# Always prints `{}` and exits 0. PreInvocation stdout is parsed as JSON, and a
# hook must never break the session.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/agent-memory/agy-conversations"

emit() { printf '{}\n'; exit 0; }

PAYLOAD=$(cat)

# protojson camelCase. Keep only characters legal in a filename component so a
# hostile or malformed id cannot escape the state directory.
CONVERSATION_ID=$(printf '%s' "$PAYLOAD" | python3 -c "
import json, re, sys
try:
    v = str(json.load(sys.stdin).get('conversationId') or '')
except Exception:
    v = ''
print(v if re.fullmatch(r'[A-Za-z0-9._-]{1,128}', v) else '')
" 2>/dev/null)

# No usable id means no way to tell first invocation from tenth. Skip the work
# rather than run it every time — a missed pull self-corrects on the next
# session, a pull per model call does not.
[[ -z "$CONVERSATION_ID" ]] && emit

mkdir -p "$STATE_DIR" 2>/dev/null || emit
find "$STATE_DIR" -type f -mtime +7 -delete 2>/dev/null || true

MARKER="$STATE_DIR/$CONVERSATION_ID"
[[ -e "$MARKER" ]] && emit
: > "$MARKER" 2>/dev/null || emit

# stdout belongs to the hook contract, so the scripts' git output goes nowhere;
# stderr is left alone so Antigravity can log a real failure.
bash "$HERE/memory-pull.sh" >/dev/null || true
bash "$HERE/verify-memory.sh" >/dev/null || true

emit
