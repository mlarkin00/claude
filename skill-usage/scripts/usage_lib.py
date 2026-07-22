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

**Counts are sharded per machine.** Each machine writes only
`skill-usage/<machine-id>.json` and never reads or rewrites another machine's
shard, so two machines can never produce a conflicting edit to the same file.
Totals are a read-time sum across shards.

A single shared counts file cannot be made safe here. Counts are absolute
values rather than deltas, so git has no correct way to merge two machines'
versions: a content conflict forces you to discard one side's numbers. Worse,
the conflict markers make the file unparseable, and an increment landing on an
unparseable file used to reset it to a single entry — every prior count gone.
Sharding removes the shared write target entirely, which also makes any rebase
of a sync commit trivially conflict-free.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import socket
import tempfile
import uuid
from datetime import datetime, timezone

# ACTIVE_SKILLS_USAGE_REPO is honoured as a fallback so installs predating the
# split out of the active-skills plugin keep working without reconfiguration.
REPO_ENV = "SKILL_USAGE_REPO"
LEGACY_REPO_ENV = "ACTIVE_SKILLS_USAGE_REPO"
COUNTS_DIRNAME = "skill-usage"
# The pre-sharding layout: one shared file at the repo root. Still summed into
# totals so history from before the split is not silently dropped, but never
# written to again.
LEGACY_COUNTS_BASENAME = "skill-usage.json"
LOCAL_FALLBACK = os.path.expanduser("~/.claude/skill-usage.json")

CONFIG_ROOT = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
CACHE_ROOT = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
MACHINE_ID_PATH = os.path.join(CONFIG_ROOT, "skill-usage", "machine-id")


class CorruptCounts(Exception):
    """A counts file exists but could not be parsed.

    Raised rather than swallowed: treating an unreadable file as empty is what
    turns one bad read into permanent data loss on the next write.
    """


def _hostname_slug() -> str:
    """Filename-safe hostname, or a constant if the host has no usable name."""
    raw = ""
    try:
        raw = socket.gethostname() or ""
    except OSError:
        raw = ""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-").lower()[:32]
    return slug or "machine"


def machine_id() -> str:
    """Stable shard name for this machine.

    Hostname alone is readable but not safe: two hosts can share one (cloud VMs
    and containers routinely do), and colliding shard names would reintroduce
    exactly the shared-file conflict this design exists to remove. So the id is
    `<hostname>-<random>`, generated once and persisted under the config dir.

    If the id cannot be persisted, fall back to the bare hostname rather than a
    fresh random value — a deterministic name keeps writing to one shard, while
    re-rolling would litter the repo with a new file on every single increment.
    """
    try:
        with open(MACHINE_ID_PATH) as f:
            cached = f.read().strip()
        if cached:
            return cached
    except OSError:
        pass

    ident = "%s-%s" % (_hostname_slug(), uuid.uuid4().hex[:6])
    try:
        os.makedirs(os.path.dirname(MACHINE_ID_PATH), exist_ok=True)
        with open(MACHINE_ID_PATH, "w") as f:
            f.write(ident + "\n")
    except OSError:
        return _hostname_slug()
    return ident


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


def counts_relpath() -> str:
    """This machine's shard, relative to the repo root.

    Returned separately from the absolute path because git needs the relative
    form to scope a commit to this shard alone.
    """
    return os.path.join(COUNTS_DIRNAME, machine_id() + ".json")


def counts_path() -> str:
    """Absolute path to the counts file this machine writes.

    With no repo configured there is nothing to share and nothing to sync, so
    the unsharded machine-local fallback is kept as-is.
    """
    repo = resolve_repo()
    if repo:
        return os.path.join(repo, counts_relpath())
    return LOCAL_FALLBACK


