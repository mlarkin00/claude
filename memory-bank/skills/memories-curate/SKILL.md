---
name: memories-curate
description: Curate all GCP Memory Bank memories for the current user — deduplicates and rewrites facts for agent-readability. Safe to run at any time; changes are applied silently and a summary is reported.
---

Curate all memories in the GCP Memory Bank.

## Steps

1. Use the Agent tool with subagent_type `memory-bank:memories-curate`.
2. When the agent returns its JSON summary `{"reviewed": N, "updated": N, "deleted": N}`, report to the user:
   `Curated N memories: X rewritten, Y duplicates removed.`

## Rules

- Always surface the summary — this skill is invoked explicitly by the user.
- If the agent returns an error or empty/unparseable result, report: `Curation completed with no changes.`
