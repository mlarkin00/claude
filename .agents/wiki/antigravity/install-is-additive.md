---
type: Runtime Behaviour
title: agy plugin install is additive — it never deletes files removed from the source
description: Re-installing a plugin over an existing install copies new/changed files
  but leaves behind anything the source no longer ships; removed components persist
  silently, and the install counts include the stale leftovers.
tags:
- antigravity
- install
---

`agy plugin install <path>` over a plugin that is already installed **merges**
the source into the destination directory. It copies new and changed files, but
it does **not** remove a file that the source no longer contains. Removing a
component from a plugin therefore does not remove it from an already-installed
agy runtime — the old files sit in `~/.gemini/config/plugins/<name>/` until
something deletes them explicitly.

Verified on **agy 1.1.5**, 2026-07-23, two ways.

## Controlled test

A throwaway plugin shipped one skill (`keep`) and one agent (`doomed-agent.md`).

```
install #1 (source has agents/)     → skills: 1 processed, agents: 1 processed
                                       install has agents/doomed-agent.md
rm -rf source agents/; install #2   → skills: 1 processed, agents: 1 processed
                                       install STILL has agents/doomed-agent.md
```

Two things to take from install #2: the removed file survived, and the installer
**still reported `agents: 1 processed`** though the source had no `agents/` at
all. The count reflects the post-merge destination, stale files included — a
sharper case of [install counts are not evidence](installer-counts.md).

## Field case

The agents→skills refactor (2026-07-23) deleted every plugin's `agents/`. A live
agy runtime that had the older release installed, then re-installed the new
source, ended up with the new skills **and** the dead `agents/` directories side
by side — `agent-memory/agents/{bootstrap-memory,memory-puller,memory-pusher}.md`,
`memory-bank/agents/bootstrap-memory-bank.md`,
`llm-wiki/agents/okf-*.md` — none of which the current source ships.

## Consequence

- Re-installing is not a clean sync. To drop a removed component from an existing
  install, delete it — either `rm -rf ~/.gemini/config/plugins/<name>/<removed>`,
  or `agy plugin uninstall <name>` then install, which removes the whole plugin
  directory first (see [component support](component-support.md), which notes
  uninstall removes only the plugin directory). A plugin dir here is pure code —
  agent-memory keeps its data in `~/.agents/agent-memory`, memory-bank in GCP —
  so uninstall+reinstall loses nothing.
- Left in place, the stale `agents/` files are inert on agy (plugin agents cannot
  be invoked there at all — see [component support](component-support.md)), so
  they cause no functional harm; they are misleading clutter, and they make the
  install disagree with the source.
- Do not read a version label as proof of what content is installed either: agy's
  plugin path is not version-keyed, so installing pre-bump source leaves an old
  `version` in `plugin.json` next to fully current files. Verify content by
  observing an effect, not by reading the manifest version.

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)
