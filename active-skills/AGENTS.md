# active-skills

## Project Goal

Source of truth for a curated set of agent skills, consumed by Claude Code and Antigravity. This is the **authoring** repo — clone it to edit skills. The `mlarkin00/plugins` marketplace mirrors it via CI, so users install from that single place (Claude marketplace, or `agy plugin install` of that repo) and never clone this one.

## Project Context

The repository root **is** the plugin. Two manifests coexist because the runtimes read different paths:

| Runtime | Manifest | Version |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | `0.2.1` |
| Antigravity | `plugin.json` | `0.1.11` |

Versions are deliberately independent — one runtime's fix must not force an empty release for the other. Each runtime ignores the other's files.

This repo contains **skills and skill-authoring tooling only**. Usage tracking lives in the separate `skill-usage` plugin in `mlarkin00/plugins`. That separation is intentional: plugin machinery here made the repo a poor place to author skills.

## Operational Commands

```bash
# Regenerate the README inventory (run after adding/removing/retitling a skill)
bash scripts/gen-readme.sh

# Update-check sidecar tests (unittest — pytest is not a dependency)
python3 -m unittest discover -s tests -q

# Validate as an Antigravity plugin (also a good check that skills/ is clean)
agy plugin validate .

# Validate both manifests parse
python3 -c "import json;[json.load(open(f)) and print('OK',f) for f in ['.claude-plugin/plugin.json','plugin.json']]"
```

## Style & Conventions

- Each skill MUST live in `skills/<skill-name>/` with a `SKILL.md`, and `skills/` MUST contain **nothing but skill directories**. Antigravity installs every entry there as a skill, so a loose file becomes a phantom skill. `agy plugin validate .` reports the count, so a jump of one is the symptom.
- Run `gen-readme.sh` after any skill change. The block between `<!-- SKILLS:START -->` and `<!-- SKILLS:END -->` is generated and MUST NOT be hand-edited.
- **Versions are automatic — do not hand-bump.** `.github/workflows/release.yml` patch-bumps the affected manifest(s) on every push to `main` and tags per runtime. The path→runtime mapping is the whole contract:

  | Changed path | Bumps |
  |---|---|
  | `skills/**` | both (`.claude-plugin/plugin.json` + `plugin.json`) |
  | `sidecars/**` | Antigravity only (`plugin.json`) |
  | docs, `scripts/`, `tests/`, `.github/` | nothing |

  This exists because plugin caches are version-keyed: an unbumped change is never delivered, so relying on memory to bump was a silent-failure mode. Extend the mapping when a runtime-specific directory is added.

## Architecture & Constraints

**This repository is public.** Everything committed here, including history, is world-readable. Before adding files, check for internal paths — a pattern scan for `google3`, `go/`, and `blaze` alone is not sufficient; it missed `/google/bin/...` and internal proto paths such as `learning/gemini/...` elsewhere in this codebase.

**Do not add usage-tracking code here.** It belongs in `skill-usage`. Counts are personal telemetry and must never be committed to a public repo; `skill-usage.json` is gitignored as a backstop.

**Expect the remote to move under you.** `release.yml` commits a version bump on top of your push, so a follow-up push can be rejected. Rebase, never force.

**Never:**
- Put a non-skill file directly under `skills/`
- Hand-edit the generated skill inventory in `README.md`
- Hand-bump a manifest `version` — `release.yml` owns it, and a manual bump races the bot
- Commit usage counts
