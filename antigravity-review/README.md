# antigravity-review

A Claude Code plugin that delegates **code review** to **Google Antigravity** via the `agy`
CLI. It assembles your git changes plus the surrounding context into a structured review
brief, sends it to `agy --print`, and relays Antigravity's feedback back to you — a
second-opinion review from a different model.

## What you get

| Component | Name | Purpose |
| --- | --- | --- |
| Skill | `agy-review` | Gathers the current artifacts + context and dispatches the agent. Auto-activates on "review my changes with antigravity" and invocable as `/agy-review`. |
| Agent | `agy-code-reviewer` | Resolves the diff, runs the review via `agy`, and relays Antigravity's findings with a short synthesis on top. |
| Command | `/agy-review` | Thin slash-command entry point; loads the `agy-review` skill. |
| Script | `scripts/agy-review.sh` | The workhorse: git diff → review brief → `agy --print`. Usable standalone. |

## Requirements

- [`git`](https://git-scm.com)
- The **Antigravity CLI** (`agy`) on your `PATH`. Verify with `agy models`; run `agy install`
  to configure shell paths if needed.

## Usage

In Claude Code:

```
/agy-review                     # review uncommitted changes
/agy-review staged              # review only what's staged
/agy-review branch              # review the current branch vs its base (main/master)
/agy-review security            # review uncommitted changes, focus on security
/agy-review <commit-sha>        # review a specific commit
```

Or just ask: *"review my changes with antigravity"*, *"get an agy review of this branch,
focus on error handling"*. Claude dispatches the `agy-code-reviewer` agent automatically.

## The script (standalone)

```
scripts/agy-review.sh [options]

  --target <spec>   auto (default) | working | staged | branch | A..B | <commit>
  --base <ref>      base ref for the 'branch' target (default: auto main/master/origin)
  --focus <text>    reviewer focus, e.g. "security, error handling"
  --model <name>    agy model (exact name from `agy models`); default: "Gemini 3.5 Flash (High)"
  --allow-fs        let agy read the repo for extra context (--add-dir + --dangerously-skip-permissions)
  --timeout <dur>   agy --print-timeout (default 5m)
  --save <file>     also write the assembled brief to <file>
```

Examples:

```bash
# Review uncommitted changes, security focus (uses the default Gemini 3.5 Flash (High))
scripts/agy-review.sh --focus security

# Override the model
scripts/agy-review.sh --focus security --model "Gemini 3.1 Pro (High)"

# Review a branch and let Antigravity read the repo for deeper context
scripts/agy-review.sh --target branch --allow-fs

# Just build the brief, don't send it
scripts/agy-review.sh --save /tmp/review-brief.md
```

## How it works

1. The script resolves a git diff for the requested scope and assembles a brief containing
   the change scope, changed-files stat, commit log (for branches/commits), a strict
   output-format instruction, and the full diff.
2. It calls `agy --print "<brief>"`. By default the diff is sent **inline** and `agy` gets
   **no filesystem access** — the brief is self-contained. Pass `--allow-fs` to let `agy`
   read the repository (`--add-dir <repo>` + `--dangerously-skip-permissions`) when the
   review needs surrounding-source context.
3. Antigravity returns a Markdown review: a summary, severity-tagged findings
   (`[BLOCKER]` / `[MAJOR]` / `[MINOR]` / `[NIT]`) with `file:line` citations and suggested
   fixes, and a verdict (`APPROVE` / `APPROVE WITH NITS` / `REQUEST CHANGES`).

## Notes & safety

- `--allow-fs` enables `agy`'s `--dangerously-skip-permissions`, which lets `agy` run tools
  without prompting. The review brief instructs a read-only review, but only enable this
  flag when you want the deeper context. The default (inline diff, no fs access) is safest.
- Large diffs are passed as a single shell argument and can hit the OS argument-size limit;
  the script warns when the brief is large. Narrow the scope (`--target staged`, a single
  commit) or use `--allow-fs` so `agy` reads files itself.