def shard_paths(repo: str | None = None) -> list[str]:
    """Every counts file contributing to the totals, newest layout first.

    Includes the legacy root file when present so pre-sharding history still
    counts. Order is only for stable output; the sum is order-independent.
    """
    repo = repo if repo is not None else resolve_repo()
    if not repo:
        return [LOCAL_FALLBACK] if os.path.isfile(LOCAL_FALLBACK) else []
    paths = []
    shard_dir = os.path.join(repo, COUNTS_DIRNAME)
    try:
        for name in sorted(os.listdir(shard_dir)):
            if name.endswith(".json"):
                paths.append(os.path.join(shard_dir, name))
    except OSError:
        pass
    legacy = os.path.join(repo, LEGACY_COUNTS_BASENAME)
    if os.path.isfile(legacy):
        paths.append(legacy)
    return paths


def totals(repo: str | None = None) -> dict:
    """Sum every shard into one {skill: {count, last_used_at}} mapping.

    A shard that will not parse is skipped rather than aborting the whole
    report — one damaged machine should not hide the other three.
    """
    merged: dict = {}
    for path in shard_paths(repo):
        try:
            counts = load(path)
        except CorruptCounts:
            continue
        for name, entry in counts.items():
            if not isinstance(entry, dict):
                continue
            total = merged.setdefault(name, {"count": 0, "last_used_at": ""})
            total["count"] += int(entry.get("count", 0) or 0)
            seen = str(entry.get("last_used_at") or "")
            if seen > total["last_used_at"]:
                total["last_used_at"] = seen
    return merged


def normalize(name: str) -> str:
    """Strip a plugin prefix so one skill keeps one counter.

    `active-skills:gcloud` and `gcloud` are the same skill reached two ways.
    Antigravity yields the bare name, so this also keeps the two runtimes
    agreeing on a single key per skill.
    """
    return name.rsplit(":", 1)[-1].strip()


def load(path: str) -> dict:
    """Read a counts file. Missing means empty; unreadable means stop.

    The distinction is the whole point. Returning {} for a file that exists but
    will not parse means the next save writes a fresh file containing only the
    skill just used, destroying every count in it. That is not hypothetical: it
    is what happened when a git merge left conflict markers in the shared counts
    file. Sharding should keep a conflict from ever reaching this file, but the
    read stays strict so a truncated or hand-edited file fails loudly instead.
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (ValueError, OSError) as exc:
        raise CorruptCounts("%s: %s" % (path, exc)) from exc
    if not isinstance(data, dict):
        raise CorruptCounts("%s: expected a JSON object" % path)
    return data


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


def lock_path_for(path: str) -> str:
    """Where the lock guarding `path` lives.

    Deliberately outside the repo. The lock only coordinates parallel sessions
    on this machine, so it is machine-local state, and putting it beside the
    counts left an untracked file in the user's checkout that they had to know
    to gitignore. Keyed by the shard path so two configured repos cannot share
    one lock.
    """
    key = re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-")[-100:]
    return os.path.join(CACHE_ROOT, "skill-usage", "locks", key + ".lock")


@contextlib.contextmanager
def locked(path: str):
    """Hold an exclusive lock across a read-modify-write.

    Parallel sessions on this machine increment the same shard; without this,
    concurrent read-then-write pairs silently drop counts. Cross-machine safety
    comes from sharding instead — no lock could provide it.
    """
    lock_path = lock_path_for(path)
    try:
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        handle = open(lock_path, "w")
    except OSError:
        # An unusable cache dir must not stop counting; the worst case is a
        # lost increment under exact concurrency, not a crashed session.
        yield
        return
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield
    finally:
        handle.close()


def increment(name: str) -> None:
    """Add one to this machine's shard.

    Only ever touches `skill-usage/<this machine>.json`, so a concurrent write
    from another machine is impossible by construction — the lock below is
    guarding parallel sessions on *this* machine only.

    Raises CorruptCounts if the shard is unreadable. Callers are hooks that
    already exit 0 on any exception, so the effect is a skipped count and a
    line on stderr rather than an overwritten file.
    """
    path = counts_path()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with locked(path):
        counts = load(path)
        entry = counts.get(name)
        prior = entry.get("count", 0) if isinstance(entry, dict) else 0
        counts[name] = {"count": int(prior) + 1, "last_used_at": now}
        save(path, counts)
