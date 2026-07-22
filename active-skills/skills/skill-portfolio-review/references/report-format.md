# Portfolio Review Report — Format

The deliverable of this skill is a **report that another agent can execute with
no further judgment.** It describes the new/consolidated (umbrella) skills, the
skills to remove, and portfolio-level learnings, and it spells out every change
as concrete, ordered operations with exact paths and commands.

Write the report so a downstream agent (or a maintainer) can implement it
top-to-bottom without re-deriving the analysis: no "consider whether…", no
unresolved choices. Every decision is already made and justified here.

## Table of Contents

1. [Report skeleton](#report-skeleton)
2. [Learnings section](#learnings-section)
3. [Per-change implementation spec](#per-change-implementation-spec)
4. [New / umbrella skill specs](#new--umbrella-skill-specs)
5. [Removals table](#removals-table)
6. [Structured summary block (required)](#structured-summary-block-required)
7. [Self-check before finishing](#self-check-before-finishing)

---

## Report skeleton

```markdown
# Skill Portfolio Review — <portfolio-dir>

## Overview
- Scanned: <N> skills. Candidate clusters: <K>.
- Recommended: <A> new umbrellas, <B> merges into existing skills, <C> demotions,
  <D> removals. <E> skills kept as-is.
- Net: <N> skills → <N-D> skills.

## Learnings
<portfolio-level observations — see below>

## Changes to implement
<one numbered "Change" block per consolidation/removal — the executable core.
Order so that umbrellas are created/patched before their siblings are archived,
and reference migrations come after the target exists.>

## New / consolidated umbrella skills
<a spec per NEW or substantially-rewritten umbrella — see below>

## Skills to remove
<table — see below>

## Skills kept as-is
<one line each: skill — why no merge improves it>

## Structured summary (required)
<the consolidations/prunings YAML block — see below>
```

Lead the Overview with the headline: how many genuine consolidations exist
versus how many clusters are correct as-is. Never pad the count — a clean
portfolio with two real merges is a valid, honest result.

---

## Learnings section

"Any other learnings" — the cross-cutting observations a per-cluster view
misses. Include what applies:

- **Naming** — inconsistent conventions (gerund vs. noun), narrow/session-artifact names (from scan `narrow_named`), names that collide semantically.
- **Scoping patterns** — clusters that are healthy families vs. genuine redundancy; any monolith that should *split* rather than absorb.
- **Coverage gaps** — a category with one overloaded skill, or an obvious umbrella class with no skill serving it.
- **Cross-reference structure** — hubs many skills point at (`referenced_by`), and orphans nothing points at.
- **Triggering risk** — skills whose descriptions overlap enough to misfire against each other (a consolidation or a description fix).

Keep each learning to a sentence or two with the evidence (skill names, scan
fields). These are observations, not commands — the commands live in Changes.

---

## Per-change implementation spec

Each change is a self-contained, ordered set of operations. A downstream agent
runs them verbatim. Use this template per change:

```markdown
### Change <n>: <verb> — <short title>
- **Cluster / members:** <a, b, c>
- **Umbrella class:** <the class they serve>
- **Mechanism:** merge-into-existing <umbrella> | create-new-umbrella <name> | demote <x> into <umbrella>
- **Package integrity:** <support files + skill_md_links that must travel together, or "clean — SKILL.md only">
- **Steps (run in order):**
  1. <exact op — e.g.> Patch `skills/<umbrella>/SKILL.md`: add section `## <label>` containing <the sibling's unique insight, summarized or quoted>.
  2. <e.g.> `git mv skills/<sib>/references/<f>.md skills/<umbrella>/references/<f>.md` and rewrite the link in `skills/<umbrella>/SKILL.md` from `references/<f>.md`.
  3. <e.g.> Archive the sibling: `git mv skills/<sib> .archive/skills/<sib>`.
  4. **Migrate references** (from scan `referenced_by` + repo grep):
     - `skills/<other>/SKILL.md`: repoint "see <sib>" → `<umbrella>`.
     - Fold `skills/<sib>/evals/evals.json` meaningful prompts into `skills/<umbrella>/evals/evals.json`.
  5. **Verify:** re-run `portfolio_scan.py` and `grep -rn "<sib>" <repo> --include='*.md' --include='*.json' | grep -v '/.archive/'` returns nothing.
```

Rules that make the spec safe to execute blind:

- **Order matters.** Create/patch the umbrella *before* archiving siblings; migrate references *after* the target exists.
- **Whole packages only.** If `package integrity` is not "clean", move every listed support file and rewrite its path — never flatten only a SKILL.md.
- **No dangling paths.** The migrate + verify steps are mandatory, not optional; every inbound `skills/<sib>` reference must be repointed or removed.
- **Exact strings.** Give real paths, real `git mv` commands, and the real reference locations — not "update references as needed".

---

## New / umbrella skill specs

For every skill the report says to **create** (create-new-umbrella) or
substantially rewrite, provide a ready-to-build spec so the downstream agent
writes it without guessing:

```markdown
### Umbrella: <name>
- **name:** <kebab-case>
- **description:** <the full frontmatter description, ready to paste — what + when + triggers>
- **category:** <one of the 9>
- **Body outline:** <section headings for the shared workflow>
- **Absorbs:** <sibling> → section `## <label>` (its unique insight: <summary>); <sibling2> → `references/<f>.md` (demoted); ...
- **Support files to create/receive:** <scripts/references it inherits from siblings, with source paths>
```

For **merge-into-existing**, give the same spec framed as a patch: which
sections/support files to add to the existing umbrella and from where.

---

## Removals table

Every skill leaving `skills/` appears here, with its disposition:

| Skill        | Disposition                          | Reason (one sentence)                       | Archive command                                     |
| ------------ | ------------------------------------ | ------------------------------------------- | --------------------------------------------------- |
| `<sib>`      | consolidated into `<umbrella>`       | <why it's not its own class>                | `git mv skills/<sib> .archive/skills/<sib>`  |
| `<stale>`    | pruned (no forwarding target)        | <why obsolete/irrelevant>                   | `git mv skills/<stale> .archive/skills/<stale>` |

"Consolidated" means its content was absorbed into an umbrella; "pruned" means
archived with nothing forwarded. Every row must match exactly one entry in the
structured summary.

---

## Structured summary block (required)

After the human-readable report, emit this machine-readable block so downstream
tooling distinguishes consolidation from pruning and knows each forwarding
target. Every skill in the Removals table MUST appear in exactly one list. Use
this exact format:

````markdown
## Structured summary (required)
```yaml
consolidations:
  - from: <old-skill-name>
    into: <umbrella-skill-name>
    reason: <one short sentence — why merged, not just "similar">
prunings:
  - name: <skill-name>
    reason: <one short sentence — why archived with no merge target>
```
````

- **`consolidations`** (with `into:`) — content absorbed into an umbrella (patched a section, wrote a demoted references file, or created the umbrella from it). `into:` is the `absorbed_into` forwarding target that drives reference migration — set it deliberately.
- **`prunings`** — archived with no absorption (stale/obsolete/irrelevant).
- Leave a list empty (`consolidations: []`) if none. Do not omit the block.

The block is an index into the Changes; the Changes hold the executable detail.

---

## Self-check before finishing

Before returning the report, confirm a downstream agent could execute it blind:

- [ ] Every removal has a Change block with ordered steps and exact paths.
- [ ] Every umbrella that must exist is created/patched *before* its siblings are archived in the step order.
- [ ] Every package with support files or `skill_md_links` moves whole, with paths rewritten.
- [ ] Every `referenced_by` entry and repo-grep hit has a migration step.
- [ ] Every archived skill appears in exactly one of `consolidations` / `prunings`.
- [ ] Kept skills are listed with a one-line reason (so "why wasn't X touched?" is answered).

If the run is analysis-only, still produce the full report (it is the point of
the skill) and state that nothing was executed — the report *is* the plan.
