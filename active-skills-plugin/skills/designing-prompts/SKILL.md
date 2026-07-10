---
name: designing-prompts
description: Use this skill when you need to design, improve, or iterate on AI prompts and system instructions. This skill transitions from "vibe-based" prompting to deterministic Context Engineering, ensuring prompts are structured for both standard and reasoning models.
---

# Designing Prompts

This workflow transforms unstructured instructions into deterministic context environments. The agent MUST follow the "Goldilocks Principle": avoid both under-provisioning (AI slop) and over-provisioning (attention dilution).

## 1. Audit & Analysis

Analyze the current prompt or instructions against the "Cognitive Architecture" of the target model.

- [ ] **Classify the Agent**: Determine if the task is for a **Simple/Standard Agent** (needs heavy orchestration, CoT triggers) or a **Reasoning Agent** (needs minimal zero-shot, clear problem boundaries).
- [ ] **Identify "Vibe-Based" Patterns**: Look for subjective terms (e.g., "be helpful," "write well"), ambiguous roles, or missing constraints.
- [ ] **Consult Intent**: Ask the user: "What is the primary objective of this task? Who is the intended audience? What are the absolute constraints?"
- [ ] **Colleague Test**: Show the prompt to a colleague with minimal context. If they'd be confused, the model will be too.

## 2. Context Engineering (Implementation)

Reconstruct the prompt using deterministic frameworks.

### Structure & Hierarchy

- **Naming Compliance**: The prompt MUST be named using **kebab-case** and a simple, descriptive pattern (e.g., `report-generate` or `report-generation`, `code-review`). Avoid gerund forms (verbs ending in -ing).
- **XML Boundaries**: Use nested XML tags (e.g., `<context>`, `<constraints>`, `<output_format>`) to create a "map" for the model.
- **Role Calibration**: Define a specific, evidence-based role (e.g., "Senior Systems Architect specializing in Rust") rather than a generic one.
- **Instruction Anchoring**: Place primary directives at the absolute **beginning** (behavioral framing) or the absolute **end** (execution).

### Specificity & Constraints

- **Quantitative Constraints**: Replace subjective terms with measurable ones (e.g., "Under 200 words," "Exactly 3 bullet points," "8th-grade reading level").
- **Affirmative Directives**: Tell the model what it **Must** do. Avoid terms like "should," "consider," or "might."
- **Explicit Scope**: When an instruction should apply broadly, state the scope explicitly (e.g., "Apply this formatting to every section, not just the first one"). Models often do not silently generalize unless told to.
- **Grounding**: For long-context tasks, instruct the model to **quote** relevant parts of the context before synthesizing an answer.

### Long-Context Prompting

For large documents or data-rich inputs:

- **Put longform data at the top**: Place long documents above your query and instructions. This significantly improves response quality — queries at the end can boost quality by up to 30% on complex, multi-document inputs.
- **Structure documents with XML**: Wrap each document in `<document>` tags with `<source>` and `<document_content>` subtags.
- **Ground responses in quotes**: Ask the model to extract and quote relevant passages first, then synthesize. This cuts through document noise.

```xml
<documents>
  <document index="1">
    <source>{{filename}}</source>
    <document_content>{{content}}</document_content>
  </document>
</documents>

Find quotes relevant to {{question}}. Place them in <quotes> tags. Then synthesize your answer in <answer> tags.
```

### Output & Formatting Control

Four techniques to steer output format:

1. **Tell what to do, not what not to do**
   - Instead of: "Do not use bullet points"
   - Use: "Write in smoothly flowing prose paragraphs."

2. **XML format indicators**
   - "Write the analysis section in `<analysis>` tags."

3. **Match prompt style to desired output**
   - A prompt written in flowing prose produces flowing prose output. A prompt full of bullets produces bullets. Match the style.

4. **Detailed prose guidance for heavy formatting control**

