# mlarkin00-plugins Marketplace

## Project Goal

Single install point for one plugin set across **two runtimes** — Claude Code (via the `mlarkin00-plugins` marketplace) and Antigravity (`agy`, via a clone bulk-installed with `agy plugin install <clone>`). Owns their versioning, tagging, and GitHub releases. A change that works on only one runtime is not done.

## Project Context

Each top-level directory is one plugin serving both runtimes from one copy: `.claude-plugin/plugin.json` (Claude) and `plugin.json` (Antigravity) carrying the same version, plus some of `skills/`, `agents/`, `commands/`, `hooks/hooks.json` (Claude), `hooks.json` (Antigravity), `scripts/`, `sidecars/`. `.claude-plugin/marketplace.json` lists them. No build step; `memory-bank/tests` and `active-skills/tests` run under stdlib `unittest` (no pytest).

| Plugin | Versioned by |
|---|---|
| `agent-memory`, `llm-wiki`, `memory-bank`, `skill-usage` | `release.yml` (auto) |
| `active-skills` | `sync-active-skills.yml` (auto) |

Per-plugin briefings: `@llm-wiki/AGENTS.md`, `@memory-bank/AGENTS.md`. Backlog: `@.agents/TODO.md`. **Runtime evidence — how each rule below was established, and against which version — is an OKF bundle: `@.agents/wiki/index.md`** (authoring and maintenance: `.agents/wiki/CLAUDE.md`). Open the specific concept before changing a guard.

## Operational Commands

```bash
# Verify every manifest entry resolves on disk and ALL THREE versions agree
# (marketplace entry, Claude manifest, Antigravity manifest) — run after any plugin change
python3 -c "
import json,os
m=json.load(open('.claude-plugin/marketplace.json'))
for p in m['plugins']:
    s=p['source'].lstrip('./')
    cf=os.path.join(s,'.claude-plugin','plugin.json'); af=os.path.join(s,'plugin.json')
    cv=json.load(open(cf))['version'] if os.path.isfile(cf) else None
    av=json.load(open(af))['version'] if os.path.isfile(af) else '(no agy manifest)'
    ok = cv==p['version'] and av in (cv,'(no agy manifest)')
    print(('OK ' if ok else 'BAD'), p['name'], 'mkt='+p['version'], 'claude='+str(cv), 'agy='+av)
d={x for x in os.listdir('.') if os.path.isdir(os.path.join(x,'.claude-plugin'))}
print('unlisted on disk:', d-{p['name'] for p in m['plugins']} or 'none')"

# Regenerate the active-skills README inventory (CI runs this after every sync)
bash active-skills/scripts/gen-readme.sh

# Confirm the release workflow names no plugin that has been deleted
grep -n 'PLUGINS=' .github/workflows/release.yml

# Claude: validate a plugin or the marketplace manifest
claude plugin validate <plugin>|.

# Antigravity: the ONLY reliable check is a bulk install into a throwaway HOME.
# `agy plugin validate <path>` hard-fails on any plugin lacking a root plugin.json.
HOME=$(mktemp -d) agy plugin install "$PWD"

# Tests (stdlib unittest — pytest is not installed)
(cd memory-bank && python3 -m unittest discover -s tests)
```

## Style & Conventions

- A plugin's `version` MUST be identical in **all three** places: `.claude-plugin/plugin.json` (Claude), `plugin.json` (Antigravity), and its `marketplace.json` entry. One directory serves both runtimes, so one version describes it. Both workflows write all three; hand edits MUST too. The Antigravity manifest is optional — a plugin without one is fine, and `release.yml` logs a `::notice::` and bumps the Claude manifest alone.
- Adding or removing a plugin means three edits: the directory, the `marketplace.json` entry, and the `PLUGINS` list in `release.yml`. Missing the third leaves a stale name in the loop that drives releases.
- Never bump a version by hand for a plugin in a workflow's `PLUGINS` list — a manual bump races the bot. `active-skills` is the exception in reverse: `sync-active-skills.yml` patch-bumps it (both manifests + `marketplace.json`) on every mirrored skill change, and it is not in `release.yml`.
- **Hand edits to `active-skills/` outside `skills/` need a hand bump.** The sync only bumps when its own run dirties something, so a change you commit to `sidecars/`, `scripts/`, `tests/`, or a manifest is invisible to it and nothing else versions the plugin. Unbumped means never delivered, because caches are version-keyed. Bump both manifests and `marketplace.json` in the same commit.
- Doc-only and workflow-only changes do not trigger a release (`release.yml` filters `README.md` and `.github/`).
- **A hook that must run under Antigravity MUST be declared in a hand-written root `hooks.json`.** Shape: `{"<hook-name>": {"<Event>": [...]}}`. `PreToolUse`/`PostToolUse` take a `{matcher, hooks}` wrapper; `PreInvocation`/`PostInvocation`/`Stop` take a flat handler list. Those five are the only events — there is no `SessionStart` and no `SessionEnd`. Commands MUST be relative (`./scripts/x.sh`); cwd is the directory holding `hooks.json`. Copy the working shape from `skill-usage/hooks.json`.
- **`$CLAUDE_PLUGIN_ROOT` is populated for Claude hooks only.** It is empty in any command the model runs, and undefined everywhere in Antigravity. Skills MUST locate a script by trying, in order, `~/.claude/scripts/<plugin>/…`, `~/.gemini/config/plugins/<plugin>/scripts/…`, then `~/.claude/plugins/cache/*/<plugin>/*/scripts/…` — as two plain commands (a lookup, then the call). Never `ls a b c | head -1` (`ls` sorts, so it picks a stale cache copy) and never one `$(…)` line (auto-denied in headless agy). See `@memory-bank/AGENTS.md`.
- Session-once work has no Antigravity equivalent: map it to `PreInvocation` **and gate it**, since that fires before every model call and blocks the loop. Gate on `conversationId`; if the hook injects context, cache and replay the payload rather than skipping, because `ephemeralMessage` is transient.

