---
name: designing-code
description: "Use when starting new feature work, building a new system or module, or when the user asks how something should be designed or architected. Triggers on phrases like 'design this', 'how should we build', 'plan the architecture', 'think through the approach', 'write a design doc', 'what's the right way to implement', or any request that involves deciding *how* something should work before writing code. Also use when the user provides requirements or a spec and expects a structured design rather than jumping straight to implementation. This skill MUST be used before implementation begins on any non-trivial feature — if the work touches more than one file or introduces a new abstraction, design first."
---

# Designing code

This skill produces a design document that captures the _why_, _what_, and _how_ of a piece of work before any code is written. The goal is to surface bad assumptions, missing requirements, and architectural mismatches early — when they are cheap to fix.

## When to Use This Skill

- A new feature, service, or module is being built
- An existing system needs significant restructuring
- The user provides requirements and needs a design review before implementation
- There are multiple viable approaches and the trade-offs need to be made explicit
- The work crosses service, module, or team boundaries

## Workflow

### Phase 1: Understand the Landscape

Before proposing anything, understand what already exists. Skipping this phase leads to designs that ignore existing patterns, duplicate abstractions, or conflict with conventions already established in the codebase.

- [ ] **Read the requirements.** Restate them back in a numbered list. Identify anything ambiguous or underspecified — flag these as open questions, do not assume answers.
- [ ] **Explore the codebase.** Look for:
  - Existing modules or services that touch the same domain
  - Patterns already in use (naming conventions, directory structure, abstraction style)
  - Data models that the new work must integrate with or extend
  - Configuration, environment, or infrastructure conventions
  - Tests — what testing patterns exist? What coverage expectations are implied?
- [ ] **Check git history.** Look at recent commits in the relevant area. Understand what direction the code is moving and whether there is in-flight work that could conflict.
- [ ] **Summarize findings.** Write a short "Landscape" section capturing what exists, what patterns are in play, and what constraints the codebase imposes. This section prevents the design from contradicting reality.

### Phase 2: Clarify Requirements

Good designs come from good requirements. This phase turns vague asks into concrete, testable statements.

- [ ] **Functional requirements.** What must the system _do_? Express each as a user-visible behavior: "When X happens, the system does Y." Avoid implementation language — describe outcomes, not mechanisms.
- [ ] **Non-functional requirements.** What qualities must the system have?
  - Performance targets (latency, throughput)
  - Scalability expectations (data volume, user growth)
  - Reliability/availability requirements
  - Security and compliance constraints
  - Observability needs (logging, metrics, alerting)
- [ ] **Constraints.** What is non-negotiable?
  - Technology restrictions (language, framework, cloud provider)
  - Timeline or team capacity limits
  - Backward compatibility requirements
  - Budget or cost ceilings
- [ ] **Out of scope.** Explicitly state what this design does NOT cover. This prevents scope creep and sets expectations.
- [ ] **Open questions.** List anything that cannot be resolved without user input. Do not bury these — present them prominently and block on them if they affect the design's viability.

### Phase 3: Design

This is where the actual architecture gets proposed. Every decision must be accompanied by its rationale — a design without reasoning is just a guess that happens to be written down.

#### 3a. Architecture Overview

Describe the high-level structure. Include:

- **Components and their responsibilities.** Name each component, state what it does, and define its boundaries. A component that "handles everything related to X" is a red flag — break it down further.
- **Data flow.** Trace the path of a request or event through the system. Cover both the happy path and the most important error paths.
- **Integration points.** Where does this design touch existing systems? What contracts (APIs, message formats, shared state) must it honor?
- **Diagram.** Include a text-based architecture diagram showing components and their relationships. Use ASCII art, Mermaid, or similar — something that lives in the markdown file and does not require external tools to view.

#### 3b. Data Model

If the design introduces or modifies persistent data:

- Define the schema (tables, collections, or document structures)
- Specify relationships and cardinality
- Call out indexing strategy for known query patterns
- Address migration path from current state

#### 3c. API / Interface Design

If the design exposes an interface (HTTP API, CLI, library API, event contract):

- Define each endpoint or method with its inputs, outputs, and error cases
- Follow conventions already established in the codebase
- Specify authentication/authorization requirements
- Include example request/response pairs for non-trivial operations

#### 3d. Key Design Decisions

For each significant choice, document:

| Decision           | Choice            | Alternatives Considered | Rationale              |
| :----------------- | :---------------- | :---------------------- | :--------------------- |
| _What was decided_ | _What was chosen_ | _What else was viable_  | _Why this option wins_ |

