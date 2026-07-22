---
name: skill-portfolio-review
description: Use when reviewing an ENTIRE collection of agent skills (not one skill) to find clusters of semantically related skills that could be consolidated into a broader "umbrella" skill — e.g. "review all my skills for consolidation", "are any of these skills redundant or overlapping", "which skills can be merged", "my skills library has grown, clean it up", or "consolidate the skill portfolio". This skill scans every skill in a directory, clusters them by semantic similarity, applies the umbrella-class test, and returns an implementation-ready report: the new/consolidated skills to build, the skills to remove, portfolio-level learnings, and exact ordered steps another agent can execute to make the changes. Make sure to use this whenever the user wants their whole skill set audited for redundancy or umbrella-ification, even if they don't say "consolidate". For reviewing or improving a SINGLE skill against best practices use skill-improvement; for authoring one new skill use skill-creator-enhanced.
---

# Skill Portfolio Review

Review a whole collection of skills to find where several narrow skills serve
one **umbrella class** and should become a single broader skill. Operates across
the portfolio, not on one skill — the unit of work is the *set*.

The hard part is not spotting similar names; it is deciding which similarities
are genuine umbrella classes (consolidate) and which are distinct skills that
merely share vocabulary (keep). Merging the latter creates monolithic skills
that are hard to trigger — so this skill treats consolidation as a judgment call
gated by the umbrella-class test, not a race to shrink the count.

**The deliverable is an implementation-ready report** — describing the
new/consolidated umbrella skills, the skills to remove, portfolio-level
learnings, and exact ordered steps another agent can execute with no further
judgment. The report is always the output; actually applying the changes is an
optional downstream step (by this agent on approval, or by whoever picks up the
report).

Use `scripts/portfolio_scan.py` for the deterministic inventory and candidate
clustering. Use `references/consolidation-playbook.md` for the umbrella-class
test, the three consolidation mechanisms, package-integrity rules, and safe
execution mechanics. Use `references/report-format.md` for the exact report
structure and the required structured summary.

## Workflow

### 1. Scan the portfolio

```bash
python scripts/portfolio_scan.py <portfolio-dir>   # e.g. skills
```

It inventories every skill (name, description, category, body size, support
files, SKILL.md relative links, cross-references) and emits JSON with:

- **`candidate_clusters`** — groups of skills linked by TF-IDF term-overlap, each with its `shared_terms`, `mean_similarity`, and which members `cross_referenced` each other.
- **`top_pairs`** — the strongest pairwise similarities regardless of threshold, so weak-but-real ties still surface.
- **`narrow_named`** — skills whose name looks like a session artifact (PR number, `audit`/`salvage`/`fix`, a version/codename).
- **`skills[]`** — per skill: `support`, `skill_md_links`, `references_other_skills`, `referenced_by` (both needed for safe archiving and reference migration).

Clusters are candidates, not verdicts. Adjust `--threshold` to widen or tighten
(0.22 default; lower surfaces looser families, higher only near-duplicates).

### 2. Apply the umbrella-class test

Read `references/consolidation-playbook.md`. For each cluster with 2+ members,
ask: *what umbrella class do these all serve, and would a maintainer name that
class and write one skill for it?* If yes, pick or create the umbrella and plan
to absorb the siblings. If the members serve genuinely different classes, keep
them — apply the over-consolidation guardrail (a balanced skill that shares
vocabulary with a neighbor is not a merge candidate).

### 3. Choose a mechanism per cluster

- **Merge into an existing umbrella** — one member is already broad enough; patch it with a labeled section per sibling, archive the siblings.
- **Create a new umbrella** — none is broad enough; author a class-level SKILL.md, archive the absorbed narrow siblings.
- **Demote to support files** — a sibling has narrow-but-valuable content; move it into the umbrella's `references/`, `templates/`, or `scripts/`, then archive it.

Before any move, check **package integrity**: if a skill has support files or
its SKILL.md links to `references/`/`templates/`/`scripts/`/`assets/`, move the
*whole* package and rewrite paths — never flatten only its SKILL.md and orphan
its linked files.

