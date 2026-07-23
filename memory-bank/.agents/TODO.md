# TODO

## P0 — Address Immediately

- [x] **[P0]** This plugin installed with **zero hooks** under Antigravity, so it never loaded or saved context there. *(2026-07-22: fixed — added `hooks.json` plus `scripts/agy_load_context.py`, which gates the loader on `conversationId` because Antigravity's `PreInvocation` fires before every model call. Root cause and evidence in `.agents/TODO.md` at the repo root.)*

- [x] **[P0]** `save_context.py` reads `transcriptPath` (Antigravity camelCase) and never `transcript_path`, so **session-end save is a silent no-op under Claude Code** — the Stop hook runs, finds no transcript, and returns. The tests feed the Antigravity key in all four cases and so never catch it. *(2026-07-22: fixed — accepts both keys; verified against a real Claude transcript. Full evidence in the root `.agents/TODO.md`.)*

## P1 — Important / Unblocking

- [x] **[P1]** Fix broken `memories:generate` event shape — session-end save + consolidation were silently failing. `save_context.py` and `sidecar_consolidate.py` sent `directContentsSource` events as `{"role":"USER","content":…}`, which the Memory Bank API REJECTS with HTTP 400 ("Unknown name 'role' at 'direct_contents_source.events[0]'"). Events must be Content-shaped: `{"content":{"role":"user"|"model","parts":[{"text":…}]}}` (role `"user"`/`"model"`, not `"USER"`/`"AGENT"`). *(2026-07-08: fixed the event-building loops in both `save_context.py` and `sidecar_consolidate.py` to emit the Content shape; updated `test_save_context.py` + `test_sidecar_consolidate.py` assertions; full suite green (30 tests). Shape matches the live-validated reference in `local-minions/minion-memory`.)*

## P2 — Nice-to-Have

- [ ] **[P2]** Reconsider the framing of `memories-curate`. Its premise here ("the sidecar runs identical curation at session end") is stale twice over: there is no sidecar — `sidecar_consolidate.py` is a `Stop` hook — and per the plugin CLAUDE.md, curation is no longer done in this plugin at all. It runs server-side on the deployed **memory-minion** agent (`nudge_minion.py` fires a fail-open nudge; the agent's own 6-hour schedule is the guaranteed trigger). So the local `memories-curate` skill is a manual nudge to that agent, not a local curation pass — reword the skill accordingly or drop it.
- [ ] **[P2]** Retry importing 2 failed memory files into GCP Memory Bank — `README.md` and `project_agent_memory_plugin.md` hit HTTP 400 (likely too large); trim and re-add via `python3 ~/.claude/scripts/memory-bank/add_memory.py`.
- [ ] **[P2]** Add a `memories-query` skill wrapping `query_memories.py` for explicit similarity search.
- [ ] **[P2]** Add `--dry-run` flag to `sidecar_consolidate.py` to preview what would be consolidated without writing.
- [ ] **[P2]** Consider a `verify-memory-bank` skill (health-check + auto-repair, analogous to `verify-memory` in agent-memory).
- [ ] **[P2]** Add a `/memories-graduate` skill wrapping `graduate_memories.py` so graduation can be triggered on-demand from a session without shelling out.
- [ ] **[P2]** Validate graduation output once remember has accumulated archive content — run `python3 scripts/graduate_memories.py --dry-run --force` and confirm candidates look correct. *(2026-06-18: dry-run confirmed correct early-exit when only `today-*.md` exists; re-test once `recent.md` accumulates)*
