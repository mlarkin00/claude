---
name: ingest
description: Use when the user invokes /llm-wiki:ingest or asks to ingest a source into an OKF bundle. Detects source type, routes to the right adapter, runs the supervised ingest loop.
---

# /llm-wiki:ingest — Ingest a Source into the Bundle

Entry point for the supervised ingest loop. Detects the source type and delegates to the appropriate adapter skill.

## Usage

```
/llm-wiki:ingest <source> [--auto]
/llm-wiki:ingest <source1> <source2> ... [--auto]
```

`--auto`: skip review pauses; author across all sources without stopping; one review at the end.

## Source type detection

| Input | Routes to |
|---|---|
| `project.dataset` (contains exactly one `.`) | `ingesting-bigquery` |
| URL starting with `http://` or `https://` | `ingesting-web` |
| Local path to a file or directory | Direct read → `authoring-concepts` |
| `seeds.txt` or `seeds.example.txt` | `ingesting-web` (file of seed URLs) |

## What happens

See `ingesting-sources` skill for the full supervised loop. Summary:

1. Detect source → activate the appropriate skill
2. Adapter lists concepts → **show plan to owner → wait for confirmation**
3. Author each concept (see `ingesting-sources` § Per-concept dispatch) — parallel subagents on Claude Code, sequential on Antigravity
4. Report diff summary → **wait for owner review**
5. If multiple sources: proceed to the next only after owner go
6. Suggest `/llm-wiki:index` and `/llm-wiki:log`

## With `--auto`

Skip pauses. Author all concepts without stopping — concurrently where the runtime can dispatch subagents (Claude Code), otherwise sequentially (Antigravity). Present one consolidated review at the end. Use when you trust the source and want unattended batch processing.

## After ingest

Always remind the owner to:
```
/llm-wiki:index   — regenerate index.md files
/llm-wiki:log     — record what was ingested
/llm-wiki:validate — confirm conformance
```
