---
name: auditing-skills
description: Use this skill when auditing an agent skill directory against the industry-standard Agent Skills Specification (v1.1). Trigger this skill when tasked to "review a skill", "audit a skill", "verify skill standards", or "check skill quality". This skill provides an exhaustive verification of naming, structure, tone, script standards, evaluation sets, and security.
---

# Auditing Skills

Execute a rigorous, exhaustive audit of the target skill directory. You MUST NOT skip any section of the specification.

## 1. Automated Baseline Audit

- **Step:** Run the baseline audit script to catch deterministic violations.
- **Action:** `python3 scripts/audit_skill.py <path_to_skill>`
- **Check:** Review the JSON output for any `❌` or `⚠️` status.

## 2. Frontmatter & Description Audit

- **Name:** 1-64 chars, kebab-case. Use simple and descriptive names (e.g., `code-design` instead of `designing-code`, `doc-review` instead of `reviewing-docs`). Avoid gerund forms (verbs ending in -ing).
- **Description:** 1-1024 chars. **MUST start with "Use when..." or "Use this skill when..."**.
- **Rule:** Description MUST NOT summarize the skill's workflow. It should only describe triggering symptoms and context.
- **Check:** Verify the description serves as a routing signal, not a shortcut.

## 3. Instruction & Tone Audit

- **Rule:** Use "Must," "Always," and "Never." Avoid passive suggestions like "should" or "consider."
- **Rule:** Body must be under 5,000 tokens/500 lines for efficiency.
- **Rule:** Use explicit `[ ]` checklists for multi-step workflows.
- **Rule:** No first-person prose ("I," "me," "my," "we").
- **Requirement:** MUST include "Gotchas," "Anti-Patterns," or "Common Mistakes" sections providing project-specific wisdom.
- **Bulletproofing:** High-stakes skills SHOULD include a "Rationalization Table" (Excuse vs. Reality) and a "Red Flags" list to resist shortcuts.

## 4. Path & Resource Audit

- **Requirement:** All paths MUST be relative (e.g., `scripts/run.sh`) and use forward slashes (`/`).
- **Check:** Ensure regex ignores string escapes like `\n` in graphviz or code blocks.

## 5. Deterministic Script Audit (scripts/)

- **Rule:** Bash scripts MUST include `set -e`.
- **Rule:** Python scripts SHOULD use PEP 723 inline dependencies (`# /// script`).
- **Rule:** All scripts MUST include `--help` documentation and examples.
- **Rule:** Destructive scripts MUST include `--dry-run` and be idempotent.
- **Rule:** MUST NOT include interactive prompts. Status to `stderr`, data to `stdout` as JSON.

## 6. Reference Documentation Audit (references/)

- **Rule:** Any file over 100 lines MUST include a Table of Contents at the top.
- **Rule:** Prefer modular files (sub-topic focus) over monolithic ones.

## 7. Evaluation Set Audit (evals/)

- **Requirement:** MUST include an `evals/` directory with standardized test queries.
- **Rule:** Recommend at least 20 queries (50% positive triggers, 50% near-misses).
- **Structure:** `evals.json` cases MUST include `prompt`, `trap` (baseline failure description), and objective `assertions`.

## 8. Security & Risk Audit

- **Credential Check:** Scan all files for hardcoded secrets, keys, or passwords.
- **Network Check:** Flag any use of `curl`, `fetch`, or `http` for verification against an allowlist.
- **Privilege Check:** Ensure `allowed-tools` is scoped to least privilege.

# Rationalization Table (Common Excuses)

| Agent Thought                      | Reality                                                                                               |
| :--------------------------------- | :---------------------------------------------------------------------------------------------------- |
| "This is a small/simple skill."    | Specification applies to ALL skills regardless of size. Audit everything.                             |
| "The description is close enough." | Triggers are the primary routing signal. "Use when..." or "Use this skill when..." is mandatory.      |
| "Workflow summary is helpful."     | Trap! Workflow summaries in descriptions cause agents to skip the body. Forbid them.                  |
| "I'll skip the script check."      | Scripts are high-risk deterministic bridges. Audit every flag and dependency.                         |
| "I'll skip the TOC check."         | Progressive disclosure requires TOC for context efficiency. Verify it.                                |
| "Evals aren't strictly required."  | Production-ready skills MUST be verifiable. Require the `evals/` folder with `trap` and `assertions`. |

# Output Format

Provide your findings in a structured Markdown table, followed by a **Remediation Plan**.

| Component   | Status   | Finding | Requirement |
| :---------- | :------- | :------ | :---------- |
| Naming      | ✅/❌    | ...     | ...         |
| Frontmatter | ✅/❌/⚠️ | ...     | ...         |
| Tone        | ✅/❌/⚠️ | ...     | ...         |
| Paths       | ✅/❌    | ...     | ...         |
| Scripts     | ✅/❌/⚠️ | ...     | ...         |
| References  | ✅/❌    | ...     | ...         |
| Evals       | ✅/❌    | ...     | ...         |
| Security    | ✅/❌    | ...     | ...         |

# Remediation Plan

For each ❌ or ⚠️, provide the exact `replace` or `write_file` block needed to bring the skill into compliance.

---

[Load Reference Spec](references/agent-skill-spec.md)

```

```
