#!/usr/bin/env bash
# Gives the plugin's scripts stable, version-free paths under ~/.claude/scripts,
# which is how the skills reach them (the plugin cache path is version-keyed and
# changes on every release).
# Called on every SessionStart — idempotent and safe to re-run.
# Requires $CLAUDE_PLUGIN_ROOT to be set by the plugin host.
#
# Scripts only. This used to also link the seven skills into ~/.claude/skills as
# loose .md files, which earned nothing: Claude Code loads them from the
# installed plugin as memory-bank:<name>, and ~/.claude/skills expects a
# directory per plugin, so nothing read the copies.

set -euo pipefail

if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
  echo "[memory-bank] WARNING: CLAUDE_PLUGIN_ROOT not set, skipping symlink install" >&2
  exit 0
fi

MB_SCRIPTS_DIR="$HOME/.claude/scripts/memory-bank"

mkdir -p "$MB_SCRIPTS_DIR"

link_file() {
  local target="$1"
  local link="$2"
  if [[ ! -L "$link" || "$(readlink "$link")" != "$target" ]]; then
    ln -sfn "$target" "$link"
  fi
}

# Python scripts (stable paths for agent skill calls)
for script in add_memory list_memories query_memories update_memory delete_memory \
              set_project_scope import_cc_memories graduate_memories nudge_minion \
              bootstrap create_engine load_context; do
  link_file "$CLAUDE_PLUGIN_ROOT/scripts/${script}.py" "$MB_SCRIPTS_DIR/${script}.py"
done
link_file "$CLAUDE_PLUGIN_ROOT/scripts/config.py"           "$MB_SCRIPTS_DIR/config.py"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/resolve_scope.py"    "$MB_SCRIPTS_DIR/resolve_scope.py"
link_file "$CLAUDE_PLUGIN_ROOT/scripts/resolve_remember.py" "$MB_SCRIPTS_DIR/resolve_remember.py"
