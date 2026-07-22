# Agent Instruction Quality Assessment Rubric

## Scoring Rubric

### 1. Project Goal Alignment (10 points)

**10 points**: The project goal is clearly stated as the first element in the document. It serves as an active constraint for all designs, plans, and implementations.
**5 points**: The project goal is present but not clearly prioritized or placed at the top.
**0 points**: No project goal is defined.

### 2. Operational Commands (15 points)

**15 points**: All essential "Golden Path" commands documented with precise strings.

- Build, test (unit/integration), lint, and deployment commands are present.
- Context-specific flags are included (e.g., `--filter`, `--watch:false`).
- Commands are copy-paste ready and verified to work.

**10 points**: Most commands present, some missing specific flags or context.
**5 points**: Basic commands only (e.g., just `npm test`), no context-aware variants.
**0 points**: Sparse or no commands documented.

### 3. Architecture & Tech Stack (15 points)

**15 points**: Clear, high-signal codebase map.

- One-sentence purpose + tech stack map (e.g., "Next.js + Prisma + Tailwind").
- Key directories and module relationships identified.
- Entry points and critical config files (`tsconfig.json`, `Makefile`) noted.
- No redundant information that is obvious from the file tree.

**10 points**: Good architecture overview, minor gaps or slight redundancy.
**5 points**: Basic directory listing only, lacks "why" or relationships.
**0 points**: Vague, incomplete, or no architecture/stack info.

### 4. Style & Conventions (Non-Linter) (15 points)

**15 points**: Specific preferences NOT covered by automated tools.

- Design patterns (e.g., "Repository pattern for DB").
- "Never" rules and strict constraints (e.g., "Never use `localStorage` directly").
- Functional vs. Class component preferences, naming conventions not in ESLint.
- "Why we do it this way" for unusual project-specific patterns.

**10 points**: Some valuable patterns documented, some redundant with linters.
**5 points**: Minimal convention documentation.
**0 points**: No style or convention info.

### 5. Minimalism & Conciseness (15 points)

**15 points**: Dense, machine-optimized high-signal content.

- Briefing files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.agents/TODO.md`) are under 100 lines and contain no human-facing narrative structure, explanations, introductory filler, or pleasantries.
- Conceptual descriptions, narrative flow, and human explanations are restricted to `README.md` and `ARCH.md`.
- Every line in agent-targeted files adds direct utility; no redundancy with code or other docs.

**10 points**: Mostly concise, some padding or verbose sections.
**5 points**: Verbose or contains redundant "human-facing" info.
**0 points**: Mostly filler or restates obvious code/config.

### 6. Currency & Synchronization (15 points)

**15 points**: Reflects current state and synced across files.

- Commands and file paths are accurate to the current codebase.
- `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md` are aligned with no stale/conflicting information, and exist as standalone files (never symlinks).
- References to external docs are valid.

**10 points**: Mostly current, minor drift or missing sync check.
**5 points**: Several outdated references or significant drift between tools.
**0 points**: Severely outdated or completely desynced.

### 7. Actionability & Specificity (15 points)

**15 points**: Instructions are strictly imperative and concrete.

- Uses "The agent MUST" or "Never use..." (Third-person imperative).
- No vague descriptions like "Ensure tests pass."
- Steps are concrete and verifiable.

**10 points**: Mostly actionable, some vague language.
**5 points**: Several theoretical or "should" statements.
**0 points**: Vague, theoretical, or purely descriptive.

## Assessment Process

1. **Discover**: Find all `AGENTS.md`, `GEMINI.md`, `CLAUDE.md` files.
2. **Cross-Reference**: Verify documented commands and paths against the codebase.
3. **Score**: Apply the rubric to each file found.
4. **Identify Gaps**: Note missing "Golden Path" commands or stale info.
5. **Propose**: Generate a Quality Report before making changes.
