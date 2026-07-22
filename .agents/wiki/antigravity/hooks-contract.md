---
type: Runtime Behaviour
title: Antigravity hooks contract
description: agy runs hooks only from a plugin's root hooks.json, supports five events,
  and sets cwd to that file's directory.
tags:
- antigravity
- hooks
timestamp: '2026-07-22T21:49:59+00:00'
---

`agy` reads lifecycle hooks from a **root `hooks.json`** in the plugin directory.
A Claude-format `hooks/hooks.json` is only consulted on the claude-format install
path (see [install paths](install-paths.md)).

## File shape

Top level is an object keyed by *hook name*:

```json
{"my-hook": {"PostToolUse": [{"matcher": "", "hooks": [{"command": "./scripts/x.py", "timeout": 5}]}]}}
```

- `PreToolUse` / `PostToolUse` take a `{matcher, hooks}` wrapper.
- `PreInvocation` / `PostInvocation` / `Stop` take a **flat** handler list.
- `enabled: false` disables a named hook.

## The five events

`PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`. That is the
complete set — there is **no `SessionStart`** and **no `SessionEnd`**. The string
`SessionStart` does appear in the binary, but not as a hook event; a raw string
match is not the schema.

## Handler fields

`type` defaults to `command` (the only supported kind), `timeout` is seconds
(default 30), and `command` runs via `sh -c` with **cwd set to the directory
containing `hooks.json`**. Commands must therefore be relative — `./scripts/x.sh`
— and must not rely on [$CLAUDE_PLUGIN_ROOT](plugin-root-env.md).

Hooks run synchronously and block the agent loop, which is why
[PreInvocation work must be gated](preinvocation-semantics.md).

## Where the spec lives

The full specification is embedded in the `agy` binary. Recover it with:

```bash
strings -a "$(readlink -f "$(which agy)")" | grep -n 'PreInvocation. Contract'
```

Read that before guessing at hook behaviour.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
