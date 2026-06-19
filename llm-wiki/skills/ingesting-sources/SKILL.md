---
name: ingesting-sources
description: Use when the user wants to ingest a new source into an OKF bundle. Covers source detection, adapter routing, the supervised ingest loop, and the adapter contract for new sources.
---

# Ingesting Sources into an OKF Bundle

This skill covers the **supervised ingest loop**: detect source → adapter lists concepts → review plan → fan out enrichers → review diff → suggest index + log.

## Source detection and adapter routing

| Input pattern | Adapter | Script |
|---|---|---|
| `project.dataset` (BigQuery) | `ingesting-bigquery` skill | `okf_bq.py` |
| URL (`http://`, `https://`) | `ingesting-web` skill | `okf_fetch.py` |
| Local file / directory | Direct read (no script) | — |
| Git repo URL | Future adapter | — |

## The supervised ingest loop

```
/llm-wiki:ingest <source>
  1. Detect source type → pick adapter
  2. Adapter lists candidate concepts → present the plan (create/update N docs) → owner confirms/adjusts
  3. Fan out okf-concept-enricher subagents for THIS source's concepts
       └ each write goes through okf_doc.py (guarded) → PostToolUse hook re-validates
  4. Present a diff summary of touched docs → owner reviews
  5. Proceed to the next source only on the owner's go
  6. Suggest /llm-wiki:index + /llm-wiki:log  (manual, per the plugin's supervised default)

/llm-wiki:ingest <sources…> --auto   → skip pauses; fan out across everything; one review at the end
```

**Always show the plan before writing.** The owner may:
- Trim the concept list (e.g. skip low-priority tables)
- Adjust the concept type vocabulary to match the bundle's CLAUDE.md
- Add or remove seed URLs for the web pass

## The adapter contract

Every source adapter provides three operations:

| Operation | Purpose | Returns |
|---|---|---|
| `list_concepts` | candidate concept IDs + types (+ resource URI, optional hint) | list of concept refs |
| `describe(concept)` | raw structured metadata for one concept | dict of metadata |
| `sample(concept)` *(optional)* | a few example rows when metadata is sparse | list of dicts |

An adapter = one **skill** (routing, judgment) + an optional **script** (deterministic metadata pull via CLI).

**Adding a new source** (PDF folder, OpenAPI spec, Postgres, CSV): write one new `ingesting-<x>` skill (describing source detection and `describe` output) plus optionally an `okf_<x>.py` script. The `authoring-concepts` skill turns raw metadata into conformant prose the same way regardless of source. No core changes.

## Per-concept enricher dispatch

For N concepts, dispatch N `okf-concept-enricher` subagents in parallel:

```
okf-concept-enricher inputs:
  - bundle_root: path to the bundle
  - concept_id: e.g. "tables/users"
  - raw_metadata: JSON from adapter describe()
  - existing_doc: JSON from okf_doc.py read (null if new)
  - concepts_list: JSON from bundle's index.md (for cross-link targets)

Output: one write via okf_doc.py → validated by PostToolUse hook
```

For large datasets (>~10 concepts), present a progress summary after each batch of ~5 rather than waiting for all.

## Review before proceeding

After each source is ingested, show:
- N docs created, M docs updated
- List of written concept IDs
- Any augmentation guard refusals (with reason)
- Suggested next steps: `/llm-wiki:index` to regenerate `index.md` files, `/llm-wiki:log` to record the ingest

The owner reviews before moving to the next source.
