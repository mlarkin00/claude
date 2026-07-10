---
name: setting-up-projects
description: Use this skill whenever the current directory lacks an `AGENTS.md` file, a `.git` repository, or other standard project descriptors, indicating it may be a new or unconfigured project. This skill MUST trigger when the user says "set up a new project," "initialize this folder," "start a new repo," or whenever an agent session begins in a directory that doesn't have a clear project-root defined. Proactively use this skill to establish the current directory as the project-root and coordinate the generation of foundational docs via the `managing-agent-instructions` skill.
---

# Setting Up Projects

This skill guides the initialization of a new project environment, ensuring that the current directory is correctly identified as the project-root and the necessary agent briefing files and system instructions are created.

## Core Mandates

- **Proactive Initialization**: If the agent detects a lack of standard project files (e.g., `.git`, `AGENTS.md`, `package.json`, `go.mod`), it MUST ask the user if they want to set up a new project in the current directory.
- **Project Root Establishment**: If the user confirms, the current directory MUST be treated as the project-root. All subsequent commands and documentation MUST be relative to this root.
- **Instruction Coordination**: Once a project is established, the agent MUST immediately invoke the `managing-agent-instructions` skill to generate `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, and `DESIGN.md`.
- **Git Awareness**: If a `.git` directory is missing in the project root, the agent MUST search up to 3 levels of parent directories. If an existing `.git` repository is found in the parent chain, the agent MUST treat that as the source of truth for git operations (e.g., the monorepo root). If no `.git` directory is found at any of these levels, the agent MUST explicitly ask the user if they want to run `git init` in the current directory or provide the path to an existing repository.
- **Ignore Files**: The agent MUST suggest or create a basic `.gitignore` file to protect sensitive information and avoid bloating the context window with build artifacts.

## Workflow

### 1. Detection & Confirmation

[ ] **Identify Missing Indicators**: Check for the absence of `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`. Check for a `.git` directory in the current root and search up to 3 parent levels (`../`, `../../`, `../../../`).
[ ] **Ask the User**: If project instructions are missing, ask: "I see this directory is not yet configured as a project. Would you like me to set up a new project here?"
[ ] **Explicit Request**: If the user says "set up a new project" or equivalent, proceed immediately to initialization.

### 2. Initialization

[ ] **Establish Root**: Mark the current directory as the project-root for the session.
[ ] **Git Handling**: - If a `.git` directory was found (in root or parent), ensure it is used for subsequent operations. - If NO `.git` was found in the root or any of the 3 parent levels, ASK the user: "No git repository was found in this directory or its parents. Would you like me to initialize a new repository here (`git init`), or can you provide the path to an existing repository?"
[ ] **Basic .gitignore**: Create a baseline `.gitignore` if it doesn't exist.
[ ] **Invoke `managing-agent-instructions`**: Transition to the `managing-agent-instructions` skill with the objective of "creating a new set of baseline project docs."

### 3. Documentation Generation

The following baseline docs MUST be generated as part of the initial setup:

- **`AGENTS.md`**: Operational briefing (commands, tech stack, style, conventions).
- **`GEMINI.md` / `CLAUDE.md`**: Assistant-specific instructions (MUST be standalone, individual files, never symlinks). If any already exist as symlinks, de-symlink them via `managing-agent-instructions` (`scripts/analyze-agent-docs.sh --fix`) before writing.
- **`DESIGN.md`**: Design system tokens and rationale (in the [google/design.md](https://github.com/google-labs-code/design.md) format, required only for projects with a visual UI).
- **`.agents/TODO.md`**: The initial task backlog.

## Gotchas & Anti-Patterns

| Excuse / Failure                                                                   | Reality                                                                                                        |
| :--------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| "I'll just create the files without asking the user."                              | Always ask for confirmation before initializing a new project root.                                            |
| "I'll skip the `managing-agent-instructions` call and just write a simple README." | READMEs are for humans. `AGENTS.md` is for agents. Use the dedicated skill.                                    |
| "This folder has a `package.json`, so it must already be set up."                  | Manifest files indicate a _project_, but not necessarily an _agent-configured_ project. Check for `AGENTS.md`. |
| "I'll wait for the user to tell me what commands to put in `AGENTS.md`."           | Proactively search for `package.json`, `Makefile`, etc., to identify the "Golden Path" commands.               |
| "I'll create the `DESIGN.md` later."                                               | A baseline `DESIGN.md` should be part of the initial setup, even if it's just a one-sentence overview.         |
| "I'll use Git commands without `git init` first."                                  | Ensure the repo is initialized before attempting other Git operations.                                         |


