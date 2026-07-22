# Context Engineering Guide Snippets

Patterns for prompts that drive agents and systems, rather than prompts a human pastes into a chat window. TCREI still governs construction — see `../SKILL.md`; this file covers what changes when the consumer is an autonomous agent with tools, long inputs, and a multi-step horizon.

## Contents

- [Foundational Engineering Principles](#foundational-engineering-principles)
- [Context Engineering](#context-engineering)
- [Mandatory Best Practices](#mandatory-best-practices-the-golden-rules)
- [Output Formatting Techniques](#output-formatting-techniques)
- [Verbosity and Length Control](#verbosity-and-length-control)
- [Tool Use Patterns](#tool-use-patterns)
- [Long-Context Patterns](#long-context-patterns)
- [Agentic System Patterns](#agentic-system-patterns)
- [Template Variable Design](#template-variable-design)
- [Empirical Grounding](#empirical-grounding)
- [Avoiding Overengineering](#avoiding-overengineering)
- [Verification Checklist](#verification-checklist)
- [Architecture of Intent Framework](#architecture-of-intent-framework)

## Foundational Engineering Principles

> Before selecting a role or drafting instructions, you must calibrate your approach based on the model's underlying cognitive architecture.

### Model Architecture: Simple vs. Reasoning Agents

| Feature          | Simple/Standard Agents                  | Reasoning Agents                            |
| :--------------- | :-------------------------------------- | :------------------------------------------ |
| **Mechanism**    | Pattern matching & sequence prediction. | Logical latent space & hidden monologues.   |
| **Strategy**     | **Heavy Orchestration.** CoT triggers.  | **Minimalist Zero-Shot.** Clear boundaries. |
| **Failure Mode** | "Lazy" output; hallucinations.          | Logic Collision; recursive loops.           |

## Context Engineering

> The quality of an AI's output is directly proportional to the quality and structure of the context provided.

1. **Supply the "Why" (Motivation):** Explaining _why_ a behavior is important enables the model to generalize intent.
2. **The Goldilocks Principle:** Avoid under-provisioning (hallucinations) and over-provisioning (attention dilution).
3. **Structured Hierarchy via XML:** Represent complex data relationships using nested XML tags.
4. **Grounding through Quoting:** Instruct the agent to quote relevant context before synthesizing.
5. **Explicit Scope:** Always state whether an instruction applies to one instance or all. Models do not silently generalize.
6. **Positive Examples over Negative Constraints:** Show correct behavior; don't just list what to avoid.

## Mandatory Best Practices (The "Golden Rules")

1. **Semantic Clarity & Quantitative Constraints:** Avoid subjective terms. Use measurable targets.
2. **Affirmative Directives:** Focus on what the agent _must_ do. Tell the model what it _should_ do instead of what it _should not_ do.
3. **Instruction Placement:** Anchor primary directives at the absolute beginning or absolute end.
4. **Colleague Test:** If a colleague with minimal context would be confused by the prompt, the model will be too. Rewrite until it passes.

## Output Formatting Techniques

Four reliable techniques to control output format:

| Technique | How |
| :-------- | :-- |
| **Affirmative directive** | "Write in flowing prose paragraphs" — not "don't use bullets" |
| **XML format tags** | "Write your analysis in `<analysis>` tags" |
| **Style matching** | Write the prompt in the style you want the output to match |
| **Explicit prose guidance** | Provide a detailed `<avoid_excessive_markdown>` block |

Positive examples of well-calibrated output outperform negative instructions for verbosity control.

## Verbosity and Length Control

Models calibrate response length to *perceived* task complexity, so a task that looks weighty gets a long answer whether or not one is wanted.

- Provide a **positive example** of well-calibrated output. This outperforms any negative instruction.
- State length explicitly: "Respond in 2-3 sentences," "under 150 words."
- For chronic over-explanation: "Provide concise, focused responses. Skip non-essential context."

## Tool Use Patterns

- **Directive language**: "Use the search tool to find X" beats "Can you look up X?"
- **When/how guidance**: If a tool under-triggers, add explicit conditions for when to invoke it.
- **Normal register**: Aggressive language ("CRITICAL: ALWAYS use this tool") causes overtriggering. Use normal prompting.
- **Parallel execution**: Without explicit instruction, models default to serial execution. Add:

```text
If multiple tool calls have no dependencies between them, make all independent calls in parallel.
```

## Long-Context Patterns

- **Data above query**: Place documents at the top of the prompt, instructions and query at the bottom. Up to 30% quality gain on complex multi-document inputs.
- **XML document structure**: Wrap each document in `<document index="N"><source>…</source><document_content>…</document_content></document>`.
- **Quote before synthesize**: Ask the agent to extract relevant quotes first, then answer. Cuts through noise.

## Agentic System Patterns

### Autonomy and Safety

Add explicit reversibility guidance for agents that can affect shared systems:

```text
Take local, reversible actions freely. For hard-to-reverse or externally visible actions, ask before proceeding.
```

### State Management

| State type | Format |
| :--------- | :----- |
| Trackable items (tests, tasks) | Structured JSON |
| Progress notes | Freeform text |
| Session checkpoints | Git commits |

### Research Pattern

For complex research: develop competing hypotheses, track confidence, self-critique, persist findings in notes files.

### Self-Correction Chain

Generate → review against criteria → refine. Each step is a separate call; intermediate outputs can be logged or branched. This is the most reliable multi-step pattern available, and it is the Evaluate/Iterate half of TCREI expressed as an automated chain.

### Subagent Orchestration

Delegation needs an explicit boundary or agents either never delegate or delegate everything:

```text
Use subagents when tasks can run in parallel, require isolated context, or involve
independent workstreams that don't share state. For simple tasks, sequential
operations, single-file edits, or work where context must carry across steps,
work directly rather than delegating.
```

## Template Variable Design

For prompts that get filled programmatically:

- Mark slots as `{{variable_name}}` and state which are required versus optional.
- Supply an **example value** for each. The example communicates expected granularity — `{{customer_name}}` with the example "Acme Corp (enterprise, 3 open tickets)" tells the caller far more than the slot name alone.

## Empirical Grounding

Agents will answer from priors about a file they never opened. Close that off explicitly:

```text
<investigate_before_answering>
Never speculate about content you have not retrieved. If the user references a file
or resource, fetch it before answering. Make claims only after investigation.
</investigate_before_answering>
```

Recommend the available tools by name. An agent that knows a tool exists still needs to be told it is the expected path to accuracy.

## Avoiding Overengineering

```text
Only make changes that are directly requested or clearly necessary:
- Scope: no features or abstractions beyond what was asked.
- Documentation: no comments on code you didn't change.
- Defensive coding: no error handling for scenarios that can't occur.
- Abstractions: no helpers for one-time operations.
```

## Verification Checklist

Before shipping a system or agent prompt:

- **Logic collision** — is it so prescriptive that a reasoning model's own process will fight it? See `tcrei-deep-dive.md` on model architecture.
- **Pressure test** — for each instruction: would the agent get this wrong without it? If not, delete it. Attention is the scarce resource.
- **Positive example test** — every "don't do X" that remains should be convertible to a demonstration of the right behavior.
- **Colleague test** — a colleague with minimal context should not be confused.

## Architecture of Intent Framework

> Autonomous agents are not independent, free-thinking problem solvers. They operate as heavily constrained infrastructural components within strict human-defined decision gates.

| Dimension          | Vibe-Based Prompting          | Deterministic Agent Design            |
| :----------------- | :---------------------------- | :------------------------------------ |
| **Interaction**    | Conversational; unstructured. | Structured XML; JSON schemas.         |
| **Memory**         | Ephemeral context window.     | Externalized state; narrative logs.   |
| **Error Handling** | Stochastic retry loops.       | Adversarial rigor; hard-fail linters. |
| **Scope**          | Implicit generalization.      | Explicit scope on every instruction.  |
