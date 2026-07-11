# Consolidation Playbook

How to turn a candidate cluster into a consolidation decision, and how to
execute it safely in a git-backed skills repo. The scan script surfaces
candidate clusters; this playbook is the judgment and mechanics on top.

## Table of Contents

1. [The umbrella-class test](#the-umbrella-class-test)
2. [The over-consolidation guardrail](#the-over-consolidation-guardrail)
3. [Three ways to consolidate](#three-ways-to-consolidate)
4. [Package integrity — not optional](#package-integrity--not-optional)
5. [Narrow-name signal](#narrow-name-signal)
6. [Executing a consolidation in this repo](#executing-a-consolidation-in-this-repo)
7. [Reference migration](#reference-migration)
8. [Iterate](#iterate)

---

## The umbrella-class test

For each cluster with 2+ members, do **not** ask "are these overlapping?" — ask:

> **What is the umbrella class these skills all serve? Would a maintainer name
> that class and write one skill for it?**

If yes, pick (or create) the umbrella and absorb the siblings into it. If no —
if each member serves a genuinely different class of task — leave them alone.

The term-overlap that put skills in a cluster is a *hint*, not the answer. Two
skills can share vocabulary and still serve different classes (e.g. a git-sync
skill and a worktree skill both talk about "branches" but do different jobs). The
umbrella-class question cuts through vocabulary overlap to intent.

---

## The over-consolidation guardrail

Consolidation has a cost that pure "reduce the count" thinking ignores: **a
skill that tries to cover too much is hard to trigger precisely, and its
irrelevant context confuses the agent.** Merging distinct skills into a
monolith trades a discoverability win for a discoverability loss.

Judge every proposed merge against the scoping ladder:

- **Atomic** — one narrow task. Fine, but many atomic skills competing to load is noise.
- **Balanced** — one complete, nameable workflow. This is the target.
- **Monolithic** — a whole domain. Hard to activate; recommend *splitting*, not merging into.

Consolidate when the result is still **balanced** — a coherent class a
maintainer would name and reach for. Do **not** consolidate when the result
would be monolithic. A 4-member "dev workflow" cluster (planning, TDD,
debugging, worktrees) is usually four balanced skills that share vocabulary, not
one umbrella — merging them produces a monolith no one can trigger cleanly.

`keep` is the right call when a skill is already a balanced, class-level skill
and no proposed merge would improve discoverability. "This is narrow but
distinct from its siblings" is *not* automatically a keep — if it is narrow and
serves the same class as an umbrella, it belongs *under* the umbrella as a
subsection or support file. But "distinct class" **is** a keep.

The example that inspired this skill targeted a bloated portfolio full of
session artifacts and demanded aggressive umbrella-ification. Do not import a
fixed archive quota. Right-size to the portfolio in front of you: a clean,
well-scoped set may yield one or two genuine merges and many correct keeps.

---

## Three ways to consolidate

Pick the right mechanism per cluster.

### a. Merge into an existing umbrella

One member is already broad enough to be the umbrella (e.g. `git-sync` for a
git-sync + refresh-sync cluster). Patch it: add a short, clearly labeled section
for each sibling's unique insight, then archive the siblings. Prefer this when a
natural umbrella already exists — it preserves an established trigger surface.

### b. Create a new umbrella SKILL.md

No existing member is broad enough. Author a new class-level skill whose
SKILL.md covers the shared workflow with short labeled subsections, then archive
the now-absorbed narrow siblings. Use only when a and c don't fit — a brand-new
skill has no triggering track record.

### c. Demote to references / templates / scripts

A sibling has narrow-but-valuable content (a session-specific recipe, a knowledge
bank, a probe script) that shouldn't be its own skill but shouldn't be lost.
Move it into the umbrella's support directory:

- `references/<topic>.md` — session-specific detail or condensed knowledge (quoted research, API excerpts, provider quirks, reproduction recipes)
- `templates/<name>.<ext>` — starter files meant to be copied and modified
- `scripts/<name>.<ext>` — statically re-runnable actions (verifiers, fixture generators, probes)

Then archive the old sibling.

---

## Package integrity — not optional

Before demoting or archiving a skill, inspect it as a **complete directory
package**, not just its SKILL.md. A skill root may include `references/`,
`templates/`, `scripts/`, and `assets/`. A reference markdown file living inside
another skill is **not** its own skill root.

The scan reports each skill's `support` files and its `skill_md_links`. If the
source skill has support files **or** its SKILL.md contains relative links
(`references/...`, `templates/...`, `scripts/...`, `assets/...`), do **not**
flatten only its SKILL.md into `<umbrella>/references/<old>.md` — that orphans
every linked file. Choose one safe path instead:

1. **Keep it** as a standalone skill, OR
2. **Fully merge** it — re-home every needed support file into the umbrella's
   canonical `references/`/`templates/`/`scripts/`/`assets/`, **and rewrite the
   moved instructions to the new paths**, OR
3. **Archive the entire original package unchanged** (whole directory).

Never leave archived or demoted instructions pointing at files left behind under
the old skill's directory.

---

## Narrow-name signal

The scan flags skills whose **name** looks like a session artifact — contains a
PR number, a version/codename number, or a token like `audit` / `diagnosis` /
`salvage` / `triage` / `fix` / `hotfix` / `wip`. These almost always belong as a
subsection or support file under a class-level umbrella rather than standing
alone. A flagged name is a prompt to check, not an automatic archive — confirm
the umbrella exists (or should) before moving it.

---

## Executing a consolidation in this repo

Skills live in `active-skills/<name>/` and are discovered by that path (see
`EVAL.txtpb`, which references skills as `active-skills/<name>`). "Archiving"
means removing a skill from `active-skills/` so it is no longer discovered,
reversibly.

**Snapshot / safety:** work on a branch, and commit before and after each
cluster so every consolidation is an isolated, revertible change.

**Archive with history preserved** — move the whole package out of
`active-skills/` rather than deleting it:

```bash
mkdir -p <repo>/.archive/skills
git mv active-skills/<old-skill> <repo>/.archive/skills/<old-skill>
```

`.archive/` at the repo root sits outside `active-skills/`, so archived skills
stop being discovered while their full package stays in the tree and in git
history. (Plain `git rm` is the alternative if the maintainer prefers
history-only recovery — but `git mv` keeps the package inspectable for
reference-migration verification.)

**Merge/patch/demote edits** use ordinary file edits and `git mv` for re-homing
support files. Always move the *whole* file set a skill's instructions depend
on, then rewrite paths in the destination.

---

## Reference migration

A consolidated or archived skill is only safely gone once nothing still points
at it. The scan's `referenced_by` field lists skills whose SKILL.md mentions the
target; also search the whole repo:

```bash
grep -rn "<old-skill>" <repo> --include='*.md' --include='*.txtpb' --include='*.json' \
  | grep -v "/.archive/"
```

For every hit, repoint it at the umbrella (the `absorbed_into` target) or remove
it if truly pruned:

- **`EVAL.txtpb`** — update any `expected_skills: "active-skills/<old>"` to the umbrella, or drop the case if the behavior moved.
- **Sibling SKILL.md bodies** — rewrite "see the `<old>` skill" pointers to the umbrella.
- **The umbrella's own evals** — fold in the archived skill's meaningful eval prompts.

This is the `absorbed_into` bookkeeping from the source methodology: record where
each archived skill went so downstream references migrate deterministically
instead of being guessed at later.

---

## Iterate

After one consolidation round, re-run the scan on the remaining set and look for
the next umbrella opportunity — earlier merges change the landscape and can
reveal or dissolve later clusters. Stop when the remaining clusters all fail the
umbrella-class test (genuinely distinct classes), not after a fixed number of
merges.
