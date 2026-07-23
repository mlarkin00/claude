---
name: bootstrap-memory
description: Use when setting up or restoring the agent memory system on a machine — the user asks to "set up agent memory", "bootstrap memory", memory has stopped syncing, or verify-memory reported a structural failure and offered to bootstrap. Clones the memory repo, wires the symlink and sync hooks, migrates legacy memories, and verifies the result.
---

Provisioning is a script, not a procedure you follow by hand. It is idempotent —
every step checks before it creates — so running it on an already-healthy machine
is safe and reports `SKIPPED` rather than failing.

**Step 1 — locate it.** The path differs per runtime:

```bash
ls -d ~/.claude/scripts/bootstrap-memory.sh \
      ~/.gemini/config/plugins/agent-memory/scripts/bootstrap-memory.sh \
      ~/.claude/plugins/cache/*/agent-memory/*/scripts/bootstrap-memory.sh 2>/dev/null
```

**Step 2 — run the first match in this precedence order**, which is *not* the
order `ls` prints (it sorts):

1. `~/.claude/scripts/bootstrap-memory.sh` — the version-free symlink
   `install-symlinks.sh` maintains.
2. `~/.gemini/config/plugins/agent-memory/scripts/bootstrap-memory.sh` — where
   Antigravity installs the plugin.
3. anything under `~/.claude/plugins/cache/` — last resort if the symlink was
   never created; prefer the highest version number.

```bash
bash <the path you chose>
```

If step 1 printed nothing, stop and report that the agent-memory plugin does not
appear to be installed.

Two constraints worth knowing before you "simplify" this: `$CLAUDE_PLUGIN_ROOT`
is set for hooks only and is **empty** in a command you run, and a one-liner
using `$(…)` command substitution gets auto-denied in a headless Antigravity
session — two plain commands are what survive a permission allowlist.

## Interpreting the result

The script prints one line per step and exits 0 when the system is ready.

- **Exit 0** — report the status table as-is. `SKIPPED` lines are normal on a
  machine that was already set up; they are not warnings.
- **Exit 1** — it stopped at the first hard failure and the final `✗ FAILED`
  line says which step and what to do. Relay that line, do the fix if it is
  yours to do, then re-run the script rather than continuing by hand.

The failures that need the user rather than you:

| `✗ FAILED` line mentions | What the user must do |
|---|---|
| `gh is not installed` | Install the GitHub CLI (https://cli.github.com) |
| `gh is not authenticated` | Run `gh auth login` |
| `settings.json is not valid JSON` | Fix the syntax by hand — the script will not overwrite a file it cannot parse |
| `exists and is not a symlink` | Move the real `~/.claude/memory` directory aside; its contents are not yet in the repo |

Step 7 reports `SKIPPED` when there is no `~/.claude` on the machine. That is
correct on Antigravity, which gets the same pull/push behaviour from the
plugin's own `hooks.json` and needs nothing in `settings.json`.

## Targeting a different repo

Both this script and `verify-memory.sh` honour the same two overrides, so they
agree about what "the memory repo" is:

```bash
AGENT_MEMORY_REPO=owner/name AGENT_MEMORY_DIR=~/somewhere bash <path>
```
