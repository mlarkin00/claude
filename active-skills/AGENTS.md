# active-skills

## Project Goal

The `active-skills` plugin as it ships in the `mlarkin00/plugins` marketplace — installable in both Claude Code and Antigravity. The skills under `skills/` are **authored in `mlarkin00/active-skills`** and mirrored here by the `sync-active-skills.yml` workflow. Everything else in this directory (the two manifests, `scripts/`, `hooks.json`, `tests/`, and docs) is hand-maintained here.

## Project Context

One directory serves both runtimes, which read different manifest paths:

| Runtime | Manifest |
|---|---|
| Claude Code | `.claude-plugin/plugin.json` |
| Antigravity | `plugin.json` |

Both manifests carry the **same** version as the `active-skills` entry in the marketplace's `.claude-plugin/marketplace.json`. `skills/` is an rsync mirror of `mlarkin00/active-skills`, overwritten on every sync — never hand-edit it here.

This directory contains **skills and skill-authoring tooling only**. Usage tracking lives in the separate `skill-usage` plugin, by design: plugin machinery mixed into the skills made them a poor thing to author against.

## Operational Commands

```bash
# Regenerate the README inventory (run after adding/removing/retitling a skill)
bash scripts/gen-readme.sh

# Update-check tests (unittest — pytest is not a dependency)
python3 -m unittest discover -s tests -q

# Validate as an Antigravity plugin (also a good check that skills/ is clean)
agy plugin validate .

# Validate both manifests parse
python3 -c "import json;[json.load(open(f)) and print('OK',f) for f in ['.claude-plugin/plugin.json','plugin.json']]"
```

## Style & Conventions

- Each skill MUST live in `skills/<skill-name>/` with a `SKILL.md`, and `skills/` MUST contain **nothing but skill directories**. Antigravity installs every entry there as a skill, so a loose file becomes a phantom skill. `agy plugin validate .` reports the count, so a jump of one is the symptom.
- Run `gen-readme.sh` after any skill change. The block between `<!-- SKILLS:START -->` and `<!-- SKILLS:END -->` is generated and MUST NOT be hand-edited.
- **One version, in all three places.** `.claude-plugin/plugin.json`, `plugin.json`, and the `active-skills` entry in `.claude-plugin/marketplace.json` MUST carry the same version. `sync-active-skills.yml` patch-bumps all three — but **only when its own run dirties something** (a mirrored skill change). A hand edit to anything outside `skills/` (`scripts/`, `hooks.json`, `tests/`, or a manifest) is invisible to the sync, so **bump all three by hand in the same commit**, or the change never ships — caches are version-keyed. `active-skills` is deliberately NOT in `release.yml`; the sync owns it alone.

## Architecture & Constraints

**This repository is public.** Everything committed here, including history, is world-readable. Skills arrive by sync from `mlarkin00/active-skills`, so the internal-path scan belongs there — a pattern scan for `google3`, `go/`, and `blaze` alone is not sufficient; it missed `/google/bin/...` and internal proto paths such as `learning/gemini/...` elsewhere in this codebase.

**Do not add usage-tracking code here.** It belongs in `skill-usage`. Counts are personal telemetry and must never be committed to a public repo; `skill-usage.json` is gitignored as a backstop.

**Expect the remote to move under you.** `sync-active-skills.yml` commits a version bump on top of your push, so a follow-up push can be rejected. Rebase, never force.

**Never:**
- Put a non-skill file directly under `skills/`
- Hand-edit `skills/` — it is the rsync mirror of `mlarkin00/active-skills` and is overwritten on the next sync
- Hand-edit the generated skill inventory in `README.md`
- Skip the hand bump when you edit outside `skills/` — the sync won't do it for you
- Commit usage counts
