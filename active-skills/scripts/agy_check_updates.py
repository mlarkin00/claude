#!/usr/bin/env python3
"""Stop hook (Antigravity) — run the update check at most once every 6 hours.

Replaces the `check-updates` sidecar, which never ran: the agy CLI starts no
sidecar manager, so `sidecars/` inside a plugin is inert (evidence in
`.agents/wiki/antigravity/`). Hooks are the only scheduling mechanism a plugin
can actually rely on there, and they ship inside the plugin, so install, update
and uninstall are handled by `agy plugin install`/`uninstall` for free.

Two things matter for a hook standing in for a timer:

  1. `Stop` fires at the end of every agent turn, so the work must be gated.
     The gate is a stat of one file; a turn that is not due costs nothing.
  2. The check makes a network call with a 10s timeout. Even on a due turn that
     must not be charged to the user, so the checker is spawned detached and
     this returns immediately.

The stamp is written *before* spawning, so a checker that hangs or fails costs
one attempt per interval rather than one per turn.

Always prints a JSON object and exits 0. A hook must never break the session.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
CHECKER = os.path.join(HERE, "check_updates.py")

CACHE_ROOT = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
STATE_PATH = os.path.join(CACHE_ROOT, "active-skills", "last-check")

INTERVAL_SECONDS = 6 * 60 * 60


def due(now: float) -> bool:
    """True when the last check is older than INTERVAL_SECONDS.

    A missing or corrupt stamp reads as "never checked" so the first run after
    install proceeds, and a wiped cache self-heals rather than going quiet.
    """
    try:
        with open(STATE_PATH) as f:
            last = float(f.read().strip())
    except (OSError, ValueError):
        return True
    return (now - last) >= INTERVAL_SECONDS


def stamp(now: float) -> bool:
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w") as f:
            f.write(str(now))
        return True
    except OSError:
        # Without a stamp the gate cannot hold, and spawning anyway would run
        # the check every single turn. Skipping is the safer failure.
        return False


def spawn() -> None:
    """Start the checker detached so the turn is not held up by the network."""
    with open(os.devnull, "wb") as devnull:
        subprocess.Popen(
            [sys.executable or "python3", CHECKER],
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
            cwd=HERE,
        )


def main() -> int:
    now = time.time()
    if due(now) and os.path.isfile(CHECKER) and stamp(now):
        spawn()
    return 0


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    print("{}")
    sys.exit(0)
