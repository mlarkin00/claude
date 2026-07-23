---
type: Pitfall
title: Hook output protocols differ between runtimes
description: Claude Code injects via plain stdout or hookSpecificOutput.additionalContext,
  Antigravity via injectSteps[].ephemeralMessage; emitting the wrong shape exits 0
  and injects nothing.
tags:
- hooks
- claude-code
- antigravity
timestamp: '2026-07-23T23:05:00+00:00'
---

A hook that wants to add context to a session must emit the shape its host
understands. The two runtimes do not share one.

| Runtime | How a hook injects context |
|---|---|
| Claude Code | plain text on stdout, **or** `{"hookSpecificOutput": {"hookEventName": "<Event>", "additionalContext": "…"}}` |
| Antigravity | `{"injectSteps": [{"ephemeralMessage": "…"}]}` |

Emitting the other runtime's shape is **not an error**. The host parses the JSON,
finds no directive it recognises, injects nothing, and the hook exits 0. Nothing
in the exit code, the logs, or the session surface says the context was dropped.

This is the output-side twin of
[hook payload key casing](payload-key-casing.md), which covers the same failure
on the input side. A shared hook script has to get **both** ends right.

## How this bites

`memory-bank/scripts/load_context.py` is registered on Claude Code's
`SessionStart` in `hooks/hooks.json`, but its only output path emits
`{"injectSteps": [{"ephemeralMessage": xml}]}` — Antigravity's shape. Verified
against Claude Code 2.1.218: every session queried Vertex AI, spent ~3.5 s
retrieving the user's memories, and discarded them. The plugin's entire read
path was dead on its primary runtime.

Across every transcript on the machine, **76 of 76** invocations recorded
`content` length 0 against 807–1104 bytes of stdout. The two hooks that did
inject on the same runtime — `memory-pull.sh` and the `remember` plugin's
`session-start-hook.sh` — both write plain text.

## How to detect it

Claude Code stores, per hook invocation, both what the hook printed and what
actually reached the context window:

- `attachment.stdout` — what the hook printed
- `attachment.content` — what was injected

**A zero exit with non-empty `stdout` and empty `content` is this bug.** Any
tool that collapses the two fields into one hides it; that conflation is why
this survived undetected for the plugin's whole life. See
[how injected context is stored](../claude-code/transcript-injected-context.md).

## Why it survived

The test suite asserted only the Antigravity shape, so it stayed green against a
hook that never fired on Claude Code — the same reason
[payload key casing](payload-key-casing.md) survived. Tests for a dual-runtime
hook must assert **both** output shapes, must assert the injected field is
non-empty rather than merely that the process exited 0, and must assert that the
delegating caller requests its own format.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
