---
name: memories-curate
description: Curate all GCP Memory Bank memories for the current user by invoking the deployed memory-minion agent — deduplicates, rewrites facts for agent-readability, and maintains display names. A summary is reported.
---

Curate all memories in the GCP Memory Bank by invoking the deployed memory-minion agent (curation runs on the GCP Agent Runtime, not locally).

## Steps

1. Run the deployed curator synchronously and capture its summary:
   ```bash
   python3 ~/.claude/scripts/memory-bank/nudge_minion.py --wait
   ```
2. The script prints a JSON summary like `{"reviewed": N, "updated": N, "deleted": N, "named": N}`. Report to the user:
   `Curated N memories: X rewritten, Y duplicates removed, Z named.`

## Rules

- Always surface the summary — this skill is invoked explicitly by the user.
- If the output is an error, or `updated`/`deleted`/`named` are all 0, report: `Curation completed with no changes.`
