---
name: auto-mode
description: Use when the user invokes `/auto <task>` or says "run autonomously", "do it end-to-end", "no prompts", "auto mode". Plan-driven autonomous execution — agent writes a full plan, batches all clarifying questions up front, then executes phase-by-phase without further prompting. Tests after every phase. Records summary + learnings back into the plan doc.
---

# Auto

## Overview

User hands off scoped work. Agent plans the entire scope, collects ALL needed input once, then executes autonomously phase-by-phase. No mid-execution prompts unless genuine blocker. Tests after every phase. Plan doc carries the audit trail.

**Announce at start:** "Using `auto` skill. Drafting plan now."

## Trigger

- `/auto <task description>`
- "run this autonomously", "do it end-to-end without asking", "auto mode"

## The Process

### Phase 0: Draft Plan

1. Derive `<title>` from request — kebab-case, ≤6 words.
2. Resolve `<datestamp>` = today, `YYYY-MM-DD`.
3. Write plan to `docs/agent-workflow/plans/<datestamp>-<title>.md` if dir exists, else `auto-plans/<datestamp>-<title>.md` (create dir).
4. Plan MUST use the template in [Plan Document Format](#plan-document-format) below.
5. Decompose scope into phases. Each phase: independent deliverable + test step. Mark which tasks within a phase can run in parallel (no shared file/state dependency).

### Phase 1: Batch Clarification (ONE round only)

After plan drafted, scan for unknowns:

- Ambiguous requirements
- Missing credentials / external resource IDs
- Choice points with no clear default
- Anything that could cause rework mid-execution

**Bundle ALL questions into a single `AskUserQuestion` call.** No drip-feed. If zero genuine unknowns → skip this phase, proceed.

After user answers, update plan doc with resolved decisions in the "Decisions" section. From here forward: NO further prompts unless blocker per [Stop Conditions](#stop-conditions).

### Phase 2..N: Execute Phases

For each phase in plan:

1. Mark phase `in_progress` (TaskCreate / TodoWrite).
2. Execute tasks. **Run independent tasks in parallel** — dispatch parallel agents (see `dispatching-parallel-agents` skill) or batch independent tool calls in one message.
3. Run the phase's test step. Capture output.
4. If test fails → diagnose, retry up to 2 attempts. Still failing → STOP per [Stop Conditions](#stop-conditions).
5. Append **Phase N Summary** block to plan doc: what changed, files touched, test result, notes/learnings, blockers hit.
6. Mark phase complete. Move to next phase.

### Final Phase: Work Summary

After all phases pass:

1. Append `## Work Summary` section to plan doc covering full scope: deliverables, files changed, tests run, decisions made, learnings, follow-ups.
2. Report to user: plan path, phases completed, summary headline.

## Guardrails (HARD RULES)

1. **No mid-execution prompts.** Only ask at Phase 1 (batched) or at a Stop Condition.
2. **No design changes outside plan.** If implementation reveals architectural concern → log in Phase Summary, do NOT refactor.
3. **No deletions outside plan.** Files / components / fields stay unless plan explicitly removes them.
4. **Parallelize by default.** Tasks with no shared state MUST run concurrently.
5. **Test gate per phase.** Skipping the test step is forbidden.
6. **Plan is source of truth.** Drift from plan → update plan first, then code.

## Stop Conditions

Halt and ask the user only when:

- Test fails after 2 retries with no clear path forward.
- Plan instruction is ambiguous AND no safe default exists.
- Discovery reveals scope outside the plan (new design decision needed).
- Destructive / irreversible action not authorized by plan (delete data, force-push, drop table).
- Missing credential / external dependency that wasn't surfaced in Phase 1.

When stopping: state the phase, the blocker, options, recommended path. Resume autonomous after answer.

## Plan Document Format

```markdown
# <Title> — Auto Plan

**Date:** YYYY-MM-DD
**Mode:** auto (autonomous execution)
**Source request:** <verbatim user input>

## Goal

<one sentence>

## Scope

In:

- ...
  Out:
- ...

## Decisions

<filled after Phase 1 clarification, or "none required">

## Phases

### Phase 1: <name>

**Parallelizable:** yes/no
**Tasks:**

- [ ] Task 1.1 — files: `path/x.ts`
- [ ] Task 1.2 — files: `path/y.ts` (parallel with 1.1)
      **Test:** `<exact command + expected result>`

### Phase 2: <name>

...

## Phase Summaries

<appended during execution>

## Work Summary

<appended at end>
```

## Parallel Execution Rules

A task pair is parallel-safe when:

- They touch disjoint files, AND
- Neither reads output the other produces, AND
- They don't compete for the same external resource (port, lock, single-writer DB row).

When parallel: dispatch via single message with multiple Agent / tool calls. Mark in plan as `(parallel with X.Y)`.

When NOT parallel: serial with explicit dependency note `(depends on X.Y)`.

## Integration

- **writing-plans** — reuse plan structure conventions when drafting.
- **dispatching-parallel-agents** — use when phase has 2+ independent worker tasks.
- **executing-plans** — `auto` is a stricter, non-interactive variant; don't chain.
- **verification-before-completion** — apply at each phase test step before marking complete.

## Remember

- Plan first, ask once, execute silent.
- Test after every phase. No exceptions.
- Parallel where safe. Serial only when forced.
- Phase summaries land in the plan doc, not chat.
- Stop only on real blockers — guess never, ask once when forced.
