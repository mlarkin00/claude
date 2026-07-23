---
name: lint
description: Use when the user invokes /llm-wiki:lint or asks for a health check on an OKF bundle. Runs mechanical stats via okf_stats.py and the semantic audit from maintaining-okf, then produces a prioritized fix-it report.
---

# /llm-wiki:lint — Bundle Health Check

Combines mechanical stats (`okf_stats.py`) with the semantic audit from the `maintaining-okf` skill into a prioritized fix-it report.

## Usage

```
/llm-wiki:lint [path]
```

`path` defaults to the nearest bundle root.

## Steps

1. **Mechanical stats** (always run first):
   ```bash
   python3 <plugin_root>/scripts/okf_stats.py <bundle_root>
   ```
   Reports: concept count by type, total links, orphans, broken links, citation coverage.

2. **Conformance check**:
   ```bash
   python3 <plugin_root>/scripts/okf_validate.py <bundle_root>
   ```

3. **Semantic audit** — run the audit procedure in the `maintaining-okf` skill for the deep read (what to look for, the rules, and the findings shape). On Claude Code you may dispatch it into a `general-purpose` subagent to isolate a large bundle read; on Antigravity run it inline.

4. **Synthesize** the combined report:

   ```
   ## OKF Bundle Health Report — <path>
   ### Stats
   - N concepts (A BigQuery Table, B Reference, ...)
   - N links, N orphans, N broken links
   - Citation coverage: N/M

   ### Critical (fix before sharing)
   [1] Broken link: tables/events_ → references/event_parameters.md (file not found)
       Fix: create the missing reference doc or remove the link.

   ### Moderate
   [2] Orphan: references/metrics/ltv.md — not linked from any concept doc.
       Fix: add a link from tables/users.md or tables/events_.md.

   ### Minor
   [3] Thin description: datasets/crypto_bitcoin.md — description is 3 words.
       Fix: expand to one tight sentence about what this dataset is.
   ```

5. **Offer to fix** specific Critical issues inline, or save the full report:
   > "Should I fix issue [1] now, or save this report to `concepts/lint-report-2026-06-19.md`?"

## After fixing

```
/llm-wiki:validate   — confirm all violations are resolved
/llm-wiki:index      — regenerate indexes if docs were added/removed
/llm-wiki:log        — record the lint pass
```
