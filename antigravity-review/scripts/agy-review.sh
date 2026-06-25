#!/usr/bin/env bash
set -euo pipefail

# agy-review.sh — assemble a code-review brief from a git diff and send it to the
# Google Antigravity CLI (`agy`) in print mode. Antigravity's review is printed
# to stdout; the assembled brief can optionally be saved with --save.
#
# Exit codes: 0 ok | 2 nothing to review | 3 git/repo error | 4 agy missing | 64 bad args

PROG=$(basename "$0")

usage() {
  cat <<'EOF'
Usage: agy-review.sh [options]

Assembles a review brief from the current git changes and sends it to the
Antigravity CLI (agy --print). Prints the raw review to stdout.

Options:
  --target <spec>   What to review (default: auto). One of:
                      auto      uncommitted changes if any, else branch vs base
                      working   uncommitted changes vs HEAD (git diff HEAD)
                      staged    staged changes only (git diff --cached)
                      branch    current branch vs its base (auto-detected)
                      A..B | A...B   an explicit git range
                      <commit>  a single commit
  --base <ref>      Base ref for the 'branch' target (default: auto main/master/origin)
  --focus <text>    Reviewer focus areas, e.g. "security, error handling"
  --model <name>    agy model (exact name from `agy models`); default: "Gemini 3.5 Flash (High)"
  --allow-fs        Let agy read the repo for extra context. Adds --add-dir and
                    --dangerously-skip-permissions. Off by default (inline diff only).
  --timeout <dur>   agy --print-timeout (default 5m)
  --save <file>     Also write the assembled brief to <file>
  -h, --help        Show this help

Requires: git and agy (the Antigravity CLI; run `agy install` to set up paths).
EOF
}

TARGET=auto
BASE=""
FOCUS=""
MODEL="Gemini 3.5 Flash (High)"  # best of the agy models for coding review; override with --model
ALLOW_FS=0
TIMEOUT="5m"
SAVE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --target)  TARGET=${2:?--target needs a value}; shift 2 ;;
    --base)    BASE=${2:?--base needs a value}; shift 2 ;;
    --focus)   FOCUS=${2:?--focus needs a value}; shift 2 ;;
    --model)   MODEL=${2:?--model needs a value}; shift 2 ;;
    --timeout) TIMEOUT=${2:?--timeout needs a value}; shift 2 ;;
    --save)    SAVE=${2:?--save needs a value}; shift 2 ;;
    --allow-fs) ALLOW_FS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "$PROG: unknown argument: $1" >&2; usage >&2; exit 64 ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "$PROG: git not found on PATH" >&2; exit 3; }
if ! command -v agy >/dev/null 2>&1; then
  echo "$PROG: 'agy' (Antigravity CLI) not found on PATH. Install it, then run 'agy install'." >&2
  exit 4
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "$PROG: not inside a git repository" >&2; exit 3; }

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '(detached)')

detect_base() {
  local b
  for b in main master; do
    if git show-ref --verify --quiet "refs/heads/$b"; then echo "$b"; return; fi
  done
  if b=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null); then
    echo "${b#origin/}"; return
  fi
  echo "HEAD~1"
}

# Resolve 'auto' to a concrete target.
if [ "$TARGET" = auto ]; then
  if git diff --quiet HEAD 2>/dev/null; then
    TARGET=branch
  else
    TARGET=working
  fi
fi

STAT=""
LOG=""
case "$TARGET" in
  working)
    RANGE_DESC="uncommitted changes (working tree + index vs HEAD)"
    DIFF=$(git diff HEAD)
    STAT=$(git diff --stat HEAD)
    ;;
  staged)
    RANGE_DESC="staged changes (index vs HEAD)"
    DIFF=$(git diff --cached)
    STAT=$(git diff --cached --stat)
    ;;
  branch)
    [ -n "$BASE" ] || BASE=$(detect_base)
    RANGE_DESC="branch '$BRANCH' vs '$BASE'"
    DIFF=$(git diff "$BASE...HEAD")
    STAT=$(git diff --stat "$BASE...HEAD")
    LOG=$(git log --oneline "$BASE..HEAD")
    ;;
  *..*)
    RANGE_DESC="range $TARGET"
    DIFF=$(git diff "$TARGET")
    STAT=$(git diff --stat "$TARGET")
    LOG=$(git log --oneline "$TARGET" 2>/dev/null || true)
    ;;
  *)
    RANGE_DESC="commit $TARGET"
    DIFF=$(git show --patch "$TARGET")
    STAT=$(git show --stat --oneline "$TARGET" | head -n 1)
    LOG=$(git log --oneline -1 "$TARGET")
    ;;
