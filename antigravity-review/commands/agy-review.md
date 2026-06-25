---
name: agy-review
description: Review your code changes with Google Antigravity (the agy CLI) and relay the feedback
argument-hint: [scope] [focus...]  e.g. "staged security" or "branch" or "<commit-sha>"
---

Use the **agy-code-reviewer** agent to send the current code changes to Google Antigravity (`agy`) for review and relay the feedback.

Interpret the arguments below as the review scope and/or focus, then dispatch the agent:

- No arguments → review the current uncommitted changes (the agent's default).
- A word like `staged`, `branch`, a commit SHA, or a `git` range → pass it through as the review target.
- Any remaining words (e.g. `security`, `performance`, `error handling`) → treat as the reviewer focus.
- Mentions of "deep" / "with context" / "read the repo" → ask the agent to run with `--allow-fs`.

Arguments: $ARGUMENTS

Launch the `agy-code-reviewer` agent now. When it returns, show your short synthesis followed by Antigravity's full review.
