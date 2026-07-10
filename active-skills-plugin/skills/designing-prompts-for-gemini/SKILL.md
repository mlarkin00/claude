---
name: designing-prompts-for-gemini
description: Use this skill when designing, tuning, or iterating on prompts specifically for Gemini models (Gemini 3, Gemini Flash, etc.). Self-contained: covers universal context engineering principles plus Gemini-specific behaviors (input taxonomy, model parameters, Google Search grounding, reasoning enhancement, agentic workflow configuration). No need to also load `designing-prompts`.
---

# Designing Prompts for Gemini

Self-contained prompt engineering guide for Gemini models. Combines universal context engineering principles with Gemini-specific behaviors and API parameters.

## 1. Audit & Analysis

Before writing or rewriting a prompt:

- [ ] **Classify the input type** (see Input Taxonomy below) — shapes the prompt structure.
- [ ] **Identify "vibe-based" patterns**: subjective terms ("be helpful," "write well"), ambiguous roles, missing constraints.
- [ ] **Colleague test**: show the prompt to a colleague with minimal context. If they'd be confused, Gemini will be too.
- [ ] **Identify the target model**: Gemini 3, Gemini Flash, or another variant — parameters and defaults differ.

## 2. Input Taxonomy

Gemini distinguishes four input types. Identify which applies — it determines whether you need instructions, context, examples, or a completion seed.

| Type | Description | Prompt structure |
| :--- | :---------- | :--------------- |
| **Question** | Model answers a question | Question + constraints |
| **Task** | Model performs an operation | Task description + input + constraints |
| **Entity** | Model operates on a piece of content | Entity + operation + constraints |
| **Completion** | Model continues a partial output | Partial output seed (model continues) |

**Completion strategy tip**: provide the start of the output you want (e.g., `"The three key factors are: 1."`) to lock in format and direction before the model generates.

## 3. Prompt Structure & Templates

### XML Structure

Explicit delimiters reduce misinterpretation. Recommended structure:

```xml
<role>You are a [specific expert role].</role>
<constraints>
1. [Constraint]
2. [Constraint]
</constraints>
<context>[Reference material or background]</context>
<task>[Specific request]</task>
```

### Markdown Structure

Alternative for system instructions:

```text
# Identity
[Role definition]

# Constraints
[Numbered list of constraints]

# Output format
[Format specification]
```

### Instruction Placement

- **Critical instructions**: place in system instruction or at the very beginning of the prompt.
- **Long contexts**: place context first, then instructions and question last. Use an anchor phrase before the question (e.g., "Based on the information above, ..."). This improves quality significantly on complex multi-document inputs.

### Role Calibration

Define a specific, evidence-based role rather than a generic one:

- Bad: "You are a helpful assistant."
- Good: "You are a senior security engineer specializing in API authentication systems."

Even a single well-calibrated role sentence measurably shapes behavior and tone.

## 4. Specificity & Constraints

- **Quantitative constraints**: replace subjective terms with measurable ones ("Under 200 words," "Exactly 3 bullet points," "Return only JSON").
- **Affirmative directives**: tell the model what it must do, not what to avoid.
- **Define ambiguous terms**: explicitly explain any terms that have multiple valid interpretations.
- **Contextual constraints**: when the model should use only provided material, say so explicitly — e.g., "Respond with only the information provided in the context above. Do not add external knowledge."
- **Explicit scope**: if an instruction applies to every instance, state it. Gemini does not silently generalize.

## 5. Long-Context Prompting & Adding Context

For large documents or data-rich inputs:

- **Data at the top**: Place long documents above query and instructions. Queries at the end can boost quality by up to 30% on complex multi-document inputs.
- **XML document structure**: Wrap each document in `<document>` tags with `<source>` and `<document_content>` subtags.
- **Quote before synthesizing**: Ask the model to extract relevant passages first, then answer. Cuts through document noise.

```xml
<documents>
  <document index="1">
    <source>{{filename}}</source>
    <document_content>{{content}}</document_content>
  </document>
</documents>

Find quotes relevant to {{question}}. Place them in <quotes> tags. Then synthesize your answer in <answer> tags.
```

