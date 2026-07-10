# Memory Discipline — Default Template

This template applies to projects using the **agentic-minions T0-T4 memory system** (working → task state → session workspace → project brain → long-term learning). When a project has adopted that system, the agent briefing (`AGENTS.md`) MUST include a **Memory Discipline** section. Copy this template in, fill the project-specific paths, and keep the MANDATORY mandates verbatim.

**Do NOT use this template for the user-level agent-memory plugin** (`~/.claude/memory/`). That system is managed automatically via hooks and requires no per-project documentation in `AGENTS.md`.

Detect agentic-minions T0-T4 adoption by the presence of any of:

- `agentic-minions-memory/` directory in the project
- a `maintaining-agent-memory` role, skill, or instruction file
- a `LongTerm` / `MemoryStore` interface in the harness
- `docs/designs/*memory*.md` that describes the T0-T4 tier architecture

If any are present, the **Memory Discipline** section is required.

---

## Template — paste into AGENTS.md (and tune only the <PROJECT-SPECIFIC> markers)

```markdown
## Memory Discipline (MANDATORY)

This project runs a tiered memory system (T0 working · T1 task state · T2 session workspace · T3 project brain · T4 long-term learning). See `@<PATH-TO-MEMORY-DESIGN-DOC>`. The mandates below apply to **every** agent session and **every** task. They are non-negotiable.

### Session start — absolute mandates

1. **MEMORY.md MUST be loaded into the working prompt at session start. No exceptions.** The T4 index (`<MEMORY-REPO>/MEMORY.md`, ≤25KB, ≤100 entries) is injected as part of Layer 1 of the prompt. If the fetch fails, proceed with the last cached index and emit a degraded-mode warning — but never start a session without an index in context.
2. **The active role instruction file MUST be loaded** (`<ROLE-INSTRUCTIONS-PATH>`). This is the T3 project brain and anchors the system prompt.
3. **Consult MEMORY.md entries before planning.** For any pointer whose description matches the task, call the memory-read tool to pull the topic body into context.

### Execution — write rules

4. **Offload any tool output >2K tokens to T2.** Write the raw payload to the session workspace (`workspace/<task_id>/scratch/…`) and replace the in-message body with a one-line manifest reference (path + ≤200-token summary).
5. **Checkpoint T1 after every state-machine transition and every tool result.** Never skip a checkpoint for latency — T1 is the sole recovery path after pod restart.
6. **Never write to T4 in the hot loop.** Long-term memory is written only at task end by the reflection pass. The user response must never block on a memory write.
7. **Honor role memory namespaces.** An agent reads and proposes edits only to topics its role is permitted to touch (`RoleTemplate.MemoryNamespaces`). Governance enforces this; do not attempt to bypass.

### Conflict & failure modes

8. **Reality primacy.** If a MEMORY.md pointer references a file, symbol, or fact that no longer matches the environment, the environment wins. Prune the pointer and flag the discrepancy for the reflection queue. Never hallucinate around a stale memory.
9. **Degraded-mode operation.** T4 fetch failure, topic read miss, or governance denial MUST NOT halt the task. Log the failure, continue with the best available context, and surface the degradation in task output.

### Task end — reflection pass

10. **Enqueue the reflection pass on `TASK_DONE` or `TASK_FAILED`.** The pass runs out-of-band, extracts only facts / preferences / corrections / mistakes, and proposes diffs against T4 topics. It does not store raw logs, chain-of-thought, or PR narrative.
11. **Only the maintainer role writes to T4.** Proposed diffs land as PRs (auto-merged for low-risk types, human-reviewed otherwise). The hot-path agent never commits directly.

### Never do these

- Never load tool output >2K tokens directly into the next LLM turn — always offload to T2 first.
- Never retry a T4 write inline — queue it to disk and let the reflection runner retry.
- Never skip loading MEMORY.md "because the task looks simple." The index is cheap; missing context is expensive.
- Never edit or delete existing T4 topic files in place when superseding — write a new topic and set the old one's `valid_until` (bi-temporal model).
```

## Customizing the template

Replace the markers:

- `<PATH-TO-MEMORY-DESIGN-DOC>` — e.g., `docs/designs/2026-04-16-multi-tier-memory-design.md`
- `<MEMORY-REPO>` — e.g., `agent-memory` or `github.com/org/agent-memory`
- `<ROLE-INSTRUCTIONS-PATH>` — e.g., `internal/agent-instructions/<role>.md`

Do **not** soften "MUST" to "should". Do **not** drop mandate #1 (session-start MEMORY.md load) under any circumstance — it is the keystone of the entire tier system.

## When the project has not yet shipped T4

If the long-term store is still in rollout (the reflection pass, Git store, or maintainer role is not live), keep the section verbatim but add a one-line note at the top:

> **Rollout status (as of YYYY-MM-DD):** T4 store is in rollout (`<design-doc>` §Rollout). Mandates #1–#3 apply using the cached/seed index; mandates #10–#11 activate when the reflection runner ships.

This keeps discipline forward-compatible: agents behave correctly the day T4 lands, with no doc churn required.
