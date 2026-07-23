#!/usr/bin/env python3
"""PreInvocation hook (Antigravity) — keep long-term memories in context.

Antigravity has no SessionStart event. PreInvocation is the nearest thing, but
it differs from Claude's SessionStart in two ways that pull in opposite
directions:

  1. It fires before EVERY model call and blocks the agent loop, and
     load_context.py costs a Vertex AI round-trip (~3.5s measured). Calling it
     unguarded puts that in front of every turn.
  2. Its `ephemeralMessage` is transient — it lives only for the invocation it
     was injected into. Inject once and the memories are gone by the next turn.
     (Verified: a second turn in the same conversation answered "NO MEMORIES
     INJECTED".)

So this neither refetches nor skips: it fetches once per conversation, caches
the rendered payload, and replays it on every later invocation. Memories stay
in context for the whole conversation at roughly 30ms per turn after the first.
The cache is refreshed after REFRESH_SECONDS so a long-running conversation
still picks up memories added part-way through.

Delegates the actual load — `load_context.py --format agy` emits the exact shape
PreInvocation wants (`{"injectSteps": [{"ephemeralMessage": ...}]}`), so its
stdout is cached and replayed untouched. The flag is not optional: the loader
defaults to Claude Code's `hookSpecificOutput` shape, which Antigravity ignores
in silence.

Always prints a JSON object and exits 0. A hook must never break the session.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.realpath(__file__))
LOADER = os.path.join(HERE, "load_context.py")
LOADER_ARGS = ["--format", "agy"]
CACHE_ROOT = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
STATE_DIR = os.path.join(CACHE_ROOT, "memory-bank", "agy-conversations")

# Keep only characters legal in a filename component, so a malformed id cannot
# escape the state directory.
SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
REFRESH_SECONDS = 30 * 60
ENTRY_TTL = 7 * 24 * 60 * 60


def emit(text: str) -> None:
    print(text)
    sys.exit(0)


def prune(state_dir: str) -> None:
    cutoff = time.time() - ENTRY_TTL
    try:
        for name in os.listdir(state_dir):
            path = os.path.join(state_dir, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                continue
    except OSError:
        pass


def read_cache(path: str) -> str | None:
    try:
        if time.time() - os.path.getmtime(path) > REFRESH_SECONDS:
            return None
        with open(path, encoding="utf-8") as f:
            cached = f.read().strip()
    except OSError:
        return None
    return cached or None


def write_cache(path: str, payload: str) -> None:
    # Atomic, so an invocation reading the cache while another refreshes it
    # cannot see a half-written payload.
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except (OSError, NameError):
            pass


def load(raw: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, LOADER, *LOADER_ARGS],
            input=raw,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return "{}"

    out = (result.stdout or "").strip()
    if not out:
        return "{}"
    try:
        parsed = json.loads(out)
    except ValueError:
        return "{}"
    return json.dumps(parsed) if isinstance(parsed, dict) else "{}"


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {}

    conversation_id = ""
    if isinstance(payload, dict):
        conversation_id = str(payload.get("conversationId") or "")

    # With no usable id there is nothing to key a cache on. Load anyway — a
    # missing id must not cost the user their memories — and accept the
    # round-trip.
    if not SAFE_ID.fullmatch(conversation_id):
        emit(load(raw))

    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except OSError:
        emit(load(raw))
    prune(STATE_DIR)

    cache_path = os.path.join(STATE_DIR, conversation_id)
    cached = read_cache(cache_path)
    if cached is not None:
        emit(cached)

    fresh = load(raw)
    write_cache(cache_path, fresh)
    emit(fresh)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print("{}")
        sys.exit(0)
