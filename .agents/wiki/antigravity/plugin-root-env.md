---
type: Runtime Behaviour
title: $CLAUDE_PLUGIN_ROOT does not exist in Antigravity
description: The variable is undefined in agy and empty in any model-run command,
  so it cannot be used to locate plugin files.
tags:
- antigravity
- hooks
- paths
timestamp: '2026-07-22T21:49:59+00:00'
---

`$CLAUDE_PLUGIN_ROOT` is **not defined anywhere in Antigravity**. The string does
not occur in the ~188 MB `agy` binary, and there is no `*_PLUGIN_ROOT` or `AGY_*`
equivalent.

Claude Code populates it for **hooks only**. It is empty in any command the model
runs — including a command a skill instructs the model to execute — on *both*
runtimes.

## Why it matters

A Claude hook converted by `agy` keeps the literal `$CLAUDE_PLUGIN_ROOT`, which
expands to nothing:

```
bash: /hooks/validate-on-write.sh: No such file or directory
```

The installer still reports `hooks : 1 processed`, so
[the count is not evidence](installer-counts.md).

## What to do instead

- **Hooks**: use relative commands; cwd is the plugin directory
  (see [hooks contract](hooks-contract.md)).
- **Scripts invoked from a script**: resolve from the script's own location,
  `readlink -f "${BASH_SOURCE[0]}"`, not an environment variable.
- **Skills**: use the ordered lookup in
  [script resolution](../cross-runtime/script-resolution.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
