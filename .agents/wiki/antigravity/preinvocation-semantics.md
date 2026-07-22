---
type: Pitfall
title: PreInvocation is not SessionStart
description: It fires before every model call and blocks the loop, and its ephemeralMessage
  is transient, so session-once work must be gated and injected context must be cached
  and replayed.
tags:
- antigravity
- hooks
timestamp: '2026-07-22T21:49:59+00:00'
---

Antigravity has no `SessionStart`, so once-per-session work maps to
`PreInvocation`. The mapping needs more than a rename.

## It fires before every model call

And it blocks the agent loop while it runs. Unguarded, a Vertex AI round-trip
(measured ~3.6s) or a `git fetch` lands in front of **every turn**. Gate on
`conversationId` from the payload.

## Its injected message is transient

`ephemeralMessage` lives only for the invocation it was injected into. A gate that
simply *skips* after the first invocation leaves later turns with nothing.

This is not detectable offline. A first implementation skipped after turn one,
passed every local test, and failed in a live session — turn 2 of the same
conversation answered "NO MEMORIES INJECTED".

## The rule

- **Side-effect work** (a `git fetch`): skipping after the first invocation is correct.
- **Context injection**: **cache the rendered payload and replay it** on every later
  invocation, with a refresh interval so a long conversation picks up new data.

Reference implementation: `memory-bank/scripts/agy_load_context.py` (3.98s first
turn, 0.03s after, memories present on both).

For context that is **static** for the session, do not use a hook at all — put it
in the briefing file, which both runtimes load for free. Which file, and whether
imports expand, differs per runtime:
[briefing-file loading](../cross-runtime/briefing-file-loading.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
