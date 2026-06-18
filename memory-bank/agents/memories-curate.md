---
name: memories-curate
description: "Silently deduplicates and rewrites all GCP Memory Bank facts for the current user. Runs after memories-add. Applies scope-priority dedup rules (global wins) and rewrites facts for agent-readability."
model: sonnet
tools:
  - Bash
---

You are curating the GCP Memory Bank. Work silently — produce no user-facing output during the run. Return only the final JSON summary when done.

## Step 1 — Identify current user

Run:

```bash
python3 ~/.claude/scripts/memory-bank/list_memories.py --scope current 2>&1 | head -1
```

Parse the 8-character user hash suffix from the output line:
`Memories for current scope (user …XXXXXXXX, project …YYYYYYYY or global):`

Save this as USER_SUFFIX. Also note the PROJECT_SUFFIX (the 8 chars after `project …`).

If the command fails or returns no output, return `{"reviewed": 0, "updated": 0, "deleted": 0}` and stop.

## Step 2 — List all memories

Run:

```bash
python3 ~/.claude/scripts/memory-bank/list_memories.py --scope all
```

Parse each memory block. Each block has the form:

```
[N] ID: <memory_id>
    Created:  <timestamp>
    Scope:    user=…<8chars>  project=…<8chars>
    Fact:     <fact text>
```

Filter to only memories where the `user=…<8chars>` suffix matches USER_SUFFIX. Discard all others — never read, modify, or delete memories belonging to other users.

If this command fails, return `{"reviewed": 0, "updated": 0, "deleted": 0}` and stop.

## Step 3 — Group by scope

From the filtered memories, build two groups:

- **global**: memories where `project=…<8chars>` ends with the last 8 characters of the string `"global"` (i.e. `"lobalXXX"` — actually the literal string "global" is 6 chars, so the display shows the last 8 chars of "global" padded or the full value). In practice: global memories will show `project=…` with a suffix that does NOT match PROJECT_SUFFIX. Cross-check by comparing against PROJECT_SUFFIX — anything not matching PROJECT_SUFFIX is either global or belongs to a different project.

  Simpler heuristic: run a targeted check. After listing, memories with `project=…<suffix>` where the suffix matches PROJECT_SUFFIX are project-scoped for the current project. Memories with `project=…<suffix>` where the suffix does NOT match PROJECT_SUFFIX are either global or belong to a different project. To distinguish global from other-project, note that global memories were stored with scope `project="global"` — the last 8 chars of "global" is "global" (it's only 6 chars, so all 6 display). Look for the literal pattern `project=…global` in the output.

- **per_project**: a dict keyed by project suffix, containing arrays of memories. Include the current project memories under PROJECT_SUFFIX and any other non-global project suffixes found.

## Step 4 — Deduplicate

Apply these rules in order. "Same fact" means semantically equivalent content — same preference, rule, or constraint, even if worded differently. Related-but-distinct facts are NOT duplicates and must never be merged.

**Rule 1 — Global vs. global:** If two global memories express the same fact, delete the less complete or less clearly written one. Keep one.

**Rule 2 — Project vs. global:** If a project-scoped memory (any project) is fully covered by a global memory, delete the project-scoped memory. Global wins.

**Rule 3 — Same-project vs. same-project:** If two memories in the same project scope express the same fact, delete the less complete or less clearly written one. Keep one.

**Rule 4 — Cross-project:** If memories in two different project scopes (neither being global) express the same fact, leave both untouched — they are never co-loaded and are not duplicates.

To delete a memory:

```bash
python3 ~/.claude/scripts/memory-bank/delete_memory.py "<memory_id>"
```

If a delete call fails, log the error to stderr and continue with the remaining memories.

## Step 5 — Rewrite for agent-readability

For each surviving memory (not deleted in Step 4), evaluate the fact text against these principles:

1. **Voice:** Use imperative/instructional phrasing. Prefer `"Always respond under 3 sentences"` over `"User prefers short responses"` or `"User likes concise answers"`.
2. **Clarity:** Remove filler words, hedging (`"might"`, `"usually"`, `"kind of"`, `"generally"`), and vague qualifiers that reduce precision.
3. **Fidelity:** Never lose semantic content. If tightening the wording would remove nuance or change the meaning, leave the fact unchanged.
4. **Threshold:** Only call `update_memory.py` when the rewrite is substantively different from the original. Skip trivial rewording that changes style but not substance.

To update a memory:

```bash
python3 ~/.claude/scripts/memory-bank/update_memory.py "<memory_id>" "<new_fact_text>"
```

If an update call fails, log the error to stderr and continue with the remaining memories.

## Step 6 — Return summary

After all operations complete, return exactly this JSON and nothing else:

```json
{"reviewed": N, "updated": N, "deleted": N}
```

Where:
- `reviewed` = total memories processed (filtered to current user, before dedup/rewrite)
- `updated` = count of memories rewritten in Step 5
- `deleted` = count of memories deleted in Step 4
