# Memories Curate Agent — Design Spec

**Date:** 2026-06-18
**Status:** SUPERSEDED (2026-07-08) — the client-side `memories-curate` subagent described here has been retired. Curation now runs server-side on the deployed **memory-minion** agent (GCP Agent Runtime; see the `agentic-minions` repo). This plugin only nudges it via `nudge_minion.py`. Kept for historical context.

## Overview

A curator subagent that runs silently after every `memories-add` invocation. It reviews all memories for the current user, deduplicates using scope-priority rules, and rewrites surviving facts for agent-readability. Changes are applied automatically with no user confirmation.

## Goals

- **Primary:** Memories in the bank are written as clear, unambiguous, actionable instructions for an LLM agent.
- **Secondary:** Eliminate redundant memories that would be loaded together in the same session.
- **Non-goal:** Deduplicate cross-project memories (they are never co-loaded, so not duplicates).

## Architecture

### New files

| File | Purpose |
|------|---------|
| `agents/memories-curate.md` | Agent definition with encoded dedup rules and rewriting principles |
| `skills/memories-curate/SKILL.md` | Standalone skill wrapper — surfaces summary to user |

### Modified files

| File | Change |
|------|--------|
| `skills/memories-add/SKILL.md` | Step 4: spawn curator via `Agent` tool, discard result silently |

### Data flow

```
/memories-add
  → add_memory.py              (adds the new memory)
  → Agent(memories-curate)     (spawned silently, result discarded)
      → list_memories.py --scope all
      → Phase 1: group by scope
      → Phase 2: deduplicate
      → Phase 3: rewrite
      → update_memory.py × N   (rewrites)
      → delete_memory.py × N   (removed duplicates)
      → returns {reviewed: N, updated: N, deleted: N}
```

The curator always reviews the full memory set — not just the newly added memory — so prior uncurated memories are cleaned up incrementally over time.

## Curator Agent Logic

### Phase 1 — List & Group

Call `python3 ~/.claude/scripts/memory-bank/list_memories.py --scope all` and parse the output into two groups:

- `global[]` — memories where `project == "global"`
- `per_project{project_hash → []}` — all other memories, keyed by project hash

### Phase 2 — Deduplicate

Apply rules in this priority order. "Same fact" is determined by semantic equivalence — exact wording is not required, but the memories must express the same preference, rule, or constraint. Related-but-distinct facts are never merged.

| Rule | Condition | Action |
|------|-----------|--------|
| Global vs. global | Two global memories cover the same fact | Keep the more complete/clearer one; delete the other |
| Project vs. global | A project-scoped memory is semantically covered by a global memory | Delete the project-scoped one (global wins) |
| Project vs. same project | Two memories in the same project scope cover the same fact | Keep the more complete/clearer one; delete the other |
| Cross-project | Two memories in different project scopes cover the same fact | Skip — they are never co-loaded, not a duplicate |

### Phase 3 — Rewrite

For each surviving memory, evaluate the fact text against these principles:

- **Voice:** Use imperative/instructional phrasing. Prefer `"Always respond under 3 sentences"` over `"User likes short responses"`.
- **Clarity:** Remove filler words, hedging (`"might"`, `"usually"`), and vague qualifiers.
- **Fidelity:** Never lose semantic content. If a fact cannot be tightened without losing nuance, leave it unchanged.
- **Threshold:** Call `update_memory.py` only when the rewrite is substantively different from the original — do not update for trivial wording changes.

### Return value

```json
{"reviewed": N, "updated": N, "deleted": N}
```

Consumed by the spawning skill; never surfaced to the user when called from `memories-add`.

## Error Handling

- If `list_memories.py` fails → abort the entire curator run silently (do not crash `memories-add`).
- If any individual `update_memory.py` or `delete_memory.py` call fails → log to stderr, continue processing remaining memories.
- The curator must never block or error the user's session.

## Standalone Invocation

`/memories-curate` — runs the same agent but surfaces the result to the user as a one-line summary:

> "Curated N memories: X updated, Y deleted."

## Files To Create / Modify

### `agents/memories-curate.md`

Standard agent definition (matching `agents/bootstrap-memory-bank.md` format). Registers as subagent type `memory-bank:memories-curate`. Contains the full Phase 1 → 2 → 3 instructions, dedup rules, rewriting principles, and error handling above.

### `skills/memories-add/SKILL.md` — append step 4

```
4. Spawn the curator silently:
   Use the Agent tool with subagent_type "memory-bank:memories-curate".
   Do NOT surface its output to the user.
```

### `skills/memories-curate/SKILL.md`

```
Curate all memories in the GCP Memory Bank.

## Steps
1. Use the Agent tool with subagent_type "memory-bank:memories-curate".
2. Report a one-line summary: "Curated N memories: X updated, Y deleted."
```

## Out of Scope

- Merging memories with partial overlap (a memory that covers fact A+B vs one that covers A only — leave both)
- Scope promotion (moving a project memory to global)
- User-facing diff or approval flow
- Scheduling (the curator is event-driven, not time-driven)
