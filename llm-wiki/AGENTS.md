# llm-wiki Plugin

## Project Goal

OKF v0.1 knowledge bundle manager for Claude Code. Claude authors and maintains persistent, interlinked markdown wikis. Ingest from BigQuery or the web; query with citations; lint for semantic health. The agent harness (ADK + Gemini) from the upstream source is replaced entirely by Claude natively.

## Project Context

Claude Code plugin (`plugin.json` + `skills/` + `agents/` + `hooks/`). Pure Python scripts for deterministic operations; Claude handles all judgment. No Node.js, no build step.

**Tech stack:** Python 3, PyYAML, markdownify (optional), google-cloud-bigquery (optional), google-genai (optional for `--llm` index mode).

## Operational Commands

```bash
# Validate OKF conformance on a bundle
python3 scripts/okf_validate.py <bundle_root>

# Validate a single file (hook mode — permissive)
python3 scripts/okf_validate.py --file <path>

# Run script self-tests
python3 scripts/okf_doc.py --help
python3 scripts/okf_index.py --help
python3 scripts/okf_visualize.py --help
python3 scripts/okf_bq.py --help
python3 scripts/okf_fetch.py --help
python3 scripts/okf_search.py --help
python3 scripts/okf_stats.py --help

# Validate hook is executable
ls -la hooks/validate-on-write.sh

# Is a bundle actually reachable from a session? (exit 1 = missing or stale)
python3 scripts/okf_discover.py <bundle_root> --check

# Tests (stdlib unittest — pytest is not a dependency)
python3 -m unittest discover -s tests -q
```

## Style & Conventions

- Scripts MUST be standalone CLI tools — no ADK context (`get_context()`, `is_web_pass()`). State via CLI flags or JSON files.
- OKF frontmatter key order: `type`, `resource`, `title`, `description`, `tags`, `timestamp` — enforced in `okf_doc.py` via `_PREFERRED_KEY_ORDER`.
- `timestamp` filled automatically by `okf_doc.py write` if absent (UTC ISO-8601 `timespec="seconds"`).
- Reserved OKF filenames live in one place, `okf_lib/paths.RESERVED_FILENAMES` (`index.md`, `log.md`, `CLAUDE.md`) — never validate, catalog, or overwrite them. Consumers disagreeing about this set is how the per-bundle `CLAUDE.md` ended up listed as a nameless `# Other` entry in the index that every session loads.
- `okf_validate.py --file` (hook mode): skips files with no frontmatter; only errors if frontmatter present but `type` missing.
- YAML serialization: `yaml.safe_dump(sort_keys=False, allow_unicode=True)`.

## Architecture & Constraints

**Deterministic/agentic split (non-negotiable):**

| Layer | What | Who |
|---|---|---|
| `scripts/` | I/O, validation, index gen, BM25 search, HTML viz, web fetch, BigQuery metadata | Python (deterministic) |
| `skills/` | Judgment: ingest routing, enrichment authoring, semantic lint, query synthesis | Claude |
| `agents/` | Autonomous loop tasks: enricher, crawler, linter, source scout | Claude agents |
| `hooks/` | PostToolUse: validates every `.md` write for OKF §9 | Shell + Python |

**Discovery is a first-class feature, not documentation.** A bundle reaches a session only through the host repo's briefing file, and the two runtimes disagree about which file and whether `@` imports expand (verified 2026-07-22 with a codeword fixture: Claude Code 2.1.218 loads `CLAUDE.md` and expands imports but does **not** read `AGENTS.md`; `agy` 1.1.5 loads `AGENTS.md`/`GEMINI.md` but does **not** expand imports; a backticked `` `@path` `` is inert on both). `okf_discover.py` picks the mechanism per file and owns the region between its `<!-- llm-wiki:discovery … -->` markers. The inlined form is a copy, so `/llm-wiki:index` re-runs it with `--sync`. Never replace it with a prose pointer — that is the mechanism this feature exists because it failed.
**No `commands/` directory.** Claude Code surfaces commands as skills, so a `commands/<n>.md` beside a `skills/<n>/SKILL.md` collided on the name and the command won — the skill body, which holds the actual instructions, never loaded. Each skill carries its own `/llm-wiki:<n>` invocation; do not reintroduce wrappers.

**Augmentation guard** (`okf_doc.py write --web-pass`): MUST refuse writes that shrink an existing doc's `# Schema` field count or `# Citations` count. Bypass with `--allow-shrink` only when intentional.

**Four-gate reference test** (web ingest): topic shape → bundle non-duplication → citation test → reuse test. All four gates MUST pass before minting a new `references/` doc.

**Never:**
- Add `google-adk` as a dependency
- Write frontmatter in a different key order than `_PREFERRED_KEY_ORDER`
- Skip the augmentation guard for web-sourced writes
- Hardcode bundle paths — always accept `<bundle_root>` as a CLI argument
