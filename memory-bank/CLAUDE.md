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
python3 scripts/graduate_memories.py --dry-run        # preview remember→memory graduation (no writes)
python3 scripts/graduate_memories.py --force          # force weekly graduation
python3 scripts/resolve_remember.py                   # list discovered remember directories with content
python3 -m unittest discover -s tests -v              # run tests (stdlib unittest, no pytest required)
```

## Style & Conventions

- Python 3 stdlib only — no pip installs.
- Single-responsibility scripts; import `config.py` + `resolve_scope.py` via `sys.path.insert`.
- All network calls MUST have timeouts and graceful exception handling — hooks must never crash the session.
- Default scope: ALWAYS `global`. Use `project` only on explicit user request.

## Architecture & Constraints

- `load_context.py` outputs `{"injectSteps": [{"ephemeralMessage": "<long_term_memories>..."}]}`.
- `save_context.py` handles Claude Code transcript fields: `role: user/assistant`, content as string or list of `{type, text}` blocks.
- `sidecar_consolidate.py` runs ≤once/24h (`--force` bypasses). Three phases: (1) semantic curation — lists user's memories, calls Gemini 3.5 Flash to deduplicate and rewrite; (2) bulk consolidation — walks `~/.claude/projects/**/*.jsonl` and sends to `memories:generate`; (3) **graduation** — calls `graduate_memories.py` on a weekly rate-limit (`--force-graduate` bypasses independently).
- `graduate_memories.py` reads remember's compressed files (`archive.md`, `recent.md`) via `resolve_remember.py`, calls Gemini Flash to classify stable facts (user/feedback/project/reference), and promotes them to both memory-bank (GCP API) and agent-memory (`~/.claude/memory/*.md` + git commit/push). Weekly rate-limit stored in `~/.cache/memory-bank/.graduation_state.json`. `today-*.md` files are intentionally excluded (too fresh).
- `resolve_remember.py` discovers remember directories: checks `.remember/` in cwd (legacy mode) and `~/.remember/*/` (external mode). Only returns dirs with non-empty content files.
- Skills call scripts via `~/.claude/scripts/memory-bank/<script>.py` (symlinked by `install-symlinks.sh`).
- Hook commands use `$CLAUDE_PLUGIN_ROOT` for script paths.
- `config.py` resolves the plugin manifest at `../.claude-plugin/plugin.json` using `os.path.realpath(__file__)` — MUST stay `realpath`, not `abspath`; `abspath` breaks when scripts are invoked via `~/.claude/scripts/memory-bank/` symlinks.
