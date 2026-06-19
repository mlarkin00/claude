---
name: querying-okf
description: Use when answering a question from an OKF bundle. Read the index first, drill into relevant concept docs, synthesize a cited answer, and offer to file the answer back into the bundle as a new concept so explorations compound.
---

# Querying an OKF Bundle

This skill implements Karpathy's "Query" operation: read the wiki, synthesize a cited answer, optionally file it back.

## Workflow

```
/llm-wiki:query "<question>"
  1. Read bundle root's index.md to understand the concept landscape
  2. Identify the most relevant concepts by type / title / description
  3. Read those concept docs in full
  4. Follow relevant cross-links (one hop) if needed for context
  5. Synthesize a cited answer
  6. Offer to file the answer back as a new concept
```

## Reading the bundle

Start with the root `index.md` — it groups concepts by type and links to every concept. Use `okf_search.py` for keyword lookup:

```bash
python3 <plugin_root>/scripts/okf_search.py <bundle_root> "<keywords>" --k 10
```

For complex questions, read the `CLAUDE.md` at the bundle root first — it explains the bundle's domain, type vocabulary, and conventions.

## Synthesizing the answer

- Be concrete. Quote field names, enum values, SQL snippets from the wiki rather than paraphrasing them.
- **Cite every factual claim** by linking to the concept doc it came from.
- Format: prose answer, then a `## Sources` section listing the concept IDs read.
- If the question can't be answered from the bundle, say so and suggest what to ingest.

## Filing the answer back

After answering, offer:

> "Would you like me to file this answer as a concept doc in the bundle? It would be saved as `concepts/<slug>.md` with `type: Q&A` (or whatever type fits your vocabulary) so future queries can find it."

If the owner says yes:
1. Pick a concept ID that fits the bundle structure (follow the `CLAUDE.md` conventions).
2. Write the concept doc via `authoring-concepts` / `okf_doc.py write`.
3. Cross-link from relevant existing concepts where natural.
4. Suggest `/llm-wiki:index` and `/llm-wiki:log`.

This is the core of the compounding wiki pattern: every answered question makes the wiki more complete.

## Example

User: "How does the events_ table relate to users?"

Steps:
1. Read `index.md` → identify `tables/events_` and `tables/users`.
2. Read both concept docs.
3. Check `references/joins/` for any join reference.
4. Synthesize: "The `events_` table links to `users` via `user_pseudo_id` — see `references/joins/events___users.md` for the canonical ON clause."
5. Offer to file `concepts/events-users-relationship.md`.