### 4. Write the implementation-ready report

This is the deliverable. Produce the report exactly as `references/report-format.md`
specifies:

- **Overview** — counts and the headline (how many genuine consolidations vs. correct-as-is).
- **Learnings** — cross-cutting observations (naming, scoping, coverage gaps, cross-reference hubs, triggering-overlap risk) with evidence from the scan.
- **Changes to implement** — one block per consolidation/removal, written as concrete ordered operations (patch which SKILL.md section, `git mv` which package, migrate which exact references) so another agent runs them verbatim.
- **New / umbrella skill specs** — for each umbrella to create or rewrite: ready-to-paste name, description, category, body outline, and which siblings fill which sections/support files.
- **Skills to remove** — a table with disposition (consolidated-into / pruned), reason, and archive command.
- **Skills kept as-is** — one line each with the reason.
- **Structured summary** — the required `consolidations:` / `prunings:` YAML block recording each archived skill's forwarding target.

Write it so a downstream agent can execute top-to-bottom with no re-derivation:
exact paths, real commands, no unresolved "consider whether…". Order the changes
so each umbrella is created/patched before its siblings are archived, and
reference migrations come after the target exists. Run the self-check at the end
of `references/report-format.md` before returning it.

### 5. (Optional) execute the report

The report stands on its own; applying it is a separate, opt-in step. If the
user wants this agent to implement it, get approval for which changes to act on,
work on a branch, and execute one change block at a time per the report — moving
whole packages (package integrity), migrating every inbound reference, then
re-running the scan to confirm nothing dangles. Otherwise, hand off the report:
another agent has everything needed in the Changes and structured summary.

## When NOT to consolidate

A cluster is a place to look, not an order to merge. Keep skills separate when
each serves a distinct, balanced class — merging them yields a monolith that is
harder to trigger than the originals. `keep` is correct when a skill is already
a class-level umbrella and no merge would improve discoverability. Do not import
a fixed archive quota from any playbook; right-size to the portfolio in front of
you.

## Gotchas & Anti-Patterns

| Excuse                                                                | Reality                                                                                             |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| "The scanner clustered them, so they should merge."                   | Clusters are term-overlap candidates. Similar vocabulary ≠ same umbrella class. Apply the test by judgment. |
| "Fewer skills is better; merge everything that's close."              | Over-merging creates monolithic skills that are hard to trigger. Balanced-and-distinct beats one grab-bag. |
| "This skill is narrow, so archive it."                                | Narrow ≠ deletable. If it serves the same class as an umbrella, demote it into that umbrella's support files — don't lose the content. |
| "I'll flatten its SKILL.md into the umbrella's references/."          | If it has support files or relative links, that orphans them. Move the whole package and rewrite paths, or keep it standalone. |
| "I archived the skill; done."                                        | Not until references migrate. Update sibling pointers and evals, or you leave dangling `skills/<old>` paths. |
| "I merged three clusters, that's enough for one pass."               | Earlier merges reshape the landscape. Re-scan and look for the next umbrella before declaring done. |
| "The report says 'migrate references as needed' — good enough."      | A vague step is not executable. Name the exact files, `git mv` commands, and reference locations so another agent runs it blind. |
| "I'll just start archiving the consolidations I found."             | The report is the deliverable; execution is a separate opt-in step. Deliver the report first, then execute on approval on a branch (or hand it off). |
| "These two are distinct but adjacent, so keep both — no more thought."| Distinct *class* is a keep; distinct-but-same-class-as-an-umbrella is a demote. Name the class before deciding. |

## Reference files

- **`scripts/portfolio_scan.py`** — inventory + TF-IDF candidate clustering + cross-reference map + narrow-name flags. `--help` for usage; JSON to stdout, summary to stderr.
- **`references/consolidation-playbook.md`** — the umbrella-class test, over-consolidation guardrail, the three mechanisms, package-integrity rules, and safe archiving + reference migration in a git repo.
- **`references/report-format.md`** — the implementation-ready report structure (learnings, per-change ordered steps, umbrella specs, removals table), the self-check, and the required `consolidations`/`prunings` structured summary.
