---
name: log
description: Use when the user invokes /llm-wiki:log or asks to append an entry to the OKF bundle log. Appends a dated entry to log.md (newest first).
---

# /llm-wiki:log — Append a Bundle Log Entry

Appends a dated entry to `log.md` — the chronological, append-only change log for the bundle. Manual operation by design (per Decision 3 in the plugin design).

## Usage

```
/llm-wiki:log <entry>
/llm-wiki:log  # interactive: prompt for entry text
```

## log.md format

```markdown
## 2026-06-19

Added 4 concept docs from bigquery-public-data.crypto_bitcoin (blocks, transactions, inputs, outputs). Web pass seeded from bitcoin.org and cloud.google.com/bigquery/public-data.

## 2026-06-17

Initialized bundle. Defined type vocabulary: BigQuery Dataset, BigQuery Table, Reference.
```

Structure:
- One `## YYYY-MM-DD` heading per calendar day
- Newest entry at the top
- Plain prose under each date heading
- Multiple entries on the same day go under the same date heading, separated by blank lines

## Steps

1. Determine the bundle root (nearest ancestor with root `index.md`).
2. Read the existing `log.md` if it exists.
3. Determine today's date.
4. If today's heading already exists at the top, append the new entry text under it (with a blank line separator).
5. If today's heading does NOT exist, prepend a new `## <date>` section above all existing entries.
6. Write the updated `log.md`.

The `log.md` file is reserved — it does NOT need frontmatter and is skipped by the conformance validator.

## What to log

Good log entries:
- "Ingested `bigquery-public-data.ga4` — 3 tables, 1 dataset. Web pass: 47 pages, 2 reference docs minted."
- "Lint pass: fixed 3 broken cross-links, added missing `# Citations` to 5 docs."
- "Query: 'How does event counting work?' → filed answer as `concepts/event-counting.md`."

The log is for humans and future LLM sessions to understand the bundle's provenance and how it has evolved.
