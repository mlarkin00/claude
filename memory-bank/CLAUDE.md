## Project Goal

GCP-backed long-term memory for Claude Code. Fetches global and project-scoped facts from Vertex AI Reasoning Engine Memory Bank at session start; consolidates new facts at session end.

## Project Context

Claude Code plugin in `mlarkin00/claude` monorepo. Port of `~/agent-skills/plugins/memory-bank` (Gemini CLI).
Python 3 stdlib only · GCP Vertex AI Memory Bank API · ADC auth.

Config lives in `.claude-plugin/plugin.json` (`config.project/location/reasoning_engine_id`); env-var fallback: `GCP_PROJECT`, `GCP_LOCATION`, `GCP_REASONING_ENGINE`.

## Operational Commands

```bash
echo '{}' | python3 scripts/load_context.py          # test session-start injection
python3 scripts/list_memories.py                      # list current-scope memories
python3 scripts/add_memory.py "fact" --scope global   # add a memory
python3 scripts/sidecar_consolidate.py --force        # force daily consolidation
cd tests && python3 -m pytest -v                      # run tests
```

## Style & Conventions

- Python 3 stdlib only — no pip installs.
- Single-responsibility scripts; import `config.py` + `resolve_scope.py` via `sys.path.insert`.
- All network calls MUST have timeouts and graceful exception handling — hooks must never crash the session.
- Default scope: ALWAYS `global`. Use `project` only on explicit user request.

## Architecture & Constraints

- `load_context.py` outputs `{"injectSteps": [{"ephemeralMessage": "<long_term_memories>..."}]}`.
- `save_context.py` handles Claude Code transcript fields: `role: user/assistant`, content as string or list of `{type, text}` blocks.
- `sidecar_consolidate.py` runs ≤once/24h; walks `~/.claude/projects/**/*.jsonl`.
- Skills call scripts via `~/.claude/scripts/memory-bank/<script>.py` (symlinked by `install-symlinks.sh`).
- Hook commands use `$CLAUDE_PLUGIN_ROOT` for script paths.
- `config.py` resolves the plugin manifest at `../.claude-plugin/plugin.json` relative to `scripts/`.
