# TODO

## P0 — Address Immediately

(none)

## P1 — Important / Unblocking

- [ ] **[P1]** Port tests from `~/agent-skills/plugins/memory-bank/tests/` — adapt for Claude Code transcript format (`role: user/assistant`) and `.claude-plugin/plugin.json` config path.
- [ ] **[P1]** Confirm `injectSteps`/`ephemeralMessage` from `SessionStart` hook injects memories into Claude Code context — `load_context.py` produces valid JSON but end-to-end injection in a live session has not been manually verified yet.
- [ ] **[P1]** Confirm `Stop` hook receives `transcriptPath` in Claude Code — verify `save_context.py` actually processes a real transcript before relying on session-end consolidation.

## P2 — Nice-to-Have

- [ ] **[P2]** Retry importing 2 failed memory files into GCP Memory Bank — `README.md` and `project_agent_memory_plugin.md` hit HTTP 400 (likely too large); trim and re-add via `python3 ~/.claude/scripts/memory-bank/add_memory.py`.
- [ ] **[P2]** Add a `memories-query` skill wrapping `query_memories.py` for explicit similarity search.
- [ ] **[P2]** Add `--dry-run` flag to `sidecar_consolidate.py` to preview what would be consolidated.
- [ ] **[P2]** Consider a `verify-memory-bank` skill (health-check + auto-repair, analogous to `verify-memory` in agent-memory).
- [ ] **[P2]** Update `bootstrap-memory-bank.md` Step 2 to use absolute path fallback when `$CLAUDE_PLUGIN_ROOT` is unset (confirmed needed during bootstrap run).