```text
When writing reports or analyses, use complete paragraphs and sentences. Reserve markdown for `inline code`, code blocks, and simple headings. Avoid bullet points unless presenting truly discrete items.
```

### Verbosity & Length Control

Models calibrate response length to perceived task complexity. If your product requires a specific style:

- Provide **positive examples** of well-calibrated output — more effective than negative instructions or "don't do X."
- Specify length constraints explicitly: "Respond in 2-3 sentences," "Keep the summary under 150 words."
- If seeing over-explanation, add: "Provide concise, focused responses. Skip non-essential context."

### Tool Use Triggering

Models follow explicit tool use directives more reliably than implicit ones.

- **Be directive**: "Search for this information using the web search tool" beats "Can you look this up?"
- **Describe when and how**: If a tool is under-used, add explicit guidance about when to invoke it and why.
- **Dial back aggressive language**: Instructions like "CRITICAL: You MUST use this tool when..." can cause overtriggering. Use normal-register language: "Use this tool when..."

### Parallel Tool Calls

Models default to serial execution unless instructed otherwise. To unlock parallel execution:

```text
If you intend to call multiple tools and there are no dependencies between the calls, make all independent tool calls in parallel. Never use placeholders or guess missing parameters — if a value is unknown, call tools sequentially to discover it first.
```

To reduce parallelism (e.g., for stability):

```text
Execute operations sequentially with brief pauses between each step to ensure stability.
```

### Empirical Grounding

- **Tool Recommendation**: Explicitly recommend that the agent use provided tools to ensure accuracy and reduce hallucinations.
- **Investigate before answering**: Instruct the model never to speculate about information it has not retrieved. Example:

```text
<investigate_before_answering>
Never speculate about content you have not retrieved. If the user references a file or resource, you MUST fetch it before answering. Make claims only after investigation.
</investigate_before_answering>
```

### Template Variable Design

- **Required vs. Optional**: Clearly define variables using `{{variable_name}}`.
- **Placeholder Examples**: Provide "Example Values" to demonstrate expected input quality.

## 3. Agentic System Prompting

When designing prompts for autonomous agents operating over long horizons:

### Balancing Autonomy and Safety

Without explicit guidance, agents may take hard-to-reverse actions (deleting files, force-pushing, posting to external services). Add:

```text
Consider the reversibility and potential impact of every action. Take local, reversible actions freely. For actions that are hard to reverse, affect shared systems, or could be destructive, ask the user before proceeding.

Actions requiring confirmation:
- Destructive: deleting files/branches, dropping tables, rm -rf
- Hard to reverse: force push, reset --hard, amending published commits
- Visible to others: pushing code, commenting on issues, sending messages, modifying shared infrastructure
```

### State Management & Multi-Window Workflows

For tasks spanning multiple context windows:

- **Structured state for trackable items**: Use JSON/structured formats for test results, task status, task lists.
- **Unstructured text for progress notes**: Freeform notes for general progress and context.
- **Use git for state**: Git provides a log of completed work and restorable checkpoints.
- **Incremental progress**: Explicitly ask the agent to track progress and focus on completing one component before moving to the next.

Example state prompt:

```text
This is a long task. Plan your work clearly. Track progress in progress.txt and structured state in state.json. Commit frequently. Never stop early — complete tasks fully.
```

### Research & Information Gathering

For complex research tasks:

```text
Search for this information in a structured way. As you gather data, develop several competing hypotheses. Track your confidence levels in progress notes. Regularly self-critique your approach. Update a hypothesis tree or research notes file to persist information and provide transparency.
```

### Subagent Orchestration

Guide when to delegate vs. work directly:

```text
Use subagents when tasks can run in parallel, require isolated context, or involve independent workstreams that don't need to share state. For simple tasks, sequential operations, single-file edits, or tasks where you need to maintain context across steps, work directly rather than delegating.
```

### Self-Correction Chaining

The most reliable multi-step pattern: generate → review → refine. Each step is a separate API call so intermediate outputs can be logged and branched:

