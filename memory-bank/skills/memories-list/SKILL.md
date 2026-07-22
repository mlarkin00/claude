---
name: memories-list
description: List memories stored in the GCP Reasoning Engine Memory Bank. Use when the user wants to see what's in their memory bank, filter by scope, or look up a memory ID before updating or deleting.
---

List memories from the GCP Memory Bank.

## Steps

1. Locate the script — it lives in a different place per runtime:
   ```bash
   ls -d ~/.claude/scripts/memory-bank/list_memories.py \
         ~/.gemini/config/plugins/memory-bank/scripts/list_memories.py \
         ~/.claude/plugins/cache/*/memory-bank/*/scripts/list_memories.py 2>/dev/null
   ```
2. Run the first match in this precedence order, which is *not* the order `ls`
   prints (it sorts):
   1. `~/.claude/scripts/memory-bank/…` — the version-free symlink Claude Code's
      `install-symlinks.sh` maintains.
   2. `~/.gemini/config/plugins/memory-bank/scripts/…` — where Antigravity
      installs the plugin.
   3. anything under `~/.claude/plugins/cache/` — last resort if the symlink was
      never created; prefer the highest version number.

   ```bash
   python3 <the path you chose> [--scope current|all]
   ```
   Default: `--scope current` (shows global + project memories for the current workspace).

   If step 1 printed nothing, stop and report that the memory-bank plugin does
   not appear to be installed. Do not use `$CLAUDE_PLUGIN_ROOT` — it is set for
   hooks only and is empty in a command you run — and do not collapse this into
   one line with `$(…)`, which gets auto-denied in a headless Antigravity session.
2. Format the output as a Markdown table: `| # | ID | Scope | Fact |`

## Rules

- Use `--scope all` only if the user explicitly asks to see all memories regardless of project.
- Truncate the Fact column at 80 characters in the table; offer to show full text on request.
