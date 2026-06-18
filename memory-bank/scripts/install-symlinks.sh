#!/usr/bin/env bash
# Creates symlinks from user-level paths into the plugin bundle.
# Called on every SessionStart — idempotent and safe to re-run.
# Requires $CLAUDE_PLUGIN_ROOT to be set by the plugin host.

set -euo pipefail

if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  echo "[memory-bank] WARNING: CLAUDE_PLUGIN_ROOT not set, skipping symlink install" >&2
  exit 0
fi

SKILLS_DIR="$HOME/.claude/skills"
MB_SCRIPTS_DIR="$HOME/.claude/scripts/memory-bank"

mkdir -p "$SKILLS_DIR" "$MB_SCRIPTS_DIR"

link_file() {
  local target="$1"
  local link="$2"
  if [[ ! -L "$link" || "$(readlink "$link")" != "$target" ]]; then
    ln -sfn "$target" "$link"
  fi
}

# Skills
link_file "$CLAUDE_PLUGIN_ROOT/skills/memory-bank/SKILL.md"                 "$SKILLS_DIR/memory-bank.md"
link_file "$CLAUDE_PLUGIN_ROOT/skills/memories-add/SKILL.md"                "$SKILLS_DIR/memories-add.md"
link_file "$CLAUDE_PLUGIN_ROOT/skills/memories-list/SKILL.md"               "$SKILLS_DIR/memories-list.md"
link_file "$CLAUDE_PLUGIN_ROOT/skills/memories-update/SKILL.md"             "$SKILLS_DIR/memories-update.md"
link_file "$CLAUDE_PLUGIN_ROOT/skills/memories-delete/SKILL.md"             "$SKILLS_DIR/memories-delete.md"
link_file "$CLAUDE_PLUGIN_ROOT/skills/memories-set-project-scope/SKILL.md"  "$SKILLS_DIR/memories-set-project-scope.md"

# Python scripts (stable paths for agent skill calls)
for script in add_memory list_memories query_memories update_memory delete_memory \
              set_project_scope import_cc_memories; do
  link_file "$CLAUDE_PLUGIN_ROOT/scripts/${script}.py" "$MB_SCRIPTS_DIR/${script}.py"
done
link_file "$CLAUDE_PLUGIN_ROOT/scripts/config.py"        "$MB_SCRIPTS_DIR/config.py"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/resolve_scope.py" "$MB_SCRIPTS_DIR/resolve_scope.py"
