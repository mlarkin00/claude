"""Shared helpers for skill usage tracking.

Resolves where counts live and owns the locked read-modify-write. Imported by
the per-runtime adapters (increments) and sync-usage.py (commits and pushes).

This plugin ships no skills of its own and deliberately does not scope counting
to any particular bundle: every skill invocation is counted, whichever plugin
provided it. That is what removes the need for a skills directory to test
against or a list of skill names to maintain.

Destination is resolved from SKILL_USAGE_REPO so no user-specific path is baked
into the published plugin. With the variable unset the counts fall back to a
machine-local file and git is skipped entirely.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone

# ACTIVE_SKILLS_USAGE_REPO is honoured as a fallback so installs predating the
# split out of the active-skills plugin keep working without reconfiguration.
REPO_ENV = "SKILL_USAGE_REPO"
LEGACY_REPO_ENV = "ACTIVE_SKILLS_USAGE_REPO"
COUNTS_BASENAME = "skill-usage.json"
LOCAL_FALLBACK = os.path.expanduser("~/.claude/skill-usage.json")


def resolve_repo() -> str | None:
    """Return the configured git work tree, or None if unusable.

    A path that is not a git work tree is treated as unset rather than as an
    error: the tracker still counts locally, it just has nowhere to push.
    """
    repo = (os.environ.get(REPO_ENV, "").strip()
            or os.environ.get(LEGACY_REPO_ENV, "").strip())
    if not repo:
        return None
    repo = os.path.abspath(os.path.expanduser(repo))
    if not os.path.isdir(os.path.join(repo, ".git")):
        return None
    return repo


def counts_path() -> str:
    """Path to the counts file: <configured repo>/skill-usage.json."""
    repo = resolve_repo()
    if repo:
        return os.path.join(repo, COUNTS_BASENAME)
    return LOCAL_FALLBACK


def normalize(name: str) -> str:
    """Strip a plugin prefix so one skill keeps one counter.

    `active-skills:gcloud` and `gcloud` are the same skill reached two ways.
    Antigravity yields the bare name, so this also keeps the two runtimes
    agreeing on a single key per skill.
    """
    return name.rsplit(":", 1)[-1].strip()


def load(path: str) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def save(path: str, counts: dict) -> None:
    """Write atomically so a crash mid-write cannot truncate the counts."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".skill-usage-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(dict(sorted(counts.items())), f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


@contextlib.contextmanager
def locked(path: str):
    """Hold an exclusive lock across a read-modify-write.

    Parallel sessions increment the same file; without this, concurrent
    read-then-write pairs silently drop counts.
    """
    lock_path = os.path.join(os.path.dirname(path) or ".", ".skill-usage.lock")
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def increment(name: str) -> None:
    path = counts_path()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with locked(path):
        counts = load(path)
        entry = counts.get(name)
        prior = entry.get("count", 0) if isinstance(entry, dict) else 0
        counts[name] = {"count": int(prior) + 1, "last_used_at": now}
        save(path, counts)
