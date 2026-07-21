# mlarkin00-claude Marketplace

## Project Goal

Claude Code plugin marketplace. Hosts the plugins published under the `mlarkin00-claude` marketplace name and owns their versioning, tagging, and GitHub releases.

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
- Never bump a version by hand. Every plugin is workflow-versioned; a manual bump races the bot.
- Doc-only and workflow-only changes do not trigger a release (`release.yml` filters `README.md` and `.github/`).

## Architecture & Constraints

**Two independent release paths.** `release.yml` fires on every push to `main`, patch-bumps any plugin in its `PLUGINS` list with release-relevant changes, commits as `github-actions[bot]`, tags `<plugin>-v<version>`, and cuts a GitHub release. It guards against its own push with `if: github.actor != 'github-actions[bot]'`. `sync-active-skills.yml` is separate and owns `active-skills` end to end.

**`active-skills/skills/` is a mirror, not source.** `sync-active-skills.yml` exact-mirrors `mlarkin00/agent-skills:active-skills/` into it on `repository_dispatch`, a daily 06:17 UTC poll, or manual run — adds, updates, **and deletes** to match. Edits made here are silently reverted on the next sync. Change skills in `mlarkin00/agent-skills`.

Everything in `active-skills/` *outside* `skills/` — `hooks/`, `scripts/`, `sync/`, `README.md`, `.claude-plugin/` — is real source and is safe to edit here.

**Expect the remote to move under you.** A push to `mlarkin00/agent-skills` touching `active-skills/**` dispatches here, and the sync bot commits to `main` on its own. A local push racing it gets rejected; rebase, never force.

**Never:**
- Edit anything under `active-skills/skills/` — it is overwritten by the mirror
- Hand-bump a version for a plugin listed in a workflow's `PLUGINS`
- Leave a deleted plugin's name in `release.yml` — under `set -euo pipefail` a `jq` read of its missing `plugin.json` aborts the release step
- Force-push `main` — the release and sync bots both commit here
