#!/usr/bin/env bash
# Gives the plugin's scripts stable, version-free paths under ~/.claude/scripts.
# Called on every SessionStart — idempotent and safe to re-run.
# Requires $CLAUDE_PLUGIN_ROOT to be set by the plugin host.
#
# Scripts only. This used to also link skills/ and agents/ into ~/.claude/, which
# earned nothing: Claude Code loads both from the installed plugin, namespaced as
# agent-memory:<name>. The skill copies landed as loose .md files in
# ~/.claude/skills/, which expects a directory per plugin, so nothing read them;
# the agent copies sat in a directory Claude Code does read, risking a second
# unnamespaced copy of each. Either way they were redundant, and every one of
# them pointed at whichever plugin root ran this script last.

set -euo pipefail

if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  echo "[agent-memory] WARNING: CLAUDE_PLUGIN_ROOT not set, skipping symlink install" >&2
  exit 0
fi

SCRIPTS_DIR="$HOME/.claude/scripts"

mkdir -p "$SCRIPTS_DIR"

link_file() {
  local target="$1"
  local link="$2"
  if [[ ! -L "$link" || "$(readlink "$link")" != "$target" ]]; then
    ln -sfn "$target" "$link"
  fi
}

# Scripts. The hooks call these through ~/.claude/scripts rather than
# $CLAUDE_PLUGIN_ROOT, so the link is what keeps them reachable across the
# version-keyed plugin cache path changing on every release.
link_file "$CLAUDE_PLUGIN_ROOT/scripts/memory-pull.sh"      "$SCRIPTS_DIR/memory-pull.sh"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/memory-push.sh"      "$SCRIPTS_DIR/memory-push.sh"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/verify-memory.sh"    "$SCRIPTS_DIR/verify-memory.sh"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/bootstrap-memory.sh" "$SCRIPTS_DIR/bootstrap-memory.sh"
