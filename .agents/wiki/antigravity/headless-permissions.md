---
type: Pitfall
title: Headless permission matching is first-word based
description: agy -p matches allow-rules on the command's first word, so a leading
  assignment or any $( ) substitution is auto-denied with no prompt.
tags:
- antigravity
- permissions
- skills
timestamp: '2026-07-22T21:49:59+00:00'
---

In headless mode (`agy -p`) a tool needing permission cannot prompt, so it is
auto-denied. Rules live in `permissions.allow` in
`~/.gemini/antigravity-cli/settings.json` as `command(<target>)`.

Matching keys on the command's **first word**:

| Command | With `command(bash)` / `command(ls)` |
|---|---|
| `bash /path/to/x.sh` | allowed |
| `ls -d a b c 2>/dev/null` | allowed |
| `SCRIPT=$(ls …); bash "$SCRIPT"` | **denied** — first token is an assignment |
| `bash "$(for p in …; done)"` | **denied** — substitution |

## Consequence for skills

A skill that shells out must issue **two plain commands** — a lookup, then the
call — rather than one clever line. See
[script resolution](../cross-runtime/script-resolution.md).

Interactive sessions are unaffected: the user simply approves once.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
