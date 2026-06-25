---
name: agy-review
description: This skill should be used when the user invokes /agy-review or /antigravity-review:agy-review, or asks to review the current changes/artifacts with Google Antigravity (e.g. "agy review my changes", "send this to antigravity for review", "get an antigravity review of my work", "have agy look at this diff"). Gathers the current diff plus session context and dispatches the agy-code-reviewer subagent to run the review through the agy CLI.
---

# /agy-review — Antigravity review of the current work

Send the current artifacts (the working changes) and the surrounding context to the
`agy-code-reviewer` subagent, which runs the review through Google Antigravity (the `agy`
CLI) and returns severity-tagged findings plus a verdict.

This skill is the gatherer and dispatcher. It does NOT call `agy` directly — the
`antigravity-review:agy-code-reviewer` subagent owns the `agy` invocation (via
`antigravity-review/scripts/agy-review.sh`). Keeping that split means one source of truth
for how the review is run.

## Usage

```
/agy-review [scope] [focus…]
```

- No scope → review the current uncommitted changes.
- `scope`: `staged`, `branch`, a commit SHA, or a git range (e.g. `main..HEAD`).
- `focus`: free-text emphasis, e.g. `security`, `error handling`, `performance`.
- Mentions of "deep" / "with context" / "read the repo" → request `--allow-fs` so
  Antigravity can read surrounding source, not just the diff.

## Steps

1. **Preflight.** Confirm the working directory is a git repo
   (`git rev-parse --is-inside-work-tree`). If not, explain that the review operates on git
   changes and stop.

2. **Determine the artifacts (scope)** from the request:
   - Default to the current uncommitted changes when no scope is given.
   - Map `staged` → staged changes, `branch` → current branch vs base, a SHA/range → that
     target.

3. **Gather the context to pass along** — this is what makes the review better than a bare
   diff dump:
   - Run `git status --short` and `git diff --stat` to summarize what is in scope. If the
     working tree is clean and no scope was given, report that and stop (nothing to review).
   - Derive a 1–2 sentence statement of the change's *intent* from the user's request and
     the current session (what is being built or fixed) — not just what the diff shows.
   - Collect any focus areas the user named.

4. **Dispatch the `agy-code-reviewer` subagent** (agent type
   `antigravity-review:agy-code-reviewer`) with a prompt that carries:
   - the scope as a target hint (`working` / `staged` / `branch` / a commit or range),
   - the focus areas,
   - the 1–2 sentence intent summary, so Antigravity reviews against what the change is
     meant to do,
   - whether to use `--allow-fs` (only when the user asked for a deep/contextual review).

   Let the subagent run the review; do not invoke `agy` or the script from this skill.

5. **Relay the result.** Present the subagent's short synthesis first, then Antigravity's
   full review verbatim under a clear heading. Attribute the substantive findings to
   Antigravity; mark any of your own additions separately.

## Notes

- One review = one subagent dispatch. To review multiple scopes, dispatch once per scope.
- If the subagent reports that `agy` is not installed, or that there are no changes for the
  scope, relay that plainly — never fabricate a review or its verdict.
- Default behavior sends the diff inline (no filesystem access). Deep mode (`--allow-fs`)
  lets Antigravity read the repo for surrounding context; mention the trade-off when using it.
