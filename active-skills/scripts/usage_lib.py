"""Shared helpers for active-skills usage tracking.

Resolves where counts live and owns the locked read-modify-write. Imported by
track-usage.py (increments) and sync-usage.py (commits and pushes).

Destination is resolved from ACTIVE_SKILLS_USAGE_REPO so no user-specific path is
baked into the published plugin. With the variable unset the counts fall back to a
machine-local file and git is skipped entirely.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone

REPO_ENV = "ACTIVE_SKILLS_USAGE_REPO"
COUNTS_BASENAME = "skill-usage.json"
LOCAL_FALLBACK = os.path.expanduser("~/.claude/active-skills-usage.json")


def resolve_repo() -> str | None:
    """Return the configured git work tree, or None if unusable.

    A path that is not a git work tree is treated as unset rather than as an
    error: the tracker still counts locally, it just has nowhere to push.
    """
    repo = os.environ.get(REPO_ENV, "").strip()
    if not repo:
        return None
    repo = os.path.abspath(os.path.expanduser(repo))
    if not os.path.isdir(os.path.join(repo, ".git")):
        return None
    return repo


def counts_path() -> str:
    """Path to the counts file.

    Deliberately the repo *root*, never active-skills/. That directory is
    exact-mirrored into the published plugin, so a counts file inside it would
    bump the plugin version and cut a release on every skill invocation.
    """
    repo = resolve_repo()
    if repo:
        return os.path.join(repo, COUNTS_BASENAME)
    return LOCAL_FALLBACK


def plugin_skills_dir() -> str | None:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not root:
        return None
    skills = os.path.join(root, "skills")
    return skills if os.path.isdir(skills) else None


def normalize(name: str) -> str:
    """Strip a plugin prefix so one skill keeps one counter.

    `active-skills:gcloud` and `gcloud` are the same skill reached two ways.
    """
    return name.rsplit(":", 1)[-1].strip()


def is_plugin_skill(name: str) -> bool:
    """True when `name` ships in this plugin.

    Membership is a directory test against the plugin's own skills/, which keeps
    the tracker scoped to active-skills without maintaining a second list that
    could drift from the mirror.
    """
    skills = plugin_skills_dir()
    if not skills or not name or "/" in name or name.startswith("."):
        return False
    return os.path.isdir(os.path.join(skills, name))


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
