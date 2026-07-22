# active-skills

A curated set of agent skills, installable as a plugin in both Claude Code and Antigravity. **This repository is the source of truth — clone it to author skills.** The [`mlarkin00/plugins`](https://github.com/mlarkin00/plugins) marketplace mirrors it automatically, so users install everything from that one place and never clone this repo.

The repository root *is* the plugin. Claude Code reads `.claude-plugin/plugin.json`; Antigravity reads `plugin.json`. The two manifests coexist and each carries its own version, so one directory serves both runtimes.

Everything here is skills or skill-authoring tooling. Usage tracking lives in a separate `skill-usage` plugin, deliberately: keeping plugin machinery out of this repo keeps it a clean place to write skills.

## Install

**Claude Code** — via the [`mlarkin00-plugins`](https://github.com/mlarkin00/plugins) marketplace:

```
/plugin marketplace add mlarkin00/plugins
/plugin install active-skills@mlarkin00-plugins
```

Skills are namespaced under the plugin, e.g. `active-skills:systematic-debugging`.

**Antigravity** — installs straight from the repository URL:

```
agy plugin install https://github.com/mlarkin00/active-skills
```

## Authoring

Each skill is a directory under `skills/` containing a `SKILL.md`. That is the whole contract — `skills/` must contain **nothing but skill directories**, because Antigravity installs every entry there as a skill and a loose file becomes a phantom skill in its UI.

After adding, removing, or retitling a skill, regenerate the inventory below:

```bash
bash scripts/gen-readme.sh
```

To publish: **bump the `version` in `plugin.json` and `.claude-plugin/plugin.json`, then push to `main`.** A sync workflow in `mlarkin00/plugins` mirrors the change into the marketplace and updates its `marketplace.json` to the new version. The bump is what matters — plugin caches are version-keyed, so a skill change shipped without a version bump will not reach anyone. The sync surfaces a warning when content changes without a bump.

## Layout

| Path | Purpose |
|---|---|
| `skills/` | The skills. Only skill directories belong here. |
| `scripts/gen-readme.sh` | Regenerates the inventory below. |
| `sidecars/check-updates/` | Antigravity: periodic update check. |
| `tests/` | Tests for the update-check sidecar. |
| `.claude-plugin/plugin.json`, `plugin.json` | The two runtime manifests. |

## Skills

<!-- SKILLS:START -->
**39 skills** (auto-generated — do not edit by hand):

- **`auto-mode`** — Plan-driven autonomous execution where the agent writes a full plan, batches clarifying questions up front, and executes phase-by-phase with testing and summary logging.
- **`brainstorming`** — Use this skill when you need to turn ideas into fully formed designs and specs through natural collaborative dialogue before any creative work - creating features, building components, adding functionality, or modifying behavior.
- **`close-session`** — Use when the user says "close session", "wrap up", "end session", "done for now", "save my work", "commit and push", or when finishing a block of work with no further tasks planned to update project documentation, commit changes, and push safely to GitHub.
- **`cloud-build-triggers`** — Use when creating, updating, or managing Google Cloud Build triggers. This skill handles 1st Gen and 2nd Gen GitHub connections, branch patterns, and mandatory IAM validation.
- **`code-design`** — Use when starting new feature work, building a new system or module, or when the user asks how something should be designed or architected. Triggers on phrases like 'design this', 'how should we build', 'plan the architecture', 'think through the approach', 'write a design doc', 'what's the right way to implement', or any request that involves deciding *how* something should work before writing code. Also use when the user provides requirements or a spec and expects a structured design rather than jumping straight to implementation. This skill MUST be used before implementation begins on any non-trivial feature — if the work touches more than one file or introduces a new abstraction, design first.
- **`dispatching-parallel-agents`** — Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
- **`documentation-lookup`** — Use up-to-date library and framework docs via Context7 MCP instead of training data. Activates for setup questions, API references, code examples, or when the user names a framework (e.g. React, Next.js, Prisma).
- **`executing-plans`** — Use when you have a written implementation plan to execute in a separate session with review checkpoints
- **`explanatory-mode`** — Use this skill ONLY when the user explicitly asks to "explain" something or provides an instruction to write or document something in an "explanatory way". It is essential for providing deep technical insights and instructional breakdowns.
- **`finishing-a-development-branch`** — Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
- **`frontend-design`** — Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.
- **`gcloud`** — Use this skill when interacting with Google Cloud services using the gcloud CLI. Use when managing cloud resources, querying configurations, or troubleshooting issues via gcloud.
- **`gemini-agents-api`** — Manages custom Agent resources on Gemini Enterprise Agent Platform. Use when the user wants to programmatically create, configure, list, update, or delete stateful, server-managed Agent resources (including mounting files, skills, and tools) before executing conversations.
- **`gemini-interactions-api`** — Guides the usage of Gemini Interactions API on Gemini Enterprise Agent Platform. Use when the user wants to use the stateful, server-managed Interactions API for multi-turn conversations, background execution, streaming, structured output, and function calling on the Agent Platform.
- **`git-sync`** — Use this skill when the user asks to sync, update, pull, push, fetch, merge, or rebase the codebase with the remote GitHub repository, or when they run the slash command /git-sync with optional parameters (e.g., "/git-sync", "/git-sync prefer remote", "/git-sync prefer local"). This skill handles git merge or rebase operations safely, ensuring local changes are preserved and prompting the user only if there are irreconcilable merge conflicts, or automatically resolving conflicts if a preference (local/remote) is specified. Make sure to use this skill whenever the user mentions git, remote, syncing, pushing, pulling, or keeping the workspace up to date.
- **`google-antigravity-sdk`** — Design, implement, and debug autonomous AI agents and multi-agent systems using the Google Antigravity (AGY) SDK. ACTIVATE this skill when the user wants to create, configure, or orchestrate Google Antigravity agents.
- **`google-cloud-recipe-auth`** — Provides expert guidance on authenticating and authorizing to Google Cloud services and APIs, covering human users, service identities, Application Default Credentials (ADC), and best practices for secure access.
- **`grill-me`** — A relentless interview to sharpen a plan or design.
- **`grilling`** — Grill the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases.
- **`guidelines`** — Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
- **`handoff`** — Compact the current conversation into a handoff document for another agent to pick up.
- **`managing-agent-instructions`** — Use when the user asks to "write a doc", "create agent instructions", "update AGENTS.md", "sync context files", "refine project rules", "update the TODO", "add a task to the backlog", or "update DESIGN.md". Use this skill to manage persistent, high-signal project-specific context in AGENTS.md, GEMINI.md, CLAUDE.md, the project task backlog in .agents/TODO.md, and the design system specification in DESIGN.md.
- **`new-prompt`** — Pre-processes raw user input through the prompt-design framework before execution. Trigger when user invokes /new-prompt "<task>" or says "refine this prompt then run it". Takes raw intent, applies context engineering to produce a deterministic prompt, then executes it as the main task.
- **`optimizing-prompts-w-vertex`** — Use when a user wants to iteratively improve a prompt using Vertex AI Prompt Optimizer with zero-shot optimization and steering hints between iterations.
- **`project-setup`** — Use this skill whenever the current directory lacks an `AGENTS.md` file, a `.git` repository, or other standard project descriptors, indicating it may be a new or unconfigured project. This skill MUST trigger when the user says "set up a new project," "initialize this folder," "start a new repo," or whenever an agent session begins in a directory that doesn't have a clear project-root defined. Proactively use this skill to establish the current directory as the project-root and coordinate the generation of foundational docs via the `managing-agent-instructions` skill.
- **`prompt-design`** — Use this skill when you need to design, improve, or iterate on AI prompts and system instructions. This skill transitions from "vibe-based" prompting to deterministic Context Engineering, ensuring prompts are structured for both standard and reasoning models.
- **`receiving-code-review`** — Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
- **`refresh-skills`** — Use this skill when the user asks to sync, update, or refresh the local agent-skills repository with its remote tracking branch on GitHub, or when they mention 'refresh skills', 'update agent skills', 'pull latest skills', 'sync agent skills repo with github', or similar commands. This skill looks for the repository at ~/agent-skills, runs the sync using the git-sync helper script with the 'prefer remote' configuration, and guides conflict resolution if any issues arise.
- **`requesting-code-review`** — Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- **`skill-creator-enhanced`** — Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, update or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
- **`skill-improvement`** — Use when reviewing, auditing, critiquing, or improving an EXISTING agent skill against the Agent Skills specification and best practices, and then implementing the fixes — e.g. "audit the skill in active-skills/gcloud against the spec", "review my SKILL.md and make it better", "is this skill following best practices", "improve this skill's triggering", "check my skill for security issues", or a final pass before publishing/sharing a skill. This skill diagnoses a skill (SKILL.md plus its scripts/references/assets) across triggering, progressive-disclosure structure, content quality, path integrity, script safety, security, scoping, and freshness, THEN implements the improvements and re-verifies them. Make sure to use this skill whenever the user wants an existing skill evaluated or upgraded, even if they don't say the word "audit". For authoring a brand-new skill from scratch or running full eval-loop benchmarks, use skill-creator-enhanced instead.
- **`skill-portfolio-review`** — Use when reviewing an ENTIRE collection of agent skills (not one skill) to find clusters of semantically related skills that could be consolidated into a broader "umbrella" skill — e.g. "review all my skills for consolidation", "are any of these skills redundant or overlapping", "which skills can be merged", "my skills library has grown, clean it up", or "consolidate the skill portfolio". This skill scans every skill in a directory, clusters them by semantic similarity, applies the umbrella-class test, and returns an implementation-ready report: the new/consolidated skills to build, the skills to remove, portfolio-level learnings, and exact ordered steps another agent can execute to make the changes. Make sure to use this whenever the user wants their whole skill set audited for redundancy or umbrella-ification, even if they don't say "consolidate". For reviewing or improving a SINGLE skill against best practices use skill-improvement; for authoring one new skill use skill-creator-enhanced.
- **`subagent-driven-development`** — Use when executing implementation plans with independent tasks in the current session
- **`systematic-debugging`** — Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- **`test-driven-development`** — Use when implementing any feature or bugfix, before writing implementation code
- **`using-agent-workflow`** — Use when starting any conversation - establishes how to find and use agent-workflow skills, requiring Skill/activate_skill invocation before ANY response including clarifying questions
- **`using-git-worktrees`** — Use when starting feature work that needs isolation from current workspace or before executing implementation plans that involve source code changes or feature development - creates isolated git worktrees in the project root (.worktrees/) with safety verification
- **`verification-before-completion`** — Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
- **`writing-plans`** — Use when you have a spec or requirements for a multi-step task, before touching code
<!-- SKILLS:END -->
