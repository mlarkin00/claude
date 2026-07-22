# TODO

Defects found in the 2026-07-22 runtime review are tracked in the marketplace
backlog (`.agents/TODO.md` at the repo root) rather than here, because their
root causes are shared with other plugins. Still open: the ten `commands/*.md`
wrappers shadow their identically-named skills in Claude Code (P1), and
`commands/stats.md` has unparseable YAML frontmatter (P2).

Closed 2026-07-22: the `PostToolUse` validator resolved to an empty path under
Antigravity (P0). This plugin now carries a root `hooks.json` and a root
`plugin.json`; `hooks/validate-on-write.sh` reads both runtimes' payload shapes
and resolves the validator from its own location instead of
`$CLAUDE_PLUGIN_ROOT`, which Antigravity does not define.

## P1 — Important / Unblocking

- [ ] **[P1]** Ship a discoverability mechanism so agents actually read the bundle — currently `/llm-wiki:init` scaffolds the bundle and leaves discovery to a hand-written pointer in the host repo's `CLAUDE.md`, which is a passive trigger that does not reliably fire. **Observed failing 2026-07-21** in `local-minions`: the pointer ("read `.agents/wiki/index.md` before re-deriving history") was in context for a full session and the agent still did not open the index unprompted — "I am about to re-derive history" is not a state an agent recognizes about itself. Proposed fix: have `/llm-wiki:init` offer to install a `SessionStart` hook that injects the bundle's root `index.md` into context (826 bytes / 9 concepts in the `local-minions` bundle — every concept by title and description, so recognition replaces recall). Prior art: the `remember` plugin's `SessionStart` injection. Also worth templating a sharper `CLAUDE.md` bullet in `templates/` — name the concrete surfaces the bundle covers rather than an abstract "before re-deriving history". Rationale for P1 over P2: unread, every other feature here is dead weight — the bar is stated best in `local-minions`' hand-written bundle `CLAUDE.md` ("a wiki nobody reads is worse than a backlog nobody prunes"), a line that is **not** in `templates/bundle-CLAUDE.md`. That the sharpest authoring rules exist only in one downstream repo is itself part of this item: harvest them back into the template. Overlaps the sidecar item below; decide whether the hook ships standalone (available now) or as the sidecar's first job.

## P2 — Nice-to-Have

- [ ] **[P2]** Add a sidecar to run periodic/background bundle maintenance — schedule the passes that currently only happen when a human remembers to type them (`/llm-wiki:lint` for semantic drift, `/llm-wiki:log` for dated entries, plus `okf_index.py` / `okf_validate.py` / `okf_stats.py`). Open questions: timer mechanism (systemd timer vs. cron vs. `SessionStart` hook), whether lint's LLM pass runs unattended or only reports, and how findings surface (write to `log.md`, open a report doc, or notify). Prior art: `local-minions`' `minion-memory-sidecar.timer`.
- [ ] **[P2]** Add `raw/` sources layer convention to `/llm-wiki:init` — scaffold a `raw/` subdirectory alongside the bundle and document the convention in `templates/bundle-CLAUDE.md`; currently unspecced (DESIGN.md §13).
- [ ] **[P2]** Implement multi-bundle repo detection — find nearest ancestor directory containing a root `index.md` with `okf_version: "0.1"` instead of requiring an explicit `<bundle_root>` argument (DESIGN.md §13).
- [ ] **[P2]** Add integration smoke test for augmentation guard — create a fixture bundle, write a doc with a known `# Schema` field count, then confirm `okf_doc.py write --web-pass` correctly blocks a shrink attempt.
- [ ] **[P2]** Add `--dry-run` to `okf_doc.py write` — preview what would be written without mutating disk; useful for agent debugging.
- [ ] **[P2]** Add shard-family wildcard display to `okf_bq.py list` output — currently lists every shard individually; collapse `prefix_YYYYMMDD` families to `prefix_*` with a count annotation.