```text
Step 1: Draft a response to the task.
Step 2: Review the draft against these criteria: {{criteria}}.
Step 3: Revise the draft based on the review.
```

### Avoiding Overengineering

```text
Avoid over-engineering. Only make changes that are directly requested or clearly necessary:
- Scope: Don't add features or abstractions beyond what was asked.
- Documentation: Don't add comments to code you didn't change.
- Defensive coding: Don't add error handling for scenarios that can't happen.
- Abstractions: Don't create helpers for one-time operations.
```

## 4. Verification & Testing

Harden the prompt against "Logic Collision" and "Attention Dilution."

- [ ] **Check for Logic Collision**: In reasoning models, ensure the prompt is not too prescriptive, which can cause recursive loops.
- [ ] **Pressure Test**: Ask: "Will the agent get this wrong without this specific instruction?" If the answer is no, remove the instruction to save tokens.
- [ ] **Positive Example Test**: If you have negative instructions ("don't do X"), convert them to a positive example showing the correct behavior.

## Prompt Naming Conventions

All newly designed prompts MUST follow these naming standards to ensure discoverability and clarity.

- **Simple and Descriptive Name**: Use simple and descriptive names (e.g., `code-design` instead of `designing-code`, `doc-review` instead of `reviewing-docs`). Avoid gerund forms (verbs ending in -ing).
- **Kebab-Case**: Use lowercase letters and hyphens only (no underscores or CamelCase).
- **Action-Oriented**: The name must describe the _primary operation_ the prompt performs.
- **Avoid Generic Nouns**: Do NOT name prompts simply after the domain (e.g., `python-helper` is bad; `python-debug` is good).

# Gotchas & Anti-Patterns

- **Naming Failure**: Using gerund forms (e.g., `designing-code`) instead of simple and descriptive names (e.g., `code-design`). Or using generic nouns/domain names (e.g., `sql-expert`) instead of specific actions (e.g., `sql-optimize`).
- **Workflow in Description**: Summarizing steps in the description causes routing failures.
- **Vibe-Coding**: Using emotional appeals or "stochastic vibes" instead of deterministic constraints.
- **The Suggestion Trap**: Using passive prose allows the agent to rationalize skipping the rule. Use "Must."
- **Over-Orchestration**: Providing too many instructions to a Reasoning Model, leading to degraded performance.
- **Missing "Why"**: Not explaining the motivation behind a constraint, preventing the model from generalizing intent.
- **Implicit Scope**: Assuming an instruction applies broadly without stating it. Always define scope explicitly.
- **Negative-Only Constraints**: Listing what NOT to do without showing what TO do instead. Negative constraints are lossy; positive examples are high-signal.
- **Speculative Claims**: Prompts that allow the agent to answer without first retrieving/reading the relevant content.

# Rationalization Table (Excuse vs. Reality)

| Agent Thought                                    | Reality                                                                       |
| :----------------------------------------------- | :---------------------------------------------------------------------------- |
| "A generic name is fine for a quick prompt."     | Generic names hide the action. Simple, descriptive naming (avoiding gerunds) is mandatory for clarity. |
| "A generic role was added, so it's better."      | Generic roles add noise. Calibration requires specific expertise and context. |
| "The prompt told the model what NOT to do."      | Negative constraints are lossy. Affirmative directives are high-signal.       |
| "It's a reasoning model; it'll figure it out."   | Reasoning models need clear _boundaries_, not just more context.              |
| "The process was summarized in the description." | This blocks the agent from loading the full procedural wisdom.                |
| "One iteration is enough."                       | Test with positive examples; a prompt that passes once may fail on edge cases. |
| "The instruction applies globally."              | Only what is stated explicitly applies. Scope everything.                     |

# Reference Snippets

- [Memory Manifesto](references/memory-manifesto.md)
- [Context Engineering Guide](references/context-engineering-guide.md)