## Architecture & Constraints

**Not every component type works on both runtimes.** Verified 2026-07-22 by live sessions, not by reading the installer:

| Component | Claude | Antigravity |
|---|---|---|
| `skills/` | yes | yes |
| `hooks` | yes | yes — from root `hooks.json` only |
| `commands/` | yes (surfaced as skills) | converted **only** on the claude-format path, i.e. when the plugin has no root `plugin.json` |
| `agents/` | yes | **no** — installed, counted, and unreachable |
| `sidecars/` | n/a | **no** — `agy` reads `<config>/sidecars/`, never a plugin's own |

Design around it: anything a plugin needs to *do* on Antigravity has to be a skill or a hook.

**Two independent release paths.** `release.yml` fires on every push to `main`, patch-bumps any plugin in its `PLUGINS` list with release-relevant changes, commits as `github-actions[bot]`, tags `<plugin>-v<version>`, and cuts a GitHub release. It guards against its own push with `if: github.actor != 'github-actions[bot]'`. `sync-active-skills.yml` is separate and owns `active-skills`.

`active-skills` MUST stay out of `release.yml`. The sync job commits to `main` on its own; a second versioner would let a rebase race onto a competing bump and produce conflicting or duplicate `active-skills-v<N>` tags.

**`active-skills/` is a real plugin; only its `skills/` is a mirror.** The manifests, `scripts/`, `sidecars/`, `tests/`, `README.md`, and `AGENTS.md` are hand-maintained **here** and are yours to edit. `active-skills/skills/` is the rsync target and is overwritten on every sync — change skills in `mlarkin00/active-skills`, never here.

`sync-active-skills.yml` runs on `repository_dispatch`, a daily 06:17 UTC poll, or manual dispatch. It selects by contract — **a skill is a top-level source directory containing a `SKILL.md`** — so the authoring repo can hold `README.md`/`docs/` without shipping phantom skills (Antigravity installs *every* entry under `skills/` as one). Skips are logged as a `::notice::`.

Two guards are load-bearing, not stylistic. The rsync destination is `active-skills/skills/`, so `--delete` cannot reach the plugin's own files one level up; an earlier whole-directory mirror ran against a restructured source, flattened the skills to the plugin root, deleted the manifests and `sidecars/`, and **reported success** (`716fb23`, recovered in `0ca72e7`). And the run aborts on zero skills, which would otherwise empty the plugin and commit it as a success.

The vendoring exists because `agy plugin install <clone>` installs every plugin *physically present* — so `active-skills` must be here, not merely referenced. There is no ad-hoc agy install from a repo URL, and `agy plugin import claude` does not work.

**Expect the remote to move under you.** A push to `mlarkin00/active-skills` dispatches here, and the sync bot commits to `main` on its own. A local push racing it gets rejected; rebase, never force.

**Never:**
- Treat `agy plugin install` output as evidence. Its component counts report what the installer walked, not what the runtime can use — it printed `commands : 10 processed` while writing zero, `hooks : 1 processed` for a hook resolving to a nonexistent path, and `agents : 3 processed` for agents nothing can invoke. Verify by observing an effect: a marker file, a counted skill, a validator line in `~/.gemini/antigravity-cli/cli.log`, a committed memory.
- Run `install-symlinks.sh` from the Antigravity copy — it links into `~/.claude/` and would repoint Claude Code's symlinks at the agy install
- Edit anything under `active-skills/skills/` — it is the mirror and is overwritten on the next sync; change skills in `mlarkin00/active-skills`
- Change the source layout `sync-active-skills.yml` reads without fixing the workflow first — that ordering is what caused `716fb23`
- Hand-bump a version for a plugin listed in a workflow's `PLUGINS`
- Leave a deleted plugin's name in `release.yml` — under `set -euo pipefail` a `jq` read of its missing `plugin.json` aborts the release step
- Force-push `main` — the release and sync bots both commit here