esac

if [ -z "${DIFF//[$' \t\r\n']/}" ]; then
  echo "$PROG: nothing to review for target '$TARGET' ($RANGE_DESC)." >&2
  exit 2
fi

BRIEF=$(mktemp "${TMPDIR:-/tmp}/agy-review.XXXXXX.md")
trap 'rm -f "$BRIEF"' EXIT

{
  echo "You are a meticulous, senior staff-level code reviewer. Review the change below and"
  echo "give precise, actionable feedback. Be rigorous but fair, and do not invent problems."
  echo
  echo "## Change under review"
  echo "- Repository: \`$REPO_NAME\` (branch \`$BRANCH\`)"
  echo "- Scope: $RANGE_DESC"
  echo "- Reviewer focus: ${FOCUS:-general correctness, bugs, security, performance, readability, and maintainability}"
  if [ -n "$STAT" ]; then
    echo
    echo "### Files changed"
    echo '```'
    echo "$STAT"
    echo '```'
  fi
  if [ -n "$LOG" ]; then
    echo
    echo "### Commits"
    echo '```'
    echo "$LOG"
    echo '```'
  fi
  echo
  echo "## Required output format"
  echo "Respond in Markdown with exactly these sections:"
  echo "1. **Summary** — 2-3 sentences: what the change does and your overall read."
  echo "2. **Findings** — a bullet list. Tag each finding with a severity: \`[BLOCKER]\`,"
  echo "   \`[MAJOR]\`, \`[MINOR]\`, or \`[NIT]\`. For each, cite \`path:line\` from the diff,"
  echo "   state the problem, and give a concrete suggested fix. Write \"None.\" for a"
  echo "   severity that has no issues."
  echo "3. **Verdict** — one of \`APPROVE\`, \`APPROVE WITH NITS\`, or \`REQUEST CHANGES\`,"
  echo "   with a one-line rationale."
  echo
  echo "Cite exact \`file:line\` locations drawn from the diff hunks. If the change is clean,"
  echo "say so plainly instead of manufacturing issues."
  echo
  echo "## Diff"
  echo '```diff'
  echo "$DIFF"
  echo '```'
} > "$BRIEF"

if [ -n "$SAVE" ]; then
  cp "$BRIEF" "$SAVE"
  echo "$PROG: brief saved to $SAVE" >&2
fi

BRIEF_BYTES=$(wc -c < "$BRIEF")
if [ "$BRIEF_BYTES" -gt 200000 ]; then
  echo "$PROG: warning: brief is large (${BRIEF_BYTES} bytes); the diff may be truncated by the OS arg limit. Consider --allow-fs and/or a narrower --target." >&2
fi

# NOTE: agy's --print/-p/--prompt is a value-taking flag — it consumes the very next
# token as the prompt. So every other flag must come BEFORE --print, and the brief must be
# --print's immediately-following value (and therefore last). Putting --print first would
# make it swallow the next flag as the "prompt" and silently ignore the real brief.
AGY_ARGS=(--print-timeout "$TIMEOUT")
[ -n "$MODEL" ] && AGY_ARGS+=(--model "$MODEL")
if [ "$ALLOW_FS" -eq 1 ]; then
  AGY_ARGS+=(--add-dir "$REPO_ROOT" --dangerously-skip-permissions)
fi
AGY_ARGS+=(--print "$(cat "$BRIEF")")

echo "==> Antigravity review — $RANGE_DESC" >&2
echo >&2

exec agy "${AGY_ARGS[@]}"
