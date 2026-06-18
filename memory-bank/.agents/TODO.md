# TODO

## P0 — Address Immediately

(none)

## P1 — Important / Unblocking

- [ ] **[P1]** Port tests from `~/agent-skills/plugins/memory-bank/tests/` — adapt for Claude Code transcript format and `.claude-plugin/plugin.json` config path.
- [ ] **[P1]** Register `memory-bank` in the root `marketplace.json` before release.
- [ ] **[P1]** Verify `injectSteps` / `ephemeralMessage` from `SessionStart` hook actually injects context in Claude Code — test by running bootstrap and checking if memories appear at session start.
- [ ] **[P1]** Update `bootstrap-memory-bank.md` Step 2 once the canonical way to locate `CLAUDE_PLUGIN_ROOT` from within a session is confirmed.

## P2 — Nice-to-Have

- [ ] **[P2]** Add a `memories-query` skill wrapping `query_memories.py` for explicit similarity search.
- [ ] **[P2]** Add `--dry-run` flag to `sidecar_consolidate.py` to preview what would be consolidated.
- [ ] **[P2]** Consider a `verify-memory-bank` skill (like `verify-memory` in agent-memory) for health-check + auto-repair.
- [ ] **[P2]** Explore whether `StopHook` receives `transcriptPath` in Claude Code the same way Gemini CLI does — confirm format from real session output before relying on `save_context.py`.
