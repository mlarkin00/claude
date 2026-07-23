## Project Goal

GCP-backed long-term memory for Claude Code. At session start, fetch global and project-scoped facts from the Vertex AI Reasoning Engine Memory Bank and inject them into context. At session end, extract and consolidate new facts from the transcript. Provides manual CRUD skills for direct memory management.

## Project Context

Claude Code plugin in the `mlarkin00/plugins` monorepo (remote: `https://github.com/mlarkin00/plugins`). Equivalent of the Gemini CLI `gcp-memory-bank` plugin (`~/agent-skills/plugins/memory-bank`).

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

# Run tests (stdlib unittest — no pytest required)
python3 -m unittest discover -s tests -v
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
- `load_context.py` emits the **caller's** hook shape and defaults to Claude Code's: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<long_term_memories>..."}}`, or `{}` when there is nothing to inject. `--format agy` switches it to `{"injectSteps": [{"ephemeralMessage": ...}]}`, and only `agy_load_context.py` passes it. The wrong shape is injected as nothing while the hook still exits 0, so a change here MUST assert both shapes and that the injected field is non-empty — see `.agents/wiki/cross-runtime/hook-output-protocols.md` in the repo root.
- `save_context.py` reads Claude Code transcript format: `{"role": "user"|"assistant", "content": string|[{type,text}]}`.
- `sidecar_consolidate.py` runs at most once per 24 hours (`--force` bypasses; state in `~/.cache/memory-bank/.sidecar_state.json`). Two phases: (1) semantic curation — fetches the user's memories, calls Gemini 3.5 Flash (`https://aiplatform.googleapis.com/v1/.../locations/global/...`) to semantically deduplicate (scope-priority: global wins) and rewrite facts for agent-readability; (2) bulk consolidation — walks `~/.claude/projects/**/*.jsonl` and sends all turns to `memories:generate`.
- `config.py` reads `.claude-plugin/plugin.json` first, falls back to env vars. MUST use `os.path.realpath(__file__)` (not `abspath`) — symlinks via `~/.claude/scripts/memory-bank/` will return empty config if `abspath` is used.
- Skills MUST resolve the scripts directory at run time rather than hardcoding one — the plugin lives somewhere different per runtime. The candidates, in precedence order, are `~/.claude/scripts/memory-bank` (the version-free symlink `install-symlinks.sh` maintains on Claude Code), `~/.gemini/config/plugins/memory-bank/scripts` (Antigravity), then `~/.claude/plugins/cache/*/memory-bank/*/scripts` as a last resort. Three constraints make that shape non-negotiable: `$CLAUDE_PLUGIN_ROOT` is populated for hooks only and is **empty** in a command the model runs; `ls a b c | head -1` does not honour argument order because `ls` sorts, which silently selects a stale cached copy; and a one-liner using `$(…)` is auto-denied in a headless Antigravity session, so the lookup and the call must be two plain commands.
- Plugin MUST be registered in root `marketplace.json` before release.
- NEVER hardcode user-specific paths; use `os.path.expanduser('~')` or `$HOME`.
