## Project Goal

GCP-backed long-term memory for Claude Code. Fetches global and project-scoped facts from Vertex AI Reasoning Engine Memory Bank at session start; consolidates new facts at session end.

## Project Context

Claude Code plugin in `mlarkin00/plugins` monorepo. Port of `~/agent-skills/plugins/memory-bank` (Gemini CLI).
Python 3 stdlib only · GCP Vertex AI Memory Bank API · ADC auth.

Config: `.claude-plugin/plugin.json` (`config.project/location/reasoning_engine_id`); env-var fallback: `GCP_PROJECT`, `GCP_LOCATION`, `GCP_REASONING_ENGINE`.

## Operational Commands

```bash
echo '{}' | python3 scripts/load_context.py          # test session-start injection
python3 scripts/list_memories.py                      # list current-scope memories
python3 scripts/add_memory.py "fact" --scope global   # add a memory
python3 scripts/sidecar_consolidate.py --force        # force daily consolidation
python3 -m unittest discover -s tests -v              # run tests (stdlib unittest, no pytest required)
```

## Style & Conventions

- Python 3 stdlib only.
- Single-responsibility scripts; import helpers via `sys.path.insert`.
- All network calls MUST have timeouts + graceful error handling.
- Default scope: ALWAYS `global`.

## Architecture & Constraints

- `load_context.py` → `{"injectSteps": [{"ephemeralMessage": "<long_term_memories>..."}]}`.
- `save_context.py` → Claude Code transcript format: `role: user/assistant`, content as string or list.
- `sidecar_consolidate.py` → ≤once/24h, walks `~/.claude/projects/**/*.jsonl`.
- `config.py` → reads `../.claude-plugin/plugin.json` via `os.path.realpath(__file__)` — MUST be `realpath`, not `abspath`; symlinks break `abspath`.
- Hook commands use `$CLAUDE_PLUGIN_ROOT`.
- Skills call scripts via `~/.claude/scripts/memory-bank/`.