This table is the most valuable part of the design. It captures institutional knowledge that would otherwise live only in someone's head. Future readers can understand not just what was built, but _why_ — and whether the original reasoning still holds.

#### 3e. Patterns and Conventions

Reference design patterns only when they solve a specific problem identified in this design. Do not list patterns for the sake of listing them.

For each pattern used:

- Name the pattern
- State the problem it solves _in this context_
- Show how it maps to the components in this design
- Note any adaptation from the canonical version and why

### Phase 4: Risk and Trade-offs

Every design makes trade-offs. Making them explicit prevents surprises during implementation.

- [ ] **What could go wrong?** Identify failure modes, edge cases, and scaling limits.
- [ ] **What are we trading off?** State what the design optimizes for and what it sacrifices. (e.g., "Optimizes for read latency at the cost of write complexity.")
- [ ] **What would we do differently at 10x scale?** This reveals assumptions baked into the design and helps assess its shelf life.
- [ ] **Security considerations.** Identify attack surfaces, trust boundaries, and data sensitivity. Do not treat this as a checkbox — think about what an attacker would target.

### Phase 5: Implementation Approach

Bridge the gap between design and code. This section makes the design _actionable_.

- [ ] **Implementation order.** Break the work into phases or milestones. Each phase must be independently deployable or at least independently testable. Avoid "big bang" implementations where nothing works until everything works.
- [ ] **Testing strategy.** For each component or phase, state what tests are needed and at what level (unit, integration, end-to-end). Reference existing test patterns in the codebase.
- [ ] **Migration plan.** If replacing or modifying existing functionality, define how to transition safely. Consider feature flags, blue-green deployment, or incremental rollout as appropriate.

## Output Format

Produce a single markdown file with this structure:

```
# Design: [Feature/System Name]

**Status:** Draft | In Review | Approved
**Author:** [name]
**Date:** [date]

## Context
[Why this work is happening — the problem or opportunity]

## Landscape
[What exists today — relevant codebase patterns, existing systems, constraints]

## Requirements
### Functional
### Non-Functional
### Constraints
### Out of Scope
### Open Questions

## Design
### Architecture Overview
### Data Model
### API / Interface Design
### Key Decisions
### Patterns

## Risks and Trade-offs

## Implementation Approach
### Phases
### Testing Strategy
### Migration Plan
```

Not every section applies to every design. Omit sections that are genuinely irrelevant — but err on the side of inclusion. A section that says "N/A — no persistent data is introduced" is better than a missing Data Model section that leaves the reader wondering if it was forgotten.

## Writing the Design Document

- **Save the document** as `DESIGN.md` in the root of the relevant module or feature directory. If no clear location exists, place it in the project root.
- **Write for the skeptical reader.** Assume the reader will challenge every decision. Pre-empt objections by including rationale.
- **Be concrete.** "The service will be fast" is not a requirement. "p95 latency under 200ms for read operations" is.
- **Use the codebase's language.** If the project calls them "handlers," do not call them "controllers." If the project uses snake_case, do not switch to camelCase in the design.
- **Show, don't tell.** Include code sketches, schema definitions, and API examples. Abstract descriptions without concrete examples leave too much room for misinterpretation.

## Gotchas and Anti-Patterns

| Mistake                                              | Why It Fails                                                                                 | What to Do Instead                                                     |
| :--------------------------------------------------- | :------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------- |
| Designing without reading the codebase               | Proposes abstractions that conflict with existing patterns or duplicates what already exists | Always complete Phase 1 before Phase 3                                 |
| Listing every design pattern you know                | Adds noise, signals insecurity, buries actual decisions                                      | Only reference patterns that solve a specific problem in _this_ design |
| Leaving requirements vague                           | "Fast" and "scalable" mean different things to different people — implementation will drift  | Quantify every non-functional requirement with a target number         |
| Skipping the Decisions table                         | The most valuable artifact for future maintainers is lost                                    | Document at least 3 key decisions with alternatives and rationale      |
| Writing a design that requires reading external docs | The design should stand alone as a complete picture                                          | Inline the relevant details; link to sources for depth                 |
| Proposing a "big bang" implementation                | Nothing works until everything works; impossible to course-correct                           | Break into independently testable phases                               |
| Treating security as an afterthought                 | Retrofitting security is 10x harder than designing it in                                     | Address security in Phase 4 for every design                           |
