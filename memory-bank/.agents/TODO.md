# TODO

## P0 — Address Immediately

(none)

## P1 — Important / Unblocking

(none)

## P2 — Nice-to-Have

- [ ] **[P2]** Consider deprecating `memories-curate` agent/skill — sidecar now runs identical semantic curation automatically at session end; the standalone skill is redundant except as an on-demand trigger.
- [ ] **[P2]** Retry importing 2 failed memory files into GCP Memory Bank — `README.md` and `project_agent_memory_plugin.md` hit HTTP 400 (likely too large); trim and re-add via `python3 ~/.claude/scripts/memory-bank/add_memory.py`.
- [ ] **[P2]** Add a `memories-query` skill wrapping `query_memories.py` for explicit similarity search.
- [ ] **[P2]** Add `--dry-run` flag to `sidecar_consolidate.py` to preview what would be consolidated without writing.
- [ ] **[P2]** Consider a `verify-memory-bank` skill (health-check + auto-repair, analogous to `verify-memory` in agent-memory).
- [ ] **[P2]** Update `bootstrap-memory-bank.md` Step 2 to use absolute path fallback when `$CLAUDE_PLUGIN_ROOT` is unset (confirmed needed during bootstrap run).
- [ ] **[P2]** Add a `/memories-graduate` skill wrapping `graduate_memories.py` so graduation can be triggered on-demand from a session without shelling out.
- [ ] **[P2]** Validate graduation output once remember has accumulated archive content — run `python3 scripts/graduate_memories.py --dry-run --force` and confirm candidates look correct.
