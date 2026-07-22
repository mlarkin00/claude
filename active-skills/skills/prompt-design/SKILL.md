---
name: prompt-design
description: Use this skill whenever the user wants a prompt built, improved, or iterated on — writing a prompt for another AI, refining a system prompt, turning a rough request into something a model will follow, or debugging a prompt that keeps producing the wrong output. Applies the TCREI framework (Task, Context, References, Evaluate, Iterate) to turn vague intent into a deterministic, copy-pasteable prompt. Use it even when the user just describes what they want an AI to do and does not say the word "prompt."
metadata:
  category: code-scaffolding
---

# Prompt Design (TCREI)

TCREI — Task, Context, References, Evaluate, Iterate — is Google's five-part framework for prompt construction. It splits into two phases that happen at different times:

| Phase | Components | When |
| :--- | :--- | :--- |
| **Construction** | Task, Context, References | Before the prompt runs. Produces the artifact. |
| **Optimization** | Evaluate, Iterate | After the user has run it and come back with output. |

Treat TCREI as a mental checklist, not a rigid script. Component order can flex — putting source material before context is often better when the source is long — but every applicable component gets considered before the prompt ships.

The reason structure works at all: models reproduce the patterns present in their context window. A generic input supplies a generic pattern and gets generic output back. Naming the role, the audience, the constraints, and the shape of a good answer supplies a specific pattern, and the model matches it.

## The deliverable

The output of construction is **the prompt block, and nothing else**. The user is going to copy it into a chat window. Commentary, component-by-component breakdowns, and "here's why I made these choices" prose all dilute the thing they asked for.

```text
[TASK]
<action verb> <persona> <output format>

[CONTEXT]
- Audience: ...
- Situation: ...
- Constraints: ...

[REFERENCES]
<exemplar, source data, or style rules>
```

Two mechanical points:

- **Bracket headers for prompts a human will paste** into Gemini, ChatGPT, or Claude. They read cleanly and survive copy-paste.
- **XML tags (`<task>`, `<context>`, `<references>`) for prompts embedded in code or system prompts**, where nesting matters and something downstream may need to parse or template the sections.

Omit a section rather than padding it. A `[REFERENCES]` block containing "N/A — no examples provided" is worse than no block, because it spends attention establishing that nothing is there.

Evaluate and Iterate are not sections of the artifact. They are what happens on the next turn.

## Step 1 — Close the gaps before writing

Three things cannot be invented on the user's behalf, because guessing wrong produces a confidently wrong prompt that looks finished:

| Field | Why guessing fails |
| :--- | :--- |
| **Audience** | Drives vocabulary, length, and what can be assumed. A brief for a CTO and one for a customer share no sentences. |
| **Hard constraints** | Word counts, banned terms, required sections, reading level. These are the only parts of output quality that are objectively checkable later. |
| **Ground truth** | Whether real source data, a past example, or a style guide exists. Without it the model will invent specifics, and the user may not catch it. |

Ask about whichever of these the request leaves open. Keep it to the two or three that actually change the prompt, ask them together rather than one at a time, and offer a concrete default with each so the user can confirm rather than compose:

> Two things before I write this:
> 1. Who reads the release notes — end users, or the internal support team? (Assuming end users.)
> 2. Do you have a previous release note I should match the format of?

Everything else — tone, persona, structure — is inferable from the answers and from the domain. Infer it and state the inference inside the prompt where the user can see and overwrite it.

If the user says to just draft something, draft it. Mark invented specifics as `[ASSUMED: ...]` inline so they are visible and easy to correct, and note what would sharpen it. Blocking on questions the user has declined to answer is worse than a labelled guess.

## Step 2 — Task

The `[TASK]` block answers "what should it produce." It carries three sub-elements, and a task missing any of them underspecifies the output:

- **Action verb** — `Draft`, `Analyze`, `Restructure`, `Summarize`. A verb commits the model to an operation. "Help me with X" does not.
- **Persona** — specific and evidence-based. "Principal Software Architect specializing in migration cost analysis" constrains which region of the model's knowledge gets sampled. "Helpful expert" constrains nothing. Assigning a role is priming: it shifts the conditional probability distribution toward the vocabulary, rigor, and format conventions of that specialty.
- **Output format** — the structural shape. `Markdown table with columns X, Y, Z`. `3-bullet executive summary`. `JSON matching this schema`. Format is the cheapest constraint to specify and the most reliably obeyed.

