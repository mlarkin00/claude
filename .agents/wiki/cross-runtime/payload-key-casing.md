---
type: Pitfall
title: Hook payload keys differ in case between runtimes
description: Claude Code sends snake_case, Antigravity sends protojson camelCase;
  a shared hook script must read both or it silently no-ops on one runtime.
tags:
- hooks
- claude-code
- antigravity
timestamp: '2026-07-22T21:49:59+00:00'
---

The two runtimes key their hook payloads differently:

| Meaning | Claude Code | Antigravity |
|---|---|---|
| transcript | `transcript_path` | `transcriptPath` |
| tool call | `tool_name`, `tool_input` | `toolCall.name`, `toolCall.args` |
| workspace | `cwd` | `workspacePaths` |
| session | `session_id` | `conversationId` |

A script serving both **must read both spellings**.

## How this bites

`memory-bank/scripts/save_context.py` read only `transcriptPath`. Under Claude
Code the lookup returned `None`, the function returned at its guard, and the Stop
hook exited 0 having sent nothing — a silent no-op for the plugin's entire life.

## Why it survived

The test suite fed Antigravity keys in **all four** cases, so it stayed green
against a hook that never fired on the primary runtime. Assert **both** shapes —
see [test traps](../testing/patched-module-reload.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
