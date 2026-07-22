---
type: Pitfall
title: ls does not honour argument order
description: ls sorts its arguments, so `ls a b c | head -1` returns the alphabetically
  smallest path, which can silently select a stale cached copy.
tags:
- shell
- paths
timestamp: '2026-07-22T21:49:59+00:00'
---

`ls a b c` prints its arguments **sorted**, not in the order given. So
`ls a b c | head -1` yields the alphabetically smallest existing path — not the
first candidate.

## Observed

Resolving a memory-bank scripts directory, `ls` printed:

```
…/plugins/cache/mlarkin00-claude/memory-bank/0.1.14/scripts   ← stale, renamed marketplace
…/plugins/cache/mlarkin00-claude/memory-bank/0.1.15/scripts
…/plugins/cache/mlarkin00-plugins/memory-bank/0.1.17/scripts
…/.claude/scripts/memory-bank                                  ← the live symlink
…/.gemini/config/plugins/memory-bank/scripts
```

A `| head -1` selects version 0.1.14 from the **old marketplace name**. A
two-candidate list had worked only by alphabetical luck; adding a third broke it.

## Fix

Use an explicit `for` loop with `break`, or — when the consumer is a model —
state the precedence as prose it applies. See
[script resolution](../cross-runtime/script-resolution.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
