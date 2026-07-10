# Context Engineering Guide Snippets

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

Generate → review against criteria → refine. Each step is a separate call; intermediate outputs can be logged or branched.

## Architecture of Intent Framework

> Autonomous agents are not independent, free-thinking problem solvers. They operate as heavily constrained infrastructural components within strict human-defined decision gates.

| Dimension          | Vibe-Based Prompting          | Deterministic Agent Design            |
| :----------------- | :---------------------------- | :------------------------------------ |
| **Interaction**    | Conversational; unstructured. | Structured XML; JSON schemas.         |
| **Memory**         | Ephemeral context window.     | Externalized state; narrative logs.   |
| **Error Handling** | Stochastic retry loops.       | Adversarial rigor; hard-fail linters. |
| **Scope**          | Implicit generalization.      | Explicit scope on every instruction.  |