## Step 3 — Context

The `[CONTEXT]` block answers "what does the model need to know to get it right." Cover audience, the background situation and what is at stake, and the explicit boundaries.

Two properties separate context that works from context that reads well:

**Quantitative over subjective.** "Keep it brief" is unenforceable and unevaluable. "Under 400 words" can be checked. Every subjective adjective in a draft prompt — professional, thorough, concise, engaging — is a candidate for replacement with something measurable.

**Affirmative over negative.** "Do not be too technical" tells the model what region to avoid but not where to go, so it lands somewhere arbitrary. "Explain each term the way you would to a new hire on their first week" names the target. Negative constraints are lossy; keep them only for genuine prohibitions ("no exclamation marks," "never name the client"), where the boundary itself is the point.

Include the stakes when they exist. A model told the brief is defending a budget line to a CTO writes differently than one told to explain a topic, and it does so without further instruction.

## Step 4 — References

References narrow the gap between what the user pictured and what comes back. They do more work per token than any other component, because showing a pattern beats describing one — the model infers format, register, and structure from an exemplar in ways a paragraph of adjectives cannot convey.

Three kinds, and most prompts want only one:

- **Few-shot exemplars** — one to three past outputs that were good. Best when format or voice is what keeps coming out wrong.
- **Source material** — transcripts, tables, logs, docs. Best when factual grounding matters; this is the main defense against invented specifics. Place long source material at the top of the prompt, above the task, and put the instruction to act on it at the bottom.
- **Style rules** — brand guidelines, terminology glossaries, banned phrases.

If the user has no references, say so and move on rather than fabricating an exemplar. A made-up example teaches the model a pattern nobody asked for, and it will follow it faithfully.

One caveat worth knowing: exemplars help standard models a great deal, and can *degrade* frontier reasoning models by interfering with their own logic. See `references/tcrei-deep-dive.md` on model architecture before loading a reasoning model with few-shot examples.

## Step 5 — Evaluate

This runs when the user comes back with the output. The value here is that the user has domain knowledge the model does not, so the job is to direct their attention at the four places outputs actually fail, rather than asking "does this look good?":

- **Accuracy** — invented facts, misread source data, fabricated citations or figures.
- **Constraint compliance** — the word count, section structure, and format rules from `[CONTEXT]`. These are checkable; check them rather than asking.
- **Tone and persona fit** — does the voice suit the stated audience.
- **Usability** — is it directly usable, or does it need heavy manual rework? A response that requires rewriting failed even when everything in it is true.

The compressed version of this checklist is RACCCA: Relevant, Accurate, Clear, Concise, Complete, Aligned. `references/tcrei-deep-dive.md` has the full rubric and an LLM-as-judge template for evaluating at scale.

## Step 6 — Iterate

When output misses, the reflex is to rewrite the prompt from scratch. That discards everything that worked and re-rolls the parts that were fine. Issue a targeted follow-up in the same conversation instead — the model still holds the context, so the correction is cheap and the delta is attributable.

Three moves, matched to the failure:

| Failure | Move | Example |
| :--- | :--- | :--- |
| Specific defect in otherwise good output | **Surgical fix** | "Remove bullet 2 and tighten section 1." |
| Structurally right, wrong dimensions | **Constraint addition** | "Rewrite under 150 words in active voice." |
| Missing an angle the audience needs | **Context adjustment** | "Add a paragraph on security implications for C-level readers." |

Change one thing at a time. Bundled edits make it impossible to tell which one helped, and prompt work is only cumulative if each change is attributable. When a fix lands, fold it back into the source prompt so the next run starts from the improved version — otherwise the improvement lives only in a chat log.

## Worked example

**Weak prompt**

> Write a promotional email for our new cloud monitoring tool.

Everything about the output is unconstrained: length, audience, voice, what to lead with. The model will pick plausible defaults, and they will be generic ones.

**TCREI prompt**

