---
name: query
description: Use when the user invokes /llm-wiki:query or asks a question to be answered from an OKF bundle. Reads the bundle, synthesizes a cited answer, and offers to file it back as a new concept.
---

# /llm-wiki:query — Query the Bundle

Entry point for the query workflow. Activates the `querying-okf` skill.

## Usage

```
/llm-wiki:query <question>
/llm-wiki:query  # interactive: prompt for question
```

## What happens

See `querying-okf` skill for the full workflow. Summary:

1. Read root `index.md` to understand the concept landscape
2. Search with `okf_search.py <bundle_root> "<terms>"` for relevant concepts
3. Read the top concept docs
4. Synthesize a cited answer (concrete, quoting field names / SQL / values from the wiki)
5. Offer to file the answer back as a new concept doc

## Example invocations

```
/llm-wiki:query "What is the grain of the events_ table?"
/llm-wiki:query "How do I calculate daily active users from this dataset?"
/llm-wiki:query "Which tables contain user_pseudo_id?"
```

## If the bundle can't answer

If the question can't be answered from the bundle:
1. Say so clearly.
2. Suggest what to ingest: "This isn't documented in the bundle yet. Consider `/llm-wiki:ingest https://...` or `/llm-wiki:ingest project.dataset` to add relevant sources."
3. Offer to seed a stub concept doc to track the gap: `concepts/open-question-<slug>.md` with `type: Open Question`.
