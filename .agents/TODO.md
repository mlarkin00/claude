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

(none — the plugin-agents item was resolved 2026-07-23: all eight agents across
`agent-memory`, `memory-bank` and `llm-wiki` became skills and scripts, so no
plugin ships an `agents/` directory. Evidence and the resulting convention are
in `.agents/wiki/antigravity/component-support.md` and the root briefings'
"No plugin here ships an `agents/` directory" rule.)

## P2 — Nice-to-Have

- [ ] **[P2]** `AGENTS.md` (114 lines) and `CLAUDE.md` (109) exceed the 100-line briefing guideline; `AGENTS.md` was 94 before the discovery block landed, and the twin-check command added 4 more to each on 2026-07-23. The block is generated and load-bearing, so trim prose instead — the `## Operational Commands` manifest-check heredoc (12 lines) is the obvious candidate to move into a script and reference by path — `.agents/scripts/` now exists to hold it. Both files need the same edit, and `check-briefing-twins.py` will fail the build if only one gets it.

- [ ] **[P2]** Quote the `description` in `skills/skill-portfolio-review/SKILL.md` — the unquoted scalar contains `report: `, so a strict YAML parser aborts with `mapping values are not allowed here` (flagged by `claude plugin validate`, reproduced with PyYAML). Claude Code's runtime reader is lenient enough that the description currently loads, so this is latent rather than broken — but the validator's verdict is "loads with empty metadata", and a parser change would make that true. **Must be fixed upstream in `mlarkin00/active-skills`** — `active-skills/skills/` here is the rsync mirror and any local edit is overwritten on the next sync.

- [ ] **[P2]** `active-skills/README.md` contradicts the current design — it still says "The repository root *is* the plugin", "The two manifests coexist and **each carries its own version**", and describes a release workflow in the source repo, closing with "Don't hand-edit a `version`; the bot owns it". *(2026-07-22: the sidecar half of this is gone — the `sidecars/**` row and the "bumps only Antigravity" clause were dropped from both `README.md` and `AGENTS.md` when the sidecar was deleted. The remaining claims below still stand.)* The rest are false as of `0ca72e7`/`8643ac6`: both manifests carry one version, the source repo has no release workflow (its own README is correct and says so), and `AGENTS.md` now *requires* a hand bump for changes outside `skills/`. This file is hand-owned here (only the block between the `SKILLS:START/END` markers is generated), so it is this repo's to fix. Also reconsider the framing — the vendored copy still addresses the reader as if they were in the authoring repo ("clone it to author skills"). **`active-skills/AGENTS.md` has the same rot** and needs the same pass: its `## Style & Conventions` still promises "Versions are automatic — do not hand-bump" with a path→runtime bump table, describing a release workflow the authoring repo does not have, and directly contradicting this repo's rule that hand edits outside `skills/` require a hand bump.

- [ ] **[P2]** `agent-memory/README.md` ships stale install instructions — line 34 says `claude plugin marketplace add mlarkin00/agent-memory-plugin`, a repo that was renamed to `mlarkin00/plugins` and now works only via GitHub's redirect, and the next step's `claude plugin install agent-memory` omits the `@mlarkin00-plugins` marketplace qualifier. Also worth reviewing the "GitHub repo ([agent-memory](https://github.com/mlarkin00/agent-memory))" links, which point at a private repo and 404 for anyone else.

- [ ] **[P2]** `memory-bank` carries its GCP `config` block in **both** manifests, but only `.claude-plugin/plugin.json` is ever read — `scripts/config.py` resolves `../.claude-plugin/plugin.json` explicitly, so the copy in the root `plugin.json` is dead weight on both runtimes (under `agy` the plugin directory still contains the Claude manifest, which is why config resolution works there at all). The two agree today; nothing keeps them in step. Drop the duplicate, or have `config.py` prefer the root manifest and fall back.
