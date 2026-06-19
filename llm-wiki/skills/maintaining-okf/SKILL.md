---
name: maintaining-okf
description: Use when performing semantic health checks on an OKF bundle — finding contradictions, stale claims, orphan pages, missing cross-references, and concepts mentioned but not yet written. Pairs with okf_stats.py for mechanical findings.
---

# Maintaining an OKF Bundle (Lint / Health)

This skill implements Karpathy's "Lint" operation: the LLM reads the wiki and identifies semantic health issues that mechanical tools can't catch.

Pair with `okf_stats.py` for mechanical stats (orphans, broken links, citation coverage). The `okf-linter` agent runs a deep semantic audit.

## What to look for

**Semantic issues** (judgment required — mechanical tools can't catch these):

1. **Contradictions** — two concept docs that make conflicting claims. Example: one doc says "event_name is always lowercase" and another says "event_name preserves original casing."
2. **Stale claims** — factual assertions that may be outdated (e.g. "the schema has 12 fields" but the current schema has 15; a "current version" claim with an old timestamp).
3. **Orphan pages** — concept docs that are never cross-linked from anywhere, making them invisible in practice.
4. **Concepts mentioned but not written** — the prose in existing docs mentions a concept by name (e.g. "the `user_properties` RECORD") but no dedicated concept doc for it exists.
5. **Missing cross-references** — two related concepts that should link to each other but don't.
6. **Data gaps** — concepts with thin descriptions, no examples, no citations, or a `# Schema` that is clearly incomplete.
7. **Type inconsistencies** — the same real-world entity called different `type` values in different docs (e.g. `Reference` vs `Article` for the same kind of thing), indicating the type vocabulary has drifted.

## Workflow

```
/llm-wiki:lint
  1. okf_stats.py → mechanical findings (orphans, broken links, citation coverage)
  2. okf-linter agent → deep semantic audit of the whole bundle
  3. Synthesize a prioritized fix-it report (Critical / Moderate / Minor)
  4. Offer to fix specific items inline, or save the report to a concept doc
```

## Fix-it report format

For each finding:
```
[SEVERITY] <short title>
  File: <concept_id>
  Issue: <one-sentence description>
  Suggested fix: <concrete action>
```

SEVERITY levels:
- **Critical**: conformance violation, broken link to a referenced concept, direct contradiction
- **Moderate**: stale claim, missing cross-ref for a high-traffic concept, orphan with inbound mentions elsewhere
- **Minor**: thin description, missing citation, stylistic inconsistency

## After linting

After applying fixes:
1. Re-run `/llm-wiki:validate` to confirm conformance.
2. Run `/llm-wiki:index` to regenerate indexes.
3. Use `/llm-wiki:log` to record the lint pass: `Fixed N findings (M critical, L minor). Ran on <date>.`
