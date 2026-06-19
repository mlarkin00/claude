---
name: stats
description: Use when the user invokes /llm-wiki:stats or asks for statistics about an OKF bundle. Runs okf_stats.py and presents the results clearly.
---

# /llm-wiki:stats — Bundle Statistics

Quick mechanical stats without the full semantic audit. Use for a fast health snapshot.

## Usage

```
/llm-wiki:stats [path]
```

## Steps

Run:
```bash
python3 <plugin_root>/scripts/okf_stats.py <bundle_root>
```

Output JSON:
```json
{
  "total_concepts": 12,
  "by_type": {"BigQuery Dataset": 1, "BigQuery Table": 4, "Reference": 7},
  "total_links": 34,
  "orphans": ["references/metrics/ltv"],
  "broken_links": [{"from": "tables/events_", "to": "references/event_parameters"}],
  "citation_coverage": "9/12"
}
```

Present this as a readable summary:

```
OKF Bundle Stats — <path>
  12 concepts: 4 BigQuery Table, 7 Reference, 1 BigQuery Dataset
  34 internal links
  1 orphan (not linked from anywhere): references/metrics/ltv
  1 broken link: tables/events_ → references/event_parameters (missing)
  Citation coverage: 9/12 (75%)
```

For orphans or broken links, suggest:
- Orphan: "Link it from a related concept, or remove it if it's no longer relevant."
- Broken link: "Create the missing concept doc or fix the link path."

For a full semantic audit including contradictions and staleness, use `/llm-wiki:lint`.
