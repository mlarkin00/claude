---
name: new-prompt
description: Pre-processes raw user input through the TCREI framework before execution. Trigger when the user invokes /new-prompt "<task>" or says "refine this prompt then run it". Takes raw intent, applies Task/Context/References structure via the prompt-design skill to produce a constraint-bearing prompt, then executes it as the main task and checks the result against its own constraints.
---

# New Prompt (Prompt Pre-Processor)

Three-phase pipeline: refine raw intent into a TCREI prompt, execute it, then check the result against the constraints the prompt itself set.

This skill is the one place where the same agent both writes a prompt and runs it. That makes it the only context in which all five TCREI letters can close in a single turn — construction (Task, Context, References) in Phase 1, and the optimization half (Evaluate, Iterate) in Phase 3, where `prompt-design` alone has to hand off and wait.

## Phase 1 — Refine

1. Extract raw intent from the skill args (everything after `/new-prompt`).
2. Announce: "Refining prompt before execution..."
3. **Invoke the `prompt-design` skill** with the raw intent as the subject.
   - Use its construction path — Task, then Context, then References. The diagnostic "improving an existing prompt" path does not apply here; the input is raw intent, not a prompt to repair.
   - The output of this phase is the **Refined Prompt**: a delimited prompt block carrying an action verb, a specific persona, a named output format, and checkable constraints.

**On gap-closing.** `prompt-design` closes missing audience, constraints, and ground truth by asking. Invoking it through `/new-prompt` is a standing instruction to draft rather than interview — the user asked for work, not a questionnaire. So take its own escape hatch: fill the gaps with the best inference from the raw intent and the surrounding conversation, and mark every invented specific inline as `[ASSUMED: ...]`.

Assumptions must be visible, never silent. The user sees the full prompt block in Phase 2 before anything runs, so a wrong `[ASSUMED: audience is external customers]` is one interruption away from being corrected. A guess that was never labelled is not.

Ask only when proceeding under any assumption would be unsafe or would waste substantial work if wrong — a destructive operation, or an ambiguity so central that both readings produce genuinely different deliverables.

## Phase 2 — Execute

1. Present the Refined Prompt to the user in a fenced block, labeled clearly:

   ```
   ### Refined Prompt
   <the output from Phase 1>
   ```

2. Announce: "Executing refined prompt now."
3. **Treat the Refined Prompt as the new user instruction.** Execute it immediately — no further confirmation required.

## Phase 3 — Evaluate and iterate

Phase 1 wrote constraints precisely so they could be checked. Verify the output against them rather than asking the user whether it looks right:

- **Constraint compliance** — the word counts, named sections, and format rules from `[CONTEXT]`. These are mechanically checkable. Count them.
- **Accuracy** — no invented specifics, particularly anywhere an `[ASSUMED: ...]` marker was load-bearing.
- **Usability** — directly usable, or does it still need rework?

When something misses, apply a surgical fix to that part and say what changed. Do not regenerate wholesale — that re-rolls the parts that already worked and hides which change helped.

Report the assumptions that survived into the result. `[ASSUMED: ...]` markers are the audit trail of what was inferred rather than given, and they are worth surfacing precisely when the output looks finished.

## Rules

- Never skip Phase 1. Even well-formed input goes through `prompt-design` — the structure is the point.
- Never ask "Should I execute this?" The user invoked this skill to execute.
- The Refined Prompt replaces the raw input entirely. Do not mix instructions from both.
- Phase 2 shows the prompt block alone. Explaining the construction choices is the wrong deliverable here; the user wants the work, and the block is already legible.

## Gotchas & Anti-Patterns

| Excuse | Reality |
| :--- | :--- |
| "The intent was vague, so I should ask first." | Invoking `/new-prompt` is the instruction to draft. Infer, mark it `[ASSUMED: ...]`, and let the visible block invite correction. |
| "I filled the gaps sensibly, no need to flag them." | An unlabelled guess is indistinguishable from a stated requirement once it is inside the prompt. Mark every one. |
| "The input was already well-structured, so I ran it directly." | Then refining costs almost nothing. Skipping Phase 1 is how unconstrained prompts slip through. |
| "The output looks good, so the constraints were met." | "Looks good" is not a word count. The constraints were written to be checked; check them. |
| "The result missed, so I'll rewrite the prompt and rerun." | Wholesale regeneration discards what worked. Fix the specific defect. |
