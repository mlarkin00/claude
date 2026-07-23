---
type: Runtime Behaviour
title: Injected context is stored as typed records, not as rendered system-reminder text
description: The transcript keeps structured attachment records; the <system-reminder>
  wrapping is applied at send time and never written, so grepping for it returns zero
  hits in a session full of injections.
tags:
- claude-code
- hooks
- transcripts
timestamp: '2026-07-23T23:05:00+00:00'
---

Injected context reaches the model wrapped in `<system-reminder>` tags, but that
wrapping is applied when the request is built and is **never persisted**.
Grepping a transcript for `system-reminder` returns zero hits in a session with
dozens of injections. Verified against Claude Code 2.1.218.

What the transcript stores instead is one record per injection, with a typed
payload:

```json
{"type":"attachment","attachment":{"type":"nested_memory","path":"/repo/AGENTS.md",
 "content":{"type":"Project","content":"# Agent Instructions…","contentDiffersFromDisk":false}}}
```

Reconstruct from `attachment.type`. Never search for the rendered form.

## Locating a transcript

```
~/.claude/projects/<project-slug>/<session-uuid>.jsonl
```

The slug is derived from cwd by replacing separators and several other
characters with `-`, so `/home/user_name/my.app` and `/home/user-name/my-app`
collapse to the same value. **The mapping is not reversible** — do not
reconstruct it. Glob for `**/<session-uuid>.jsonl` instead, taking the UUID from
`$CLAUDE_CODE_SESSION_ID`.

Two traps around identity: `$CLAUDE_CODE_BRIDGE_SESSION_ID` is a differently
formatted `session_…` id used for web links, not the transcript filename; and
"newest `.jsonl` in the directory" is wrong because subagent sidechains and
concurrent sessions write newer files. Records carrying `isSidechain: true`
belong to a subagent, not the main thread.

## Fields that carry the diagnosis

- **`hook_success`** — `content` is what reached the context window; `stdout` is
  what the hook printed. They are often equal and sometimes not, and the gap is
  exactly where a silently-dropped injection shows up. Keep them separate; see
  [hook output protocols](../cross-runtime/hook-output-protocols.md).
- **`nested_memory`** — carries `contentDiffersFromDisk`, so a stale injected
  copy is visible without re-reading the file.
- **`*_delta`** (`agent_listing_delta`, `deferred_tools_delta`,
  `mcp_instructions_delta`) — incremental. The first carries `isInitial`; later
  records add and remove. Reading only the first misstates the current set.

## What the transcript cannot tell you

The **system prompt is not in the transcript** — tool schemas, base
instructions, and anything merged into the system block are invisible. Any claim
sourced from a transcript must be scoped to everything *else*.

Records are appended as the session runs, so the in-flight turn may not be
flushed yet.

## Why this matters

Asking an agent what is in its context invites an answer from introspection,
which cannot separate "I was told this" from "I inferred this" and cannot see a
file that silently failed to load. The transcript is the ground truth. The
`show-context` skill in `mlarkin00/active-skills` renders it; the taxonomy of
all 21 observed attachment types is in that skill's
`references/transcript-format.md`.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
[2] [mlarkin00/active-skills](https://github.com/mlarkin00/active-skills)
