# TODO

Durable runtime evidence lives in the repo-root OKF bundle (`.agents/wiki/`), not
here — this file is only open tasks. The three cross-runtime hook P0s fixed on
2026-07-22/23 are recorded there: `cross-runtime/hook-output-protocols.md`
(output shapes), `cross-runtime/payload-key-casing.md` (input keys), and
`antigravity/hooks-contract.md` (the agy manifest).

## P0 — Address Immediately

(none)

## P1 — Important / Unblocking

(none)

## P2 — Nice-to-Have

- [ ] **[P2]** Reconsider the framing of `memories-curate`. Its premise here ("the sidecar runs identical curation at session end") is stale twice over: there is no sidecar — `sidecar_consolidate.py` is a `Stop` hook — and per the plugin CLAUDE.md, curation is no longer done in this plugin at all. It runs server-side on the deployed **memory-minion** agent (`nudge_minion.py` fires a fail-open nudge; the agent's own 6-hour schedule is the guaranteed trigger). So the local `memories-curate` skill is a manual nudge to that agent, not a local curation pass — reword the skill accordingly or drop it.
- [ ] **[P2]** Retry importing 2 failed memory files into GCP Memory Bank — `README.md` and `project_agent_memory_plugin.md` hit HTTP 400 (likely too large); trim and re-add via `python3 ~/.claude/scripts/memory-bank/add_memory.py`.
- [ ] **[P2]** Add a `memories-query` skill wrapping `query_memories.py` for explicit similarity search.
- [ ] **[P2]** Add `--dry-run` flag to `sidecar_consolidate.py` to preview what would be consolidated without writing.
- [ ] **[P2]** Consider a `verify-memory-bank` skill (health-check + auto-repair, analogous to `verify-memory` in agent-memory).
- [ ] **[P2]** Add a `/memories-graduate` skill wrapping `graduate_memories.py` so graduation can be triggered on-demand from a session without shelling out.
- [ ] **[P2]** Validate graduation output once remember has accumulated archive content — run `python3 scripts/graduate_memories.py --dry-run --force` and confirm candidates look correct. *(2026-06-18: dry-run confirmed correct early-exit when only `today-*.md` exists; re-test once `recent.md` accumulates)*
