---
type: Pitfall
title: Sidecars load from the config directory, never from a plugin
description: agy reads <config>/sidecars/<id>/sidecar.json; a sidecars/ directory
  inside a plugin is inert and is never listed as a component.
tags:
- antigravity
- sidecars
timestamp: '2026-07-22T21:49:59+00:00'
---

`agy` loads sidecars from **`<config>/sidecars/<id>/sidecar.json`** — that is
`~/.gemini/config/sidecars/` — one directory per sidecar, with the sidecar's own
folder as the execution cwd.

It does **not** look inside `plugins/<name>/sidecars/`, which is where
`agy plugin install` puts a plugin's sidecar files. Such a sidecar is inert.

## How it was confirmed

On a live install with two sidecar-shipping plugins present:
`~/.gemini/config/sidecars/` did not exist, no `sidecar_data/` runtime directory
was ever created, no sidecar process was running, and the installer never listed
sidecars as a component at all.

## Visible consequence

`skill-usage` counts skill invocations correctly through its `PostToolUse` hook,
but the counts file is never committed — committing is the sidecar's job.

## Fix shape

Install into `~/.gemini/config/sidecars/<id>/` (symlink or copy), or move the work
into a hook. A plugin cannot ship a working sidecar by placing it under
`sidecars/` and expecting the installer to find it.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
