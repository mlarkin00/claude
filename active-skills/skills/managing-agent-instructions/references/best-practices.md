# Agent Context Engineering: Best Practices

## Table of Contents

1. [The "Machine README" Philosophy](#the-machine-readme-philosophy)
2. [Hierarchical Context](#hierarchical-context)
3. [The Golden Path: Operational Commands](#the-golden-path-operational-commands)
4. [Standalone Assistant-Specific Files](#standalone-assistant-specific-files)
5. [Refining Style & Constraints](#refining-style--constraints)

## The "Machine README" Philosophy

Traditional READMEs and architecture docs (`ARCH.md`) are for humans; they contain explanations, narratives, and structure optimized for human understanding. **Agent briefing files (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`) and backlogs (`.agents/TODO.md`) are strictly for machines.**

- **Human-centric vs. Agent-centric**: 
  - **Human-optimized (`README.md`, `ARCH.md`)**: Written for readability, narrative explanation, and structural clarity so developers can quickly understand the project's purpose and system design.
  - **Agent-optimized (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `TODO.md`)**: Structured for token efficiency, speed, and parsing by LLMs. Omit pleasantries, prose explanations, and human-friendly fluff. Use dense checklists, raw commands, and highly-specific directives.
- **Amnesiac Briefing**: Assume the agent is a Senior Engineer who has never seen this project.
- **High Signal-to-Noise**: Every word costs money (tokens) and attention. If it's obvious from the file tree, don't write it.

## Hierarchical Context

Documentation should traverse the directory tree.

- **Root (`/AGENTS.md`)**: Global project standards, shared utilities, core tech stack.
- **Subdirectory (`/src/modules/auth/AGENTS.md`)**: Domain-specific quirks, local test helpers, specific security constraints for the module.

## The Golden Path: Operational Commands

Agents need to know exactly how to verify their work.

- **Bad**: "Tests are in the tests folder."
- **Good**: `npm run test:unit --filter "@shared/utils"`
- **Why**: Precise commands prevent the agent from guessing or running massive, slow test suites unnecessarily.

## Standalone Assistant-Specific Files

Maintain separate files for separate assistants (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`) at the project root rather than symlinking them. This allows tailoring instructions to each assistant's unique capabilities, tools, and quirks (e.g., `GEMINI.md` for Gemini CLI, `CLAUDE.md` for Claude Code). If symlinks exist, they MUST be removed and replaced with standalone files.

## Refining Style & Constraints

Focus on what linters _cannot_ catch.

- **Patterns**: "Use Zod for all external API validation."
- **Constraints**: "Never use `localStorage` directly; use the `StorageWrapper` utility."
- **Ownership**: "The `legacy/` directory is read-only. Never modify files there."
