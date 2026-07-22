---
type: Pitfall
title: The agy CLI never starts the sidecar manager
description: A valid sidecar in the documented config location does not run under
  the CLI, so sidecars are unusable there no matter where a plugin puts them.
tags:
- antigravity
- sidecars
timestamp: '2026-07-22T23:20:00+00:00'
---

Verified against `agy` 1.1.5.

The documented mechanism is real. The spec embedded in the binary describes
sidecars living at **`<config>/sidecars/<id>/sidecar.json`** — that is
`~/.gemini/config/sidecars/` — one directory per sidecar, with the sidecar's own
folder as the execution cwd, runtime output under `<appdata>/sidecar_data/`, and
a `schedule` builtin taking a cron expression.

**None of it runs under the CLI.** The `agy` binary contains the entire
subsystem — `SidecarManager.Start`, `pollSidecarsLoop`, `loadGlobal`,
`loadPlugin`, `migrateLegacyDir` — but the CLI never starts it. The spec text is
shipped as agent-facing documentation, and by inference the desktop Antigravity
app is what runs the manager. That half is untested here.

## How it was established

A sidecar was planted at `~/.gemini/config/sidecars/zz-probe/` in exactly the
documented layout — a `sidecar.json` with `command`/`args` pointing at a script
that appends a marker line — and exercised against two sessions:

* a short `agy -p` run, and
* a live interactive session held open for roughly three minutes.

In both cases the command never fired, no `logs/` directory was generated
beside the sidecar, no `sidecar_data/` runtime directory was created anywhere,
and `cli.log` contained no sidecar line other than
`Migration [MIGRATION_ID_SIDECAR_USER_CONFIG_BYPASS] is disabled`. Had the
manager started, `migrateLegacyDir` alone would have logged.

## Correcting an earlier claim

This page previously said sidecars fail because a plugin puts them in the wrong
place, and that the fix was to install into the config directory. Both are
wrong. The binary exports `loadPlugin` and the error string
`Failed to load sidecars from plugin %s`, so plugin-owned sidecars are a
supported path in the product — and relocating to the config directory fixes
nothing, because nothing on the CLI reads either location.

## Nothing outside `plugins/<name>/` has a lifecycle

Confirmed with an install/uninstall cycle in a throwaway `HOME`:
`agy plugin install` copies a plugin's `sidecars/` into the plugin directory but
never lists it as a processed component, and `agy plugin uninstall` deletes the
whole plugin directory and its `import_manifest.json` entry while touching
nothing outside `plugins/`. There is no postinstall or lifecycle hook in the
plugin spec. So a config-level sidecar would never be created on install,
refreshed on update, or removed on uninstall.

## What this repo did instead

Both sidecars were deleted on 2026-07-22 and their work moved into `Stop` hooks,
which ship inside the plugin and are therefore installed, updated and removed by
`agy plugin install`/`uninstall` for free. `Stop` fires at the end of every agent
turn, so each is gated: `skill-usage` passes `--min-interval 1800` to
`sync-usage.py`, and `active-skills` gates on a 6-hourly stamp and spawns the
network call detached. See [component support](component-support.md) and the
[hooks contract](hooks-contract.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