For general context addition:

- Provide troubleshooting guides, documentation excerpts, domain-specific schemas.
- Use `<context>` or `<documents>` tags to separate reference material from instructions.
- Add a strict grounding constraint when the model should use only provided material: "Respond with only the information provided in the context above. Do not add external knowledge."

## 6. Few-Shot Prompting

Few-shot examples are one of the highest-leverage techniques for controlling format, phrasing, and response patterns.

> "Prompts without few-shot examples are likely to be less effective." — Gemini docs

Best practices:

- **Relevant**: mirror your actual use case closely.
- **Varied**: cover edge cases so the model does not pick up unintended patterns.
- **Consistent format**: use identical formatting (XML tags, whitespace, newlines) across all examples.
- **3–5 examples** for best results; experiment with quantity — too many can cause overfitting.
- Detailed instructions can sometimes be removed when examples already demonstrate the task clearly.

```text
<examples>
  <example>
    <input>{{example_input_1}}</input>
    <output>{{example_output_1}}</output>
  </example>
  <example>
    <input>{{example_input_2}}</input>
    <output>{{example_output_2}}</output>
  </example>
</examples>
```

## 7. Output & Formatting Control

- **Specify format explicitly**: "Format your response as a markdown table with columns: Name, Status, Notes."
- **Completion seeding**: start the output yourself to lock in structure (e.g., `| Name | Status | Notes |\n|---`).
- **Match prompt style to desired output**: a prompt written in flowing prose produces prose; bullets produce bullets.
- **Verbosity control**: Gemini 3 provides direct, efficient answers by default. If you need more detail, ask for it explicitly. If you need less, say so.
- **Affirmative format directives**: "Write in smoothly flowing paragraphs" beats "Do not use bullet points."

## 8. Model Parameters

| Parameter | What it controls | Guidance |
| :-------- | :--------------- | :------- |
| `max_output_tokens` | Maximum response length | ~4 chars/token; 100 tokens ≈ 60–80 words |
| `temperature` | Randomness in token selection | Lower = deterministic; Higher = creative. **Gemini 3: keep at default 1.0** |
| `topK` | Candidate token pool size | topK=1 = greedy; topK=3 = picks from 3 most probable |
| `topP` | Cumulative probability cutoff | Default 0.95; tokens selected until sum reaches topP |
| `stop_sequences` | Halt generation at specific strings | Choose sequences unlikely to appear naturally in content |

### Gemini 3 Temperature Warning

**Do not lower temperature below 1.0 on Gemini 3.** The docs explicitly warn that "changing the temperature (setting it below 1.0) may lead to unexpected behavior, such as looping or degraded performance." Use default 1.0 unless you have a specific tested reason to change it.

### Fallback Responses

If Gemini returns a fallback/refusal, this typically indicates a safety filter trigger. First remediation: try increasing the temperature parameter.

## 9. Template Variable Design

- Define all variable slots using `{{variable_name}}`.
- Provide "Example Values" to demonstrate expected input quality.
- Distinguish required vs. optional variables in comments or a legend.

## 10. Tool Use

### Parallel Tool Calls

Gemini defaults to serial execution unless instructed otherwise. To unlock parallel execution:

```text
If you intend to call multiple tools and there are no dependencies between the calls, make all independent tool calls in parallel. Never use placeholders or guess missing parameters — if a value is unknown, call tools sequentially to discover it first.
```

To reduce parallelism for stability:

```text
Execute operations sequentially with brief pauses between each step to ensure stability.
```

### Google Search Grounding

Enable when the model needs obscure, recent, or time-sensitive facts. Avoids hallucinations by grounding responses in real-time web content.

Add a strict grounding instruction when you want the model to limit itself entirely to retrieved content:

```text
Answer only using information retrieved from the provided sources. Do not add external knowledge.
```

### Code Execution

