# Content Guidelines for Agent Instructions

## High-Signal Content (What TO Document)

### 1. "Golden Path" Commands

Precise strings for common workflows that prevent guesswork.

- **Build**: `npm run build:prod` vs `npm run build:dev`.
- **Verify**: `npm test -- --filter=api` or `make lint`.
- **Environment**: How to set up local data or mocks.

### 2. Non-Obvious "Why"s (Architecture)

Decisions that aren't clear from looking at the code.

- "We use the Repository pattern because of X."
- "The `legacy/` module is read-only; never modify it."
- "Auth must be initialized before any database call."

### 3. Strict Constraints & Gotchas

Rules that prevent recurring bugs or debugging loops.

- "Never use `localStorage` directly; use `StorageWrapper`."
- "Tests MUST run sequentially (`--runInBand`) due to shared DB state."
- "Next.js `NEXT_PUBLIC_*` vars must be set at build time."

### 4. Established Testing Patterns

Guidance on how to verify changes in this specific project.

- "Use `supertest` with the helper in `tests/setup.ts`."
- "Use factory functions in `tests/factories/` instead of inline mocks."

## Low-Signal Content (What NOT to Document)

### 1. Obvious Information

Do not restate what is clear from the file tree or class names.

- **Bad**: "The `UserService` class handles user operations."
- **Why**: The class name already says this.

### 2. Generic AI Advice

Avoid universal best practices that agents already know.

- **Bad**: "Always write tests for new features."
- **Bad**: "Use meaningful variable names."
- **Why**: This is baseline knowledge, not project-specific.

### 3. Transient/Historical Context

Do not include one-off fixes or commit history unless it dictates a future constraint.

- **Bad**: "We fixed a bug in commit abc123 where the login button failed."
- **Why**: It clutters the file and doesn't provide future value.

### 4. Verbose Explanations

Avoid paragraphs. Use tables or short bullet points.

- **Bad**: A 3-paragraph explanation of what JWT is.
- **Good**: "Auth: JWT with HS256, tokens in `Authorization: Bearer` header."

## Target Audience & Density Rules

- **Human-Targeted Files (`README.md`, `ARCH.md`)**: Structured for human readability. Use explanatory paragraphs, narrative flows, diagrams, and structural formatting to make design decisions, architectural context, and high-level project overview easy for humans to comprehend.
- **Machine-Targeted Files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.agents/TODO.md`)**: Structured exclusively for agent efficiency. Omit human-friendly narratives, introductory filler, and conversational explanations. Keep these documents extremely dense, compact, and checklist-driven.

## The Context Window Tax

Every line in an agent instruction file is a "tax" on every subsequent message in the session.

- **Goal**: Maximum utility for minimum tokens.
- **Rule**: If it doesn't save a turn or prevent a mistake, delete it.
