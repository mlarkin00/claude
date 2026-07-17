---
name: new-prompt
description: Pre-processes raw user input through the prompt-design framework before execution. Trigger when user invokes /new-prompt "<task>" or says "refine this prompt then run it". Takes raw intent, applies context engineering to produce a deterministic prompt, then executes it as the main task.
---

# New Prompt (Prompt Pre-Processor)

Two-phase pipeline: refine raw user intent into a deterministic prompt, then execute it.

## Phase 1 — Refine

1. Extract raw intent from the skill args (everything after `/new-prompt`).
2. Announce: "Refining prompt before execution..."
3. **Invoke the `prompt-design` skill** with the raw intent as the subject.
   - Let prompt-design run its full methodology: audit → context engineering → verification.
   - It may ask clarifying questions — answer them or relay them to the user.
   - The output of this phase is the **Refined Prompt**: a well-structured, context-engineered task description.

## Phase 2 — Execute

1. Present the Refined Prompt to the user in a fenced block, labeled clearly:
   ```
   ### Refined Prompt
   <the output from Phase 1>
   ```
2. Announce: "Executing refined prompt now."
3. **Treat the Refined Prompt as the new user instruction.** Execute it immediately — no further confirmation required.

## Rules

- Never skip Phase 1. Even if the raw input looks well-formed, run it through `prompt-design`.
- Never ask "Should I execute this?" — the user invoked this skill to execute.
- If `prompt-design` produces multiple prompt variants, pick the highest-signal one and state why.
- The Refined Prompt replaces the raw input entirely. Do not mix instructions from both.
