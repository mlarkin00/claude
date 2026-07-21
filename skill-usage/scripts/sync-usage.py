#!/usr/bin/env python3
"""SessionEnd hook — commit and push the session's usage counts.

Increments accumulate in the counts file during the session; this pushes them
once at the end rather than per invocation, keeping history to one commit per
session instead of one per skill call.

No-ops when ACTIVE_SKILLS_USAGE_REPO is unset, when nothing changed, or when the
repo is mid-merge/rebase. Always exits 0.
"""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import usage_lib  # noqa: E402

TIMEOUT = 15


def git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def mid_operation(repo: str) -> bool:
    """True during a merge/rebase/cherry-pick.

    Committing into someone else's half-finished operation would entangle the
    counts with conflict resolution, so the sync waits for a later session.
    """
    result = git(repo, "rev-parse", "--git-dir")
    if result.returncode != 0:
        return True
    git_dir = os.path.join(repo, result.stdout.strip())
    markers = ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply")
    return any(os.path.exists(os.path.join(git_dir, m)) for m in markers)


def main() -> int:
    repo = usage_lib.resolve_repo()
    if not repo or mid_operation(repo):
        return 0

    counts = usage_lib.COUNTS_BASENAME
    if not os.path.exists(os.path.join(repo, counts)):
        return 0

    status = git(repo, "status", "--porcelain", "--", counts)
    if status.returncode != 0 or not status.stdout.strip():
        return 0

    # --only commits this path alone, leaving any unrelated staged work in the
    # repo untouched.
    commit = git(
        repo, "commit", "--only", "--no-verify",
        "-m", "chore(active-skills): update skill usage counts",
        "--", counts,
    )
    if commit.returncode != 0:
        return 0

    git(repo, "push")  # a failed push just leaves the commit for next session
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        sys.exit(0)
