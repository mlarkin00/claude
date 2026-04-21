#!/usr/bin/env bash
# Creates symlinks from user-level paths into the plugin bundle.
# Called on every SessionStart — idempotent and safe to re-run.
# Requires $CLAUDE_PLUGIN_ROOT to be set by the plugin host.

set -euo pipefail

if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  echo "[agent-memory] WARNING: CLAUDE_PLUGIN_ROOT not set, skipping symlink install" >&2
  exit 0
fi

SCRIPTS_DIR="$HOME/.claude/scripts"
AGENTS_DIR="$HOME/.claude/agents"
SKILLS_DIR="$HOME/.claude/skills"

mkdir -p "$SCRIPTS_DIR" "$AGENTS_DIR" "$SKILLS_DIR"

link_file() {
  local target="$1"
  local link="$2"
  if [[ ! -L "$link" || "$(readlink "$link")" != "$target" ]]; then
    ln -sfn "$target" "$link"
  fi
}

# Scripts
link_file "$CLAUDE_PLUGIN_ROOT/scripts/memory-pull.sh"   "$SCRIPTS_DIR/memory-pull.sh"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/memory-push.sh"   "$SCRIPTS_DIR/memory-push.sh"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/verify-memory.sh" "$SCRIPTS_DIR/verify-memory.sh"

# Agent delegation wrappers
link_file "$CLAUDE_PLUGIN_ROOT/agents/memory-puller.md" "$AGENTS_DIR/memory-puller.md"
link_file "$CLAUDE_PLUGIN_ROOT/agents/memory-pusher.md" "$AGENTS_DIR/memory-pusher.md"

# Skills
link_file "$CLAUDE_PLUGIN_ROOT/skills/verify-memory/SKILL.md" "$SKILLS_DIR/verify-memory.md"
link_file "$CLAUDE_PLUGIN_ROOT/skills/add-memory/SKILL.md"    "$SKILLS_DIR/add-memory.md"
