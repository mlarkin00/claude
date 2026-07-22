# mlarkin00-plugins Marketplace

## Project Goal

Claude Code plugin marketplace. Hosts the plugins published under the `mlarkin00-plugins` marketplace name and owns their versioning, tagging, and GitHub releases.

## Project Context

Each top-level directory is a self-contained plugin (`.claude-plugin/plugin.json` + some of `skills/`, `agents/`, `commands/`, `hooks/`, `scripts/`). `.claude-plugin/marketplace.json` is the manifest that lists them. No build step, no test suite — correctness is manifest/disk agreement plus workflow behavior.

| Plugin | Versioned by |
|---|---|
| `agent-memory` | `release.yml` (auto) |
| `memory-bank` | `release.yml` (auto) |
| `llm-wiki` | `release.yml` (auto) |
| `active-skills` | `sync-active-skills.yml` (auto) |

Per-plugin briefings: `@llm-wiki/AGENTS.md`, `@memory-bank/AGENTS.md`.

## Operational Commands

```bash
# Verify every manifest entry resolves on disk and versions agree (run after any plugin change)
python3 -c "
import json,os
m=json.load(open('.claude-plugin/marketplace.json'))
for p in m['plugins']:
    s=p['source'].lstrip('./'); f=os.path.join(s,'.claude-plugin','plugin.json')
    v=json.load(open(f))['version'] if os.path.isfile(f) else None
    print(('OK ' if v==p['version'] else 'BAD'), p['name'], p['version'], v)
d={x for x in os.listdir('.') if os.path.isdir(os.path.join(x,'.claude-plugin'))}
print('unlisted on disk:', d-{p['name'] for p in m['plugins']} or 'none')"

# Regenerate the active-skills README inventory (CI runs this after every sync)
bash active-skills/scripts/gen-readme.sh

# Confirm the release workflow names no plugin that has been deleted
grep -n 'PLUGINS=' .github/workflows/release.yml
```

## Style & Conventions

- A plugin's `version` MUST be identical in its `plugin.json` and its `marketplace.json` entry. The workflows write both; hand edits MUST too.
- Adding or removing a plugin means three edits: the directory, the `marketplace.json` entry, and the `PLUGINS` list in `release.yml`. Missing the third leaves a stale name in the loop that drives releases.
- Never bump a version by hand for a plugin in a workflow's `PLUGINS` list — a manual bump races the bot.
- `active-skills` is versioned differently: `sync-active-skills.yml` patch-bumps it on every mirrored skill change. It is not in `release.yml`. Both of its manifests (`.claude-plugin/plugin.json` for Claude, `plugin.json` for Antigravity) carry the **same** version — one plugin serves both runtimes.
- **Hand edits to `active-skills/` outside `skills/` need a hand bump.** The sync only bumps when its own run dirties something, so a change you commit to `sidecars/`, `scripts/`, `tests/`, or a manifest is invisible to it and nothing else versions the plugin. Unbumped means never delivered, because caches are version-keyed. Bump both manifests and `marketplace.json` in the same commit.
- Doc-only and workflow-only changes do not trigger a release (`release.yml` filters `README.md` and `.github/`).

## Architecture & Constraints

**Two independent release paths.** `release.yml` fires on every push to `main`, patch-bumps any plugin in its `PLUGINS` list with release-relevant changes, commits as `github-actions[bot]`, tags `<plugin>-v<version>`, and cuts a GitHub release. It guards against its own push with `if: github.actor != 'github-actions[bot]'`. `sync-active-skills.yml` is separate and owns `active-skills`.

`active-skills` MUST stay out of `release.yml`. The sync job commits to `main` on its own; a second versioner would let a rebase race onto a competing bump and produce conflicting or duplicate `active-skills-v<N>` tags.

**`active-skills/` is a real plugin; only its `skills/` is a mirror.** The manifests, `scripts/`, `sidecars/`, `tests/`, `README.md`, and `AGENTS.md` are hand-maintained **here** and are yours to edit. `active-skills/skills/` is the rsync target and is overwritten on every sync — change skills in `mlarkin00/active-skills`, never here.

`sync-active-skills.yml` runs on `repository_dispatch` from the source repo, a daily 06:17 UTC poll, or manual dispatch. It selects skills by contract: **a skill is a top-level directory in the source repo containing a `SKILL.md`.** Anything else at that root (`README.md`, `.github/`, a future `docs/`) is skipped, so the authoring repo can hold non-skill content without shipping phantom skills — Antigravity installs *every* entry under `skills/` as a skill. A directory missing its `SKILL.md` is skipped silently; the run logs a `::notice::` naming what it skipped.

The rsync destination is `active-skills/skills/`, which is what makes the plugin's own files safe: `--delete` cannot reach one level up. That scoping is load-bearing, not stylistic — an earlier whole-directory mirror ran against a restructured source, flattened the skills to the plugin root, deleted the manifests and `sidecars/`, and **reported success** (`716fb23`, recovered in `0ca72e7`). The workflow also aborts if the source yields zero skills, because `--delete` would otherwise empty the plugin and commit it as a success.

This vendoring exists so this repo is the single install point for both runtimes: Claude via the marketplace entry, Antigravity via a clone of this repo bulk-installed with `agy plugin install <clone>` — which reports `Found bulk plugins directory` and installs every plugin physically present, hence `active-skills` must be present, not merely referenced. (There is no ad-hoc agy install from a repo URL, and `agy plugin import claude` does not work; the local clone is the proven path.)

**Expect the remote to move under you.** A push to `mlarkin00/active-skills` dispatches here, and the sync bot commits to `main` on its own. A local push racing it gets rejected; rebase, never force.

**Never:**
- Edit anything under `active-skills/skills/` — it is the mirror and is overwritten on the next sync; change skills in `mlarkin00/active-skills`
- Change the source layout `sync-active-skills.yml` reads without fixing the workflow first — that ordering is what caused `716fb23`
- Hand-bump a version for a plugin listed in a workflow's `PLUGINS`
- Leave a deleted plugin's name in `release.yml` — under `set -euo pipefail` a `jq` read of its missing `plugin.json` aborts the release step
- Force-push `main` — the release and sync bots both commit here
