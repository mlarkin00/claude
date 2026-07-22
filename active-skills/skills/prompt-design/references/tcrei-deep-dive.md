# TCREI Deep Dive

Supporting detail for the TCREI framework. Read the section that matches the problem at hand — this file is not meant to be loaded whole.

## Contents

- [Origins and terminology variants](#origins-and-terminology-variants) — TCREI vs. TCREPI vs. "Task, Context, Role, Exemplar, Instructions"
- [Why each component works](#why-each-component-works) — the mechanism behind personas, exemplars, and affirmative directives
- [Model architecture: standard vs. reasoning](#model-architecture-standard-vs-reasoning) — when to add scaffolding and when it hurts
- [Chain-of-Thought integration](#chain-of-thought-integration) — where CoT belongs in a TCREI prompt
- [The RACCCA evaluation rubric](#the-raccca-evaluation-rubric) — structured criteria for the Evaluate phase
- [LLM-as-a-judge](#llm-as-a-judge) — automating evaluation at scale, with a rubric template
- [Prompt iteration logs](#prompt-iteration-logs) — versioning prompts as software artifacts
- [Common pitfalls](#common-pitfalls)

## Origins and terminology variants

TCREI comes from Google's Prompting Essentials curriculum, and the mnemonic is "Thoughtfully Create Really Excellent Inputs." The same framework circulates under several expansions:

| Variant | Expansion | Note |
| :--- | :--- | :--- |
| **TCREI** | Task, Context, References, Evaluate, Iterate | The canonical Google form. Includes the optimization phase. |
| **TCREI** (alt) | Task, Context, Role, Exemplar, Instructions | Splits Role out of Task and Instructions out of Context. Construction only. |
| **Exemplars** | = References | Interchangeable; both mean few-shot examples or source material. |

The differences are organizational, not substantive. Every variant covers the same ground: what to produce, who for and under what limits, what good looks like. Use whichever decomposition makes the gaps visible for a given task. When a user names one of these variants explicitly, follow their vocabulary rather than correcting it.

## Why each component works

Understanding the mechanism matters because it tells you when a technique will *stop* working.

### Role / persona — priming and latent-space constraint

Assigning a persona works on two levels. Cognitively it is priming: exposure to one stimulus shapes the response to the next, so framing the model as a specialist frames the problem as that specialist's problem. Mechanically, the model holds a high-dimensional representation of language, and a role is a strong conditional signal that steers sampling toward one region of it. "Act as a Senior Data Scientist" raises the conditional probability of technical terminology, analytical structure, and professional register, and lowers it for conversational filler.

The implication: the persona's value scales with its specificity. "Act as an expert" barely narrows the distribution and mostly wastes tokens. "Act as a Principal Software Architect specializing in monolith-to-microservice migration cost" narrows it sharply.

### Exemplars — in-context learning

Few-shot examples work through in-context learning: demonstrations injected into the context window let the model infer the task's format, style, and logical shape without any weight updates. The mechanism is analogical reasoning — solving a new instance by pattern-matching against solved ones.

A finding worth knowing: the model learns primarily the *format* of the task from exemplars, and often generalizes correctly even when the labels in the examples are wrong. This makes exemplars extremely reliable for controlling structure, phrasing, and register — and less reliable than they look for teaching factual content.

### Affirmative directives — probability mass, not rule-following

Models predict likely continuations; they do not maintain a checklist of prohibitions. A negative constraint ("don't be verbose") requires the model to represent the forbidden region and then sample outside it, which leaves the destination unspecified. An affirmative directive ("respond in 2-3 sentences") places probability mass directly on the target. This is why "tell it what to do" consistently outperforms "tell it what to avoid" — the two are not symmetric operations.

## Model architecture: standard vs. reasoning

| | Standard LLMs | Reasoning models |
| :--- | :--- | :--- |
| **Mechanism** | Pattern matching, sequence prediction | Extended internal deliberation before answering |
| **Best strategy** | Heavy orchestration: detailed instructions, few-shot exemplars, explicit CoT triggers | Minimalist zero-shot: clear problem boundaries, minimal scaffolding |
| **Failure mode** | Generic output, hallucination, dropped constraints | Logic collision — prescriptive instructions interfere with native reasoning and can produce recursive loops |

This inverts a core piece of prompting advice. Techniques that reliably improve standard models — adding exemplars, appending "think step by step" — can measurably *degrade* frontier reasoning models by overriding reasoning they would have done better unprompted. Before loading a prompt with scaffolding, establish which class of model it targets. When targeting a reasoning model, spend the effort on stating the problem and its boundaries precisely, not on demonstrating how to solve it.

## Chain-of-Thought integration

CoT has two insertion points in a TCREI prompt, matched to different needs.

**Zero-shot CoT — in the instruction.** Append a trigger phrase to the task: "Let's think step by step," "Break the problem into segments and produce a result for each," "Decompose the task before answering." Cheapest option; effective on standard models for multi-step arithmetic and logic. Redundant to harmful on reasoning models, which already do this internally.

**Few-shot CoT — in the exemplars.** Show the intermediate reasoning inside the examples, not just input→output. More reliable than the zero-shot trigger because it demonstrates the *specific* reasoning pattern the task needs rather than invoking a generic one. Write the reasoning in natural language — models handle prose reasoning more reliably than compressed notation or raw equations.

```text
Input:  | Item: iPhone 13 Pro | Aug 1 Inv: 50 | Sep 1 Inv: 40 | Sales: 9 |
Output:
  Reasoning: Starting inventory 50, ending 40, so 10 units left stock while
  9 sales were recorded — a 1-unit discrepancy, likely a return or shrinkage.
  The summary should report sales while noting inventory movement.
  Summary: The iPhone 13 Pro recorded 9 sales in August, with inventory
  falling from 50 to 40 units.

Now apply the same reasoning to:
Input:  | Item: Samsung Galaxy S22 | Aug 1 Inv: 25 | Sep 1 Inv: 20 | Sales: 5 |
```

## The RACCCA evaluation rubric

A mental checklist for the Evaluate phase, useful when "does this look right?" is too coarse:

| Criterion | Question |
| :--- | :--- |
| **Relevant** | Does it address the actual task and constraints, not an adjacent one? |
| **Accurate** | Is it factually correct and free of invented specifics? |
| **Clear** | Is it understandable to the stated audience on one read? |
| **Concise** | Is anything present that could be removed without loss? |
| **Complete** | Are all requested elements there, including the ones buried mid-prompt? |
| **Aligned** | Does it match the requested tone, persona, and format? |

Additional dimensions worth checking on longer or higher-stakes work: **consistency** (do similar prompts yield similar quality) and **safety** (bias, harmful content, inappropriate material).

Rating on a 1-5 anchored scale beats pass/fail when tracking a prompt across revisions — it makes small regressions visible that a binary would hide.

## LLM-as-a-judge

For evaluating a prompt across many inputs rather than one, use a second model as an automated evaluator.

1. **Curate a golden dataset.** Inputs representing the most important real intents plus the hard edge cases. This is the ground truth for what "good" means.
2. **Design an anchored rubric.** Translate subjective quality into scored dimensions with labeled criteria per integer. Unanchored 1-5 scales drift.
3. **Construct the judge prompt.** Give the judge the original prompt, the generated output (or the full trace), and the rubric. Require a score *and* a rationale per dimension — the rationale is what makes disagreements diagnosable.
4. **Calibrate against humans.** Judge scores must be checked against expert scores until they reliably agree. An uncalibrated judge measures the judge.
5. **Automate.** Wire it into CI to catch regressions before deployment.

**Rubric template:**

```text
You are an expert evaluator. Assess the AI-generated response against the rubric below.

Initial prompt: [original prompt]
AI response / trace: [full output including any reasoning]

EVALUATION RUBRIC

1. Correctness & factual accuracy — Score (1-5) + rationale
   1: significant factual errors or hallucinations
   3: mostly correct, minor inaccuracies
   5: fully accurate and supported by the provided context

2. Completeness — Score (1-5) + rationale
   1: fails to address major parts of the prompt
   3: addresses the main query, misses sub-tasks or nuance
   5: fully addresses all explicit and implicit parts

3. Adherence to instructions & constraints — Score (1-5) + rationale
   1: ignores key constraints (word count, format, prohibitions)
   3: follows most instructions, deviates on minor ones
   5: adheres perfectly to all formatting, length, and content constraints

4. Reasoning & logic (if applicable) — Score (1-5) + rationale
   1: flawed, illogical, or erroneous
   3: generally sound with a minor flaw or skipped step
   5: logical, clear, and leads correctly to the answer

Final: overall score (average) + summary of strengths and weaknesses.
```

## Prompt iteration logs

Prompts that ship are software artifacts and benefit from the same discipline. Store them in git. Log every change with the hypothesis that motivated it, then the result — a change without a recorded hypothesis teaches nothing, because you cannot tell afterward whether it worked for the reason you thought. Tie each version to its evaluation results so decisions rest on data rather than recollection.

| Version | Date | Change / hypothesis | Results | Analysis | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| v1.0 | 2026-07-21 | Zero-shot, task only. Hypothesis: minimal instruction suffices. | Accuracy 65%, judge 2.5/5 | Generic output, misses the core request on complex cases. | Deprecated |
| v1.1 | 2026-07-22 | Added role + one exemplar. Hypothesis: role fixes tone, exemplar fixes format. | Accuracy 88%, judge 4.2/5 | Large gain in tone and format; output now parsable. Reasoning errors persist. | Production |
| v1.2 | 2026-07-23 | Added "think step by step" to the instruction. Hypothesis: reduces reasoning errors. | Accuracy 94%, judge 4.6/5 | Multi-step calculations now correct. | In review |

## Common pitfalls

- **Vague language.** Subjective terms — "good," "short," "fast," "interesting" — are unenforceable and unevaluable. Replace with quantities, named structures, or reading levels.
- **Insufficient context.** Without background, the model produces something generic and plausible, which is harder to spot as wrong than something obviously off.
- **No examples.** Style and format expectations that were never demonstrated will not be met reliably, however well described.
- **Buried instructions.** Critical directives placed mid-prompt get dropped. Anchor them at the very beginning (framing) or the very end (execution).
- **Unstructured mixing.** Instructions, context, and examples run together without delimiters produce unpredictable results. Separate them.
- **Over-constraining.** Too many rigid or mutually conflicting constraints degrade coherence. Specificity has a ceiling.
- **Skipping iteration.** Treating the first output as the verdict on the prompt. Evaluate and Iterate are half the framework.
- **Ignoring model architecture.** Applying standard-LLM scaffolding to a reasoning model, or expecting a standard model to succeed zero-shot on a task that needs demonstration.
