---
type: Runtime Behaviour
title: Two install paths, selected by the root plugin.json
description: A root plugin.json puts agy on its native path; without one it takes
  the claude-format path, which converts commands and merges a broken hooks block.
tags:
- antigravity
- install
timestamp: '2026-07-22T21:49:59+00:00'
---

`agy plugin install` handles a plugin one of two ways, chosen by whether a root
`plugin.json` is present.

| | no root `plugin.json` (claude-format) | with root `plugin.json` (native) |
|---|---|---|
| `hooks/hooks.json` | converted, `$CLAUDE_PLUGIN_ROOT` left intact → broken | ignored |
| root `hooks.json` | **merged** with the converted block — both fire | used as-is |
| `commands/` | converted to `<plugin>-cmd-*` skills | not converted |

## The merge trap

Shipping a correct root `hooks.json` *without* a root `plugin.json` does not
replace the converted block — `agy` appends its own under the key `"hooks"`, so
the broken copy keeps firing on every tool call alongside the working one. A
plugin that needs working hooks needs **both** files.

## Verified

A clean A/B on `llm-wiki`: without the root manifest `agy` writes 10
`llm-wiki-cmd-*` skill directories; with it, zero. Both runs print the identical
line `commands : 10 processed (converted to skills)` — see
[installer counts](installer-counts.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
