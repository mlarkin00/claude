## Project Goal

GCP-backed long-term memory for Claude Code. At session start, fetch global and project-scoped facts from the Vertex AI Reasoning Engine Memory Bank and inject them into context. At session end, extract and consolidate new facts from the transcript. Provides manual CRUD skills for direct memory management.

## Project Context

Claude Code plugin in the `mlarkin00/claude` monorepo (remote: `https://github.com/mlarkin00/claude`). Equivalent of the Gemini CLI `gcp-memory-bank` plugin (`~/agent-skills/plugins/memory-bank`).

Tech stack: Python 3 (stdlib only) · GCP Vertex AI Reasoning Engine Memory Bank API · ADC via `gcloud` · bash hook scripts.
Plugin root: `~/claude/memory-bank/`

GCP config: project `845186993936`, location `us-west1`, reasoning engine `2527865193187246080` (hardcoded in `.claude-plugin/plugin.json`; env-var fallback: `GCP_PROJECT`, `GCP_LOCATION`, `GCP_REASONING_ENGINE`).

## Operational Commands

```bash
# Verify ADC
gcloud auth application-default print-access-token > /dev/null && echo OK

# Test context load (session start)
echo '{}' | python3 scripts/load_context.py

# Test context save (session end) — pipe a minimal transcript
echo '{"transcriptPath":"/tmp/test.jsonl","workspacePaths":["."]}' | python3 scripts/save_context.py

# Run sidecar consolidation manually
python3 scripts/sidecar_consolidate.py --force

# Add a test memory
python3 scripts/add_memory.py "Test fact from bootstrap" --scope global

# List current memories
python3 scripts/list_memories.py

# Run tests
cd tests && python3 -m pytest -v
```

## Style & Conventions

- Python 3 stdlib only — no third-party dependencies.
- Each script is single-responsibility; import helpers from `config.py` and `resolve_scope.py`.
- All scripts MUST handle auth failure and network errors gracefully — never crash the session.
- Scripts use `sys.path.insert(0, ...)` to resolve sibling modules; do NOT add `__init__.py`.
- Hook scripts called via `$CLAUDE_PLUGIN_ROOT` must work when stdin is a pipe.
- Default memory scope is ALWAYS `global`; only use `project` when the user explicitly requests it.

## Architecture & Constraints

- Hooks: `SessionStart` → `install-symlinks.sh` then `load_context.py`; `Stop` → `save_context.py` then `sidecar_consolidate.py`.
- `load_context.py` outputs `{"injectSteps": [{"ephemeralMessage": "<long_term_memories>..."}]}` — Claude Code processes this to inject facts into the session context.
- `save_context.py` reads Claude Code transcript format: `{"role": "user"|"assistant", "content": string|[{type,text}]}`.
- `sidecar_consolidate.py` runs at most once per 24 hours (state in `~/.cache/memory-bank/.sidecar_state.json`); walks `~/.claude/projects/**/*.jsonl` for bulk consolidation.
- `config.py` reads `.claude-plugin/plugin.json` first, falls back to env vars.
- Skill scripts are symlinked to `~/.claude/scripts/memory-bank/` by `install-symlinks.sh`; skills call them via `~/.claude/scripts/memory-bank/<script>.py`.
- Plugin MUST be registered in root `marketplace.json` before release.
- NEVER hardcode user-specific paths; use `os.path.expanduser('~')` or `$HOME`.