```text
[TASK]
Act as a Principal B2B SaaS Copywriter specializing in DevOps tools. Write a cold
outreach email offering a 14-day free trial of our automated log monitoring platform.
Output format: 3 subject line options, email body under 150 words, and CTA button text.

[CONTEXT]
- Audience: Directors of Engineering at Series-B startups suffering from alert fatigue.
- Tone: Direct, peer-to-peer, pain-point focused.
- Key value prop: Reduces false-positive PagerDuty alerts by 60% using ML grouping.
- Constraints: No exclamation marks. Do not use "game-changing" or "revolutionary."

[REFERENCES]
Emulate the structure and concise tone of this email, which booked 12 demos:

Subject: Quick question about your deployment pipeline
Hi {{FirstName}},
Most engineering teams we talk to lose 10+ hours a week chasing duplicate logs
during minor outages.
We built [Product] to automatically cluster related stack traces before they reach
PagerDuty.
Worth a 5-minute test run on your staging environment this week?
Best,
[Name]
```

The task names a verb, a specialty, and three deliverables. The context makes length and vocabulary checkable and bans the two phrases that would have appeared. The reference carries the voice — the short paragraphs, the question close, the absence of hype — which no amount of describing "direct, peer-to-peer tone" would have transferred as reliably.

## Improving an existing prompt

Requests arrive from the other direction just as often: here is a prompt, make it better. Same framework, run diagnostically — map what exists onto T/C/R and the gaps are the fix list.

1. **Locate each component.** Which of Task, Context, References is present? A missing component is usually the whole problem.
2. **Audit the Task.** Is there an action verb, a specific persona, a named output format?
3. **Convert subjective to measurable.** Every unenforceable adjective becomes a number, a named structure, or a reading level.
4. **Flip negative constraints** to affirmative ones, keeping genuine prohibitions.
5. **Pressure test each line.** Ask: would the model get this wrong without this instruction? If no, delete it. Prompts fail from attention dilution as often as from underspecification, and long prompts are where instructions go to be ignored.
6. **Colleague test.** If a colleague with minimal context would be confused, the model will be too.

Return the revised prompt as a block, then a short list of what changed and why — here the reasoning is the point, because the user needs to judge whether the changes match intent they never stated.

## Naming

Prompts that get saved and reused need names that say what they do. Use kebab-case, name the operation rather than the domain, and skip gerunds: `code-review`, not `reviewing-code`; `sql-optimize`, not `sql-expert`.

## Gotchas & Anti-Patterns

| Excuse | Reality |
| :--- | :--- |
| "The request was clear enough, I'll skip the questions." | Clear about *what*, silent about *for whom* and *how long*. Those two determine most of the output. |
| "I'll add a breakdown so they understand the choices." | They asked for a prompt. Construction ships the block; explanation belongs in the improve-an-existing-prompt path, where it is the deliverable. |
| "No references were provided, so I'll write an example." | A fabricated exemplar is a pattern the model will faithfully copy. Say none exists instead. |
| "'Professional and concise' captures the tone." | Unenforceable and unevaluable. Constraints that cannot be checked cannot be iterated on. |
| "'Don't be too formal' communicates the target." | It names a region to avoid, not one to land in. Say what the voice should be. |
| "More instructions means more control." | Past a point, added instructions dilute attention and the important ones get dropped. Delete anything the model would do anyway. |
| "The output was wrong, so I'll rewrite the prompt." | Rewriting re-rolls the parts that worked. Issue a targeted follow-up, then fold the fix back into the source. |
| "I'll fix all four problems in one follow-up." | Bundled changes make it impossible to tell which one worked. |
| "It's a reasoning model, so more examples will help." | Few-shot exemplars can degrade reasoning models. They want clear boundaries, not more scaffolding. |
| "Adding a role improved it — 'act as an expert.'" | Generic roles add tokens and constrain nothing. Specificity is what shifts the output. |
| "One good result means the prompt works." | One result may be luck. A prompt is proven by holding up across the cases it will actually see. |

## References

- `references/tcrei-deep-dive.md` — why each component works (priming, in-context learning), the RACCCA rubric, LLM-as-judge template, Chain-of-Thought integration, iteration logs, standard vs. reasoning model architecture.
- `references/context-engineering-guide.md` — patterns for agentic and system prompts: long-context structure, tool-use triggering, state management, output formatting, safety boundaries.
- `references/memory-manifesto.md` — context as identity and memory.
