---
name: enrich
description: Use when the user invokes /llm-wiki:enrich or asks to re-enrich specific concept docs. Re-authors the named concepts (or all concepts if none specified), one doc per concept, following authoring-concepts.
---

# /llm-wiki:enrich — Re-enrich Concept Docs

Re-runs enrichment on specific concepts (or all). Each concept is re-authored by following the `authoring-concepts` skill. Useful for refreshing stale docs after a source schema change.

## Usage

```
/llm-wiki:enrich [concept-id…]
```

Without arguments, re-enriches ALL concepts in the bundle.

## Steps

1. If concept IDs are specified, use them directly. Otherwise, walk the bundle and collect all concept IDs (from non-reserved `.md` files with a `type` field).

2. For each concept ID, read the existing doc:
   ```bash
   python3 <plugin_root>/scripts/okf_doc.py read <bundle_root> <concept_id>
   ```

3. Determine the source for fresh metadata:
   - If the concept has a `resource` URI pointing to BigQuery, use `okf_bq.py describe`.
   - For other concepts, re-read the raw source if available in `raw/`.
   - If no live source is available, enrich from the existing doc + context alone.

4. Author each concept by following `authoring-concepts` — read existing doc, get fresh raw metadata, write the augmented doc via `okf_doc.py write` (the PostToolUse hook validates each write). Dispatch per the runtime: on Claude Code fan out one `general-purpose` subagent per concept to run them in parallel; on Antigravity, which cannot invoke dispatchable subagents, do them sequentially. See `ingesting-sources` § Per-concept dispatch for the shared contract.

5. Report: N docs updated, M unchanged, any errors.

6. Suggest `/llm-wiki:index` to regenerate indexes after bulk updates.

## Limiting scope

To re-enrich just one table:
```
/llm-wiki:enrich tables/events_
```

To re-enrich all reference docs:
```
/llm-wiki:enrich references/metrics/dau references/joins/events___users
```
