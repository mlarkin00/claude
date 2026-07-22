# Review Report & Improvement Protocol

How to present findings and how to turn them into committed improvements.

## Table of Contents

1. [Severity model](#severity-model)
2. [Report structure](#report-structure)
3. [Applying improvements](#applying-improvements)
4. [Re-verification](#re-verification)

---

## Severity model

Rank every finding so the user knows what to fix first. Merge the mechanical
severities (error/warning/info) with judgment from the rubric.

| Severity     | Meaning                                                                    |
| ------------ | -------------------------------------------------------------------------- |
| **Blocker**  | Breaks discovery, breaks a path, or is a security risk (secret, exfiltration, covert instruction). Fix before the skill is used again. |
| **High**     | Materially hurts triggering or reliability (weak description, no gotchas, interactive script, unhandled branch). |
| **Medium**   | Departs from best practice (bloated body, duplication, missing --help, no TOC). |
| **Low**      | Cosmetic / stylistic (voice slips, phrasing, minor freshness nits).        |

Any security or path-integrity error is at least **High**; a hardcoded secret
or covert instruction is always a **Blocker**.

---

## Report structure

Present the review in this shape. Keep findings concrete: every one names a
location, states the impact, and carries a specific fix.

```markdown
# Skill Review: <skill-name>

## Verdict
<One paragraph: is it production-ready, needs work, or has blockers? Lead with the headline.>

## Scorecard
| Dimension                         | Score (1–5) | Notes                          |
| --------------------------------- | ----------- | ------------------------------ |
| Discovery & Triggering            | x           | ...                            |
| Structure & Progressive Disclosure| x           | ...                            |
| Instructional Content Quality     | x           | ...                            |
| Logic & Path Integrity            | x           | ...                            |
| Scripts & Determinism             | x           | (n/a if no scripts)            |
| Security & Safety                 | x           | ...                            |
| Scoping & Coherence               | x           | ...                            |
| Freshness & Skill Decay           | x           | ...                            |

## Findings (ranked)
### [Blocker] <title>
- **Where:** `path:line`
- **Problem:** <what, with a quote>
- **Why it matters:** <impact on triggering / reliability / safety>
- **Fix:** <the concrete change>

### [High] <title>
...

## Prioritized improvement plan
1. <the change to make first, and why>
2. ...
```

Order findings by severity, then by leverage (triggering and security changes
usually move the needle most).

---

## Applying improvements

This skill does not stop at diagnosis — it implements the fixes. After
presenting the report:

1. **Snapshot first.** Before editing, copy the skill so the change is
   reversible and the before/after is inspectable:
   `cp -r <skill-path> <skill-path>.bak` (remove the `.bak` once the user is happy).
2. **Sort fixes into two buckets:**
   - **Mechanical / unambiguous** (dead paths, missing `set -e`, absent TOC,
     voice fixes, a missing Gotchas section, secret → env var): apply directly.
   - **Judgment calls** (rewriting the description, re-scoping, cutting content
     the model may already know, changing the workflow): propose the specific
     edit and confirm with the user before committing it. Show before/after for
     anything that changes behavior or meaning.
3. **Edit in place**, preserving the skill's existing voice and conventions —
   match its heading style and terminology rather than imposing a template.
4. **Fix the root cause, not the symptom.** A vague description isn't fixed by
   appending keywords; rewrite it around what+when. A bloated body isn't fixed
   by deleting lines; move the detail into a reference and point to it.
5. **Don't overfit.** Skills are used across many prompts. Resist adding narrow
   rules for one example or oppressive MUSTs; prefer a general instruction that
   explains its reasoning.

---

## Re-verification

An improvement isn't done until it's verified.

1. **Re-run the mechanical audit** on the edited skill:
   `python scripts/audit_skill.py <skill-path>` — confirm the findings you
   claimed to fix are gone and you introduced no new ones.
2. **Re-run the triggering test** if the description changed: regenerate the
   3-trigger / 3-near-miss prompts and confirm the new description separates
   them cleanly.
3. **Spot-check paths** you touched still resolve.
4. **Report the delta**: state plainly what changed, what improved (ideally
   with the before/after audit counts), and what you intentionally left alone
   and why. Never claim a fix you didn't verify.
