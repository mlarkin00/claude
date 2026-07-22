---
type: Convention
title: How a skill locates its plugin's scripts
description: Try three known roots in order as two plain commands; never $CLAUDE_PLUGIN_ROOT,
  never ls piped to head, never a single substitution line.
tags:
- skills
- paths
timestamp: '2026-07-22T21:49:59+00:00'
---

A plugin lives somewhere different per runtime, and
[$CLAUDE_PLUGIN_ROOT is unusable](../antigravity/plugin-root-env.md). A skill that
runs a script must locate it first.

## Candidates, in precedence order

1. `~/.claude/scripts/<plugin>/…` — the version-free symlink Claude Code's
   `install-symlinks.sh` maintains.
2. `~/.gemini/config/plugins/<plugin>/scripts/…` — Antigravity's install.
3. `~/.claude/plugins/cache/*/<plugin>/*/scripts/…` — last resort when the symlink
   was never created.

## Shape: two plain commands

```bash
ls -d <candidate1> <candidate2> <candidate3> 2>/dev/null
```

then run the first match **in the precedence order above**, as a separate command.

## Two traps

- **`ls` sorts its arguments**, so the first line out is not the first candidate —
  see [ls argument order](../testing/ls-argument-order.md). State the precedence as
  prose the model applies.
- **Never collapse it into one `$(…)` line** — auto-denied headlessly, see
  [headless permissions](../antigravity/headless-permissions.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
