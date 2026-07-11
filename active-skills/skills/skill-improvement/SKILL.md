---
name: skill-improvement
description: Use when reviewing, auditing, critiquing, or improving an EXISTING agent skill against the Agent Skills specification and best practices, and then implementing the fixes — e.g. "audit the skill in active-skills/gcloud against the spec", "review my SKILL.md and make it better", "is this skill following best practices", "improve this skill's triggering", "check my skill for security issues", or a final pass before publishing/sharing a skill. This skill diagnoses a skill (SKILL.md plus its scripts/references/assets) across triggering, progressive-disclosure structure, content quality, path integrity, script safety, security, scoping, and freshness, THEN implements the improvements and re-verifies them. Make sure to use this skill whenever the user wants an existing skill evaluated or upgraded, even if they don't say the word "audit". For authoring a brand-new skill from scratch or running full eval-loop benchmarks, use skill-creator-enhanced instead.
metadata:
  category: code-quality
---

# Skill Improvement

Review an existing agent skill against the specification and best practices,
then **implement the improvements** and verify them. Auditing is the diagnostic
first half; the job is not finished until the fixes are applied and re-checked.

Use `scripts/audit_skill.py` for the deterministic, objectively-checkable
findings, and the rubric in `references/rubric.md` for the parts that need
judgment (does the description actually trigger? is the content non-obvious? is
the scope coherent?). A machine can tell you a path is broken; only judgment
can tell you a description is too timid.

## Workflow

Work through these phases in order. Do not stop after the report — Phase 5 and 6
are the point of the skill.

### 1. Locate and inventory

Identify the target skill directory (the one containing `SKILL.md`). Read
`SKILL.md` in full and list the bundled resources:

```bash
find <skill-path> -type f -not -path '*/__pycache__/*' | sort
```

Note what exists (`scripts/`, `references/`, `assets/`) and read the scripts and
any reference files the body points to. If the user pointed at a repo of many
skills rather than one, ask which skill (or offer to review each in turn).

### 2. Run the mechanical pre-pass

```bash
python scripts/audit_skill.py <skill-path>
```

It emits JSON to stdout (findings with `severity`, `dimension`, `location`,
`message`, `fix`) and a one-line summary to stderr. These are the checks not
worth re-deriving by hand every review: frontmatter validity, name↔directory
match, description length, body size, broken/absolute paths, resource nesting,
script fail-fast/interactivity/`--help`, hardcoded-secret and adversarial-
instruction scans, and reference-file TOCs. Treat its output as the objective
layer of the review — necessary, not sufficient.

### 3. Deep review with the rubric

Read `references/rubric.md` and score the skill **1–5** on each dimension,
citing concrete evidence (file, line, quote). The rubric covers: Discovery &
Triggering, Structure & Progressive Disclosure, Instructional Content Quality,
Logic & Path Integrity, Scripts & Determinism, Security & Safety, Scoping &
Coherence, and Freshness & Skill Decay. Never assert a score without a
citation.

### 4. Run the triggering test

The description decides whether the skill is ever consulted, so test it
directly. Using **only** the description, generate 3 realistic prompts that
should trigger the skill and 3 near-misses that should not. If the should-
trigger set feels forced, the description is too narrow; if the near-misses
would also fire, it is too broad. This is the fastest way to catch the most
common failure — a skill that never triggers.

### 5. Write the review report

Produce the ranked report defined in `references/report-template.md`: a verdict,
a scorecard, findings ordered by severity (Blocker → High → Medium → Low), each
with a location, the impact, and a concrete fix, and a prioritized improvement
plan. Lead with the headline: production-ready, needs work, or has blockers.

### 6. Implement the improvements, then re-verify

This is where the skill earns its name. Follow the improvement protocol in
`references/report-template.md`:

- **Snapshot first** (`cp -r <skill-path> <skill-path>.bak`) so changes are reversible.
- **Apply mechanical/unambiguous fixes directly** (dead paths, missing `set -e`, absent TOC, voice fixes, secret → env var, a missing Gotchas section).
- **Propose judgment calls before committing them** (rewriting the description, re-scoping, cutting content the base model already handles) — show before/after for anything that changes meaning or behavior.
- **Fix root causes, not symptoms**, preserve the skill's existing voice, and don't overfit to one example.
- **Re-run `audit_skill.py`** and, if the description changed, the triggering test. Confirm the findings you fixed are gone and no new ones appeared.
- **Report the delta**: what changed, what improved (before/after audit counts help), and what you deliberately left alone and why. Never claim a fix you didn't verify.

## What good looks like

A strong skill: has a description stating **what** it does and **when** to use
it with realistic trigger phrases; keeps `SKILL.md` lean and pushes detail into
`references/`; writes imperative instructions that **explain their why** instead
of stacking bare MUSTs; includes a Gotchas/Anti-Patterns section; references
only paths that resolve; ships fail-fast, non-interactive scripts; hardcodes no
secrets and makes no covert requests; covers one coherent job; and stays
current with the tools it targets. Measure the target against that bar, then
move it there.

## Gotchas & Anti-Patterns

| Excuse                                                              | Reality                                                                                     |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| "The mechanical audit passed, so the skill is fine."               | The script only checks the objective layer. A description can be spec-valid and still never trigger. Always run the rubric and the triggering test. |
| "I wrote a thorough report, so I'm done."                          | The user asked for improvement, not just diagnosis. Implement the fixes and re-verify (Phases 5–6), don't hand back a to-do list. |
| "The description is short but accurate, that's good enough."       | Under-triggering is the #1 failure. Accurate-but-timid descriptions get skipped. Add when-to-use and realistic trigger phrases. |
| "This instruction is a MUST, so I'll leave it in ALL CAPS."        | Rule-without-reason invites the agent to rationalize skipping it. Reframe as "do X because Y" — reasons survive paraphrase; shouting doesn't. |
| "More instructions make the skill more reliable."                  | Content the base model already handles wastes tokens and over-constrains reasoning. Cut anything the agent would get right without it. |
| "I'll just append keywords to fix a vague description."            | Keyword salad is a symptom fix. Rewrite around what+when so the description actually discriminates real triggers from near-misses. |
| "I edited the skill; the fix is obviously correct."               | Unverified fixes break things. Re-run `audit_skill.py` and the triggering test before claiming success. |
| "I found a hardcoded key but the score is otherwise high."        | A secret, exfiltration path, or covert instruction is a Blocker regardless of any other score. Escalate it. |
| "I'll flatten this into my own clean template."                    | Imposing a template erases the skill's voice and context. Edit in place, matching its existing style and terminology. |

## Reference files

- **`scripts/audit_skill.py`** — deterministic pre-pass; JSON to stdout, summary to stderr. Run with `--help` for usage, `--strict` to exit non-zero on errors (CI gate).
- **`references/rubric.md`** — the full 1–5 scoring rubric across all dimensions, with anchors, evidence rules, and the trajectory-grounded refinement technique.
- **`references/report-template.md`** — the severity model, report structure, the apply-improvements protocol, and re-verification steps.
