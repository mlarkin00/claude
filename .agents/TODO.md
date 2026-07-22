# TODO

Marketplace-level backlog. Per-plugin backlogs live in `<plugin>/.agents/TODO.md`;
items here either span plugins or live in the workflows.

Everything below was found in the **2026-07-22 post-restructure runtime review**
(`agy` 1.1.5, Claude Code 2.1.217), which exercised both runtimes end to end.
What passed is recorded at the bottom so a re-check knows what not to re-derive.
Durable runtime behaviour learned that day lives in the OKF bundle at
`wiki/` (`@.agents/wiki/index.md`), not here — this file is only open tasks.

## P0 — Address Immediately

(none)

## P1 — Important / Unblocking

- [ ] **[P1]** Neither sidecar is registered or run by Antigravity — both are dead files as shipped. `agy` loads sidecars from **`<config>/sidecars/<id>/sidecar.json`** (i.e. `~/.gemini/config/sidecars/`), one directory per sidecar, per the spec embedded in the binary; it does not look inside `plugins/<name>/sidecars/`, which is where `agy plugin install` puts ours. Confirmed against a live install: `~/.gemini/config/sidecars/` does not exist, no `sidecar_data/` runtime directory was ever created, no sidecar process is running, and the installer never lists sidecars as a component at all. The visible consequence: `skill-usage` counts correctly under Antigravity (a live session took `systematic-debugging` to 1) but nothing there ever commits them, because committing and pushing is `sidecars/sync-usage`'s job. **Scoped correctly, this is an Antigravity-only gap** — on Claude Code the `SessionEnd` hook runs `sync-usage.py` and does commit, verified by two `chore(active-skills): update skill usage counts` commits landing during the 2026-07-22 session. So a dual-runtime machine self-heals on the next Claude session and only an agy-only machine accumulates counts forever. `active-skills`' `check-updates` never runs there either. Its URL was fixed in 0.2.8, so it now works wherever it is actually scheduled — which on Antigravity is nowhere. **Fix:** install sidecars into `~/.gemini/config/sidecars/<id>/` (symlink or copy from the plugin — the execution CWD is the sidecar's own folder, which `check_updates.py` already assumes), or drop them and move the work into a hook. A plugin cannot ship a working sidecar by placing it under `sidecars/` and expecting `agy plugin install` to find it.

- [ ] **[P1]** Plugin agents install but cannot be invoked under Antigravity — all eight (`agent-memory` 3, `memory-bank` 1, `llm-wiki` 4) are copied to `plugins/<name>/agents/` and counted at install (`agents : 3 processed`), but `agy agents` lists nothing and a live session asked directly answered **"NO PLUGIN SUBAGENTS"**, offering only the built-in `research` and `self`. They are not converted to skills either. The agent layer of three plugins is therefore inert on that runtime: anything that says "run the bootstrap-memory agent" — including `verify-memory.sh`'s own remediation message — has no way to happen there. **Fix:** decide whether these become skills for Antigravity (the only component type that demonstrably loads) or whether the plugins document agents as Claude-only. Note the frontmatter fix that landed in agent-memory 0.3.8 restored these agents' descriptions and tool restrictions for Claude Code only — on Antigravity they remain unreachable regardless, which is what this item is about.

## P2 — Nice-to-Have

- [ ] **[P2]** Quote the `description` in `skills/skill-portfolio-review/SKILL.md` — the unquoted scalar contains `report: `, so a strict YAML parser aborts with `mapping values are not allowed here` (flagged by `claude plugin validate`, reproduced with PyYAML). Claude Code's runtime reader is lenient enough that the description currently loads, so this is latent rather than broken — but the validator's verdict is "loads with empty metadata", and a parser change would make that true. **Must be fixed upstream in `mlarkin00/active-skills`** — `active-skills/skills/` here is the rsync mirror and any local edit is overwritten on the next sync.

- [ ] **[P2]** `active-skills/README.md` contradicts the current design — it still says "The repository root *is* the plugin", "The two manifests coexist and **each carries its own version**", and describes a release workflow in the source repo that bumps "only Antigravity" for a `sidecars/` change, closing with "Don't hand-edit a `version`; the bot owns it". All four are false as of `0ca72e7`/`8643ac6`: both manifests carry one version, the source repo has no release workflow (its own README is correct and says so), and `AGENTS.md` now *requires* a hand bump for changes outside `skills/`. This file is hand-owned here (only the block between the `SKILLS:START/END` markers is generated), so it is this repo's to fix. Also reconsider the framing — the vendored copy still addresses the reader as if they were in the authoring repo ("clone it to author skills").

- [ ] **[P2]** `agent-memory/README.md` ships stale install instructions — line 34 says `claude plugin marketplace add mlarkin00/agent-memory-plugin`, a repo that was renamed to `mlarkin00/plugins` and now works only via GitHub's redirect, and the next step's `claude plugin install agent-memory` omits the `@mlarkin00-plugins` marketplace qualifier. Also worth reviewing the "GitHub repo ([agent-memory](https://github.com/mlarkin00/agent-memory))" links, which point at a private repo and 404 for anyone else.

- [ ] **[P2]** `memory-bank` carries its GCP `config` block in **both** manifests, but only `.claude-plugin/plugin.json` is ever read — `scripts/config.py` resolves `../.claude-plugin/plugin.json` explicitly, so the copy in the root `plugin.json` is dead weight on both runtimes (under `agy` the plugin directory still contains the Claude manifest, which is why config resolution works there at all). The two agree today; nothing keeps them in step. Drop the duplicate, or have `config.py` prefer the root manifest and fall back.