Enable for arithmetic, counting, statistical, or calculation tasks. The model generates and executes Python code rather than reasoning through math — use this instead of prompting the model to calculate manually.

## 11. Reasoning Enhancement

Gemini models automatically generate internal thinking. You can steer reasoning depth with simple natural language:

```text
Think very hard before answering.
```

This improves performance at the cost of additional tokens. Use for high-stakes reasoning tasks. For latency-sensitive workloads, omit this instruction.

For structured multi-step reasoning, wrap reasoning and answer separately:

```text
<thinking>[reasoning goes here]</thinking>
<answer>[final answer]</answer>
```

## 12. Prompt Iteration Strategies

When a prompt underperforms:

1. **Rephrase**: try different word choices conveying identical intent. Different formulations yield different responses.
2. **Task analogy**: reformulate as an analogous task — e.g., change open-ended generation to multiple-choice selection for bounded, more predictable responses.
3. **Reorder content**: experiment with `[examples][context][input]` vs. `[input][examples][context]` — order impacts quality.
4. **Add/remove examples**: adjust few-shot count; fewer can generalize better, more can constrain format better.

## 13. Breaking Down Complex Prompts

### Single-Instruction Prompts

Decompose multi-instruction prompts into single-instruction prompts. Route user input to the appropriate prompt based on task type. Simpler prompts are more reliable and easier to debug.

### Prompt Chaining

Sequential prompts where the output of each step becomes the input of the next. Use when:

- A task has multiple distinct stages (e.g., extract → classify → summarize).
- You need to inspect or validate intermediate outputs before proceeding.

### Aggregation / Parallel Processing

Run different operations on data portions in parallel, then combine results. Use when:

- Input is large and can be chunked.
- Operations are independent across chunks.

### Self-Correction Chain

Generate → review against criteria → refine. Each step is a separate API call:

```text
Step 1: Draft a response to: {{task}}
Step 2: Review the draft against: {{criteria}}. List issues only.
Step 3: Revise the draft based on the review.
```

## 14. Gemini 3 — Specific Behaviors

### Direct and Efficient by Default

Gemini 3 gives direct, efficient answers. It does not pad responses or add unsolicited context. If you need elaboration or conversational depth, request it explicitly in the system instruction.

### Time Awareness

Gemini 3 Flash may not always apply correct year context. For time-sensitive queries, add:

```text
Remember: the current year is 2026.
```

Include knowledge cutoff awareness where relevant:

```text
Your knowledge cutoff date is January 2025. For anything that may have changed since then, clearly flag the uncertainty.
```

### Strict Grounding (Flash)

To prevent Gemini Flash from drawing on background knowledge when you need strict document-only answers:

```text
Answer only using information present in the provided context. If the context does not contain enough information to answer, say so.
```

### Multimodal Inputs

Treat all modalities (text, image, audio, video) as equal-class inputs. Reference each modality explicitly in the prompt:

```text
Based on the image provided above and the text description below, identify...
```

Do not assume the model will automatically attend to non-text inputs without explicit reference.

## 15. Agentic Workflow Configuration

Configure autonomous agents across three dimension groups. Include relevant dimensions in the system instruction as explicit policy.

### Reasoning & Strategy

| Dimension | What to specify |
| :-------- | :-------------- |
| **Logical decomposition** | How thoroughly to analyze constraints and prerequisites before acting |
| **Problem diagnosis** | Depth of root-cause analysis; whether to accept abductive reasoning |
| **Information exhaustiveness** | Comprehensive analysis vs. efficient best-effort |

### Execution & Reliability

| Dimension | What to specify |
| :-------- | :-------------- |
| **Adaptability** | Strict plan adherence vs. pivot when contradictory data arrives |
| **Persistence & recovery** | Self-correction depth; token cost tolerance for retries |
| **Risk assessment** | Distinguish low-risk exploratory reads from high-risk state-changing writes |

### Interaction & Output

| Dimension | What to specify |
| :-------- | :-------------- |
| **Ambiguity handling** | When to assume vs. when to request clarification |
| **Verbosity** | Explanation level during execution (silent, brief, detailed) |
| **Precision & completeness** | Edge case handling; whether estimates are acceptable |

