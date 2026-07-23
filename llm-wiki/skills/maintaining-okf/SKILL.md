---
name: maintaining-okf
description: Use when performing semantic health checks on an OKF bundle — finding contradictions, stale claims, orphan pages, missing cross-references, and concepts mentioned but not yet written. Pairs with okf_stats.py for mechanical findings.
---

# Maintaining an OKF Bundle (Lint / Health)

This skill implements Karpathy's "Lint" operation: the LLM reads the wiki and identifies semantic health issues that mechanical tools can't catch.

Pair with `okf_stats.py` for mechanical stats (orphans, broken links, citation coverage). This skill is the deep semantic audit itself — the procedure below reads the bundle and produces the findings. It replaces the retired `okf-linter` agent; run it inline, or on Claude Code dispatch it into a `general-purpose` subagent for an isolated read of a large bundle. On Antigravity, run it inline (there are no dispatchable subagents).

## What to look for

**Semantic issues** (judgment required — mechanical tools can't catch these):

1. **Contradictions** — two concept docs that make conflicting claims. Example: one doc says "event_name is always lowercase" and another says "event_name preserves original casing."
2. **Stale claims** — factual assertions that may be outdated (e.g. "the schema has 12 fields" but the current schema has 15; a "current version" claim with an old timestamp).
3. **Orphan pages** — concept docs that are never cross-linked from anywhere, making them invisible in practice.
4. **Concepts mentioned but not written** — the prose in existing docs mentions a concept by name (e.g. "the `user_properties` RECORD") but no dedicated concept doc for it exists.
5. **Missing cross-references** — two related concepts that should link to each other but don't.
6. **Data gaps** — concepts with thin descriptions, no examples, no citations, or a `# Schema` that is clearly incomplete.
7. **Type inconsistencies** — the same real-world entity called different `type` values in different docs (e.g. `Reference` vs `Article` for the same kind of thing), indicating the type vocabulary has drifted.

## Audit procedure

Run this to produce the semantic findings (it is what the `okf-linter` agent
used to do):

1. **Read the root `index.md`** to understand the bundle structure.
2. **Read every concept doc**, walking subdirectories. For a large bundle
   (>50 docs), prioritize primary concept docs (tables, datasets) over
   reference docs.
3. **Identify findings** across the seven categories above. Rules that keep the
   audit honest:
   - Only report findings you are confident about from reading the docs — do not
     speculate.
   - For a **stale claim**, compare it against other evidence *in the bundle*
     (e.g. count the actual `# Schema` fields), never against your training data.
   - For a **missing concept**, only flag concepts explicitly named in existing
     prose, not concepts you think ought to exist.
4. **Return structured findings** so the caller can synthesize a report:

```json
{
  "findings": [
    {
      "severity": "critical|moderate|minor",
      "category": "contradiction|stale|orphan|missing-concept|missing-xref|data-gap|type-inconsistency",
      "concept_id": "tables/events_",
      "title": "Contradictory case-sensitivity claim",
      "description": "tables/events_.md says event_name is always lowercase, but references/event_parameters.md says it preserves original casing.",
      "suggested_fix": "Check the BigQuery schema description; likely always lowercase. Update references/event_parameters.md."
    }
  ],
  "summary": { "total": 5, "critical": 1, "moderate": 2, "minor": 2 }
}
```

## Workflow

```
/llm-wiki:lint
  1. okf_stats.py → mechanical findings (orphans, broken links, citation coverage)
  2. Run the audit procedure above → deep semantic findings for the whole bundle
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