### Agentic System Instruction Template

```text
<agent_policy>
Planning: Before acting, identify logical dependencies and constraints in priority order. Explore multiple hypotheses before committing to an approach.

Risk: Classify each action as exploratory (low-risk, read-only) or state-changing (high-risk, write/delete/send). Confirm before state-changing actions that cannot be undone.

Precision: Quote exact information from sources rather than paraphrasing. Do not speculate about content you have not retrieved.

Persistence: Apply intelligent retry logic. Self-correct before escalating to the user. Tolerate [N] retry attempts before surfacing an error.

Ambiguity: [Assume reasonable defaults / Ask for clarification] when input is underspecified.

Verbosity: [Silent except on errors / Brief status updates / Detailed step-by-step narration].

Completeness: Do not stop early. Complete tasks fully before responding.
</agent_policy>
```

Fill in the bracketed values for your use case.

## 16. Investigating Before Answering

Instruct agents not to speculate about content they have not retrieved:

```text
<investigate_before_answering>
Never speculate about information you have not retrieved. If the user references a file, document, or resource, fetch it before answering. Make claims only after investigation.
</investigate_before_answering>
```

## 17. Subagent Orchestration

Guide when to delegate vs. work directly:

```text
Use subagents when tasks can run in parallel, require isolated context, or involve independent workstreams that don't need to share state. For simple tasks, sequential operations, single-file edits, or tasks where you need to maintain context across steps, work directly rather than delegating.
```

## 18. State Management & Multi-Window Workflows

For tasks spanning multiple context windows:

- **Structured state for trackable items**: JSON for test results, task status, task lists.
- **Freeform text for progress notes**: general progress and context.
- **Git for state**: log of completed work and restorable checkpoints.
- **Incremental progress**: ask the agent to complete one component before moving to the next.

```text
This is a long task. Plan your work clearly. Track progress in progress.txt and structured state in state.json. Commit frequently. Never stop early — complete tasks fully.
```

## 19. Verification & Testing

Harden the prompt before shipping:

- **Logic collision check**: In reasoning models, ensure the prompt is not too prescriptive — can cause recursive loops.
- **Pressure test**: "Will the agent get this wrong without this specific instruction?" If no, remove it to save tokens.
- **Positive example test**: Convert negative instructions ("don't do X") to a positive example of correct behavior.

## 20. Avoiding Overengineering

```text
Avoid over-engineering. Only make changes directly requested or clearly necessary:
- Scope: Do not add features or abstractions beyond what was asked.
- Documentation: Do not add comments to code you did not change.
- Defensive coding: Do not add error handling for scenarios that cannot happen.
- Abstractions: Do not create helpers for one-time operations.
```

# Gotchas & Anti-Patterns

| Rationalization | Reality |
| :-------------- | :------ |
| "Gemini will generalize this instruction across all sections." | State scope explicitly — it will not silently generalize. |
| "I'll lower temperature for more consistent Gemini 3 output." | **Do not.** Below 1.0 causes looping and degraded performance on Gemini 3. |
| "The few-shot examples cover it, no need for constraints." | Examples regulate format; explicit constraints regulate edge cases and failure modes. |
| "I'll just add more instructions to fix the bad output." | First try rephrasing, reordering, or adjusting examples before adding more instructions. |
| "One complex multi-task prompt is cleaner than chaining." | Multi-instruction prompts are harder to debug and less reliable. Decompose. |
| "The fallback means the model can't do this task." | Fallbacks usually indicate safety filter triggers. Try increasing temperature first. |
| "The model will attend to the image automatically." | Reference each modality explicitly in the prompt. |
| "Reasoning is expensive, skip 'think hard' for all tasks." | Reserve it for high-stakes reasoning. Use cost/quality tradeoff deliberately. |

# Reference

- [Gemini Prompting Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- [Gemini Model Parameters](https://ai.google.dev/gemini-api/docs/models)
