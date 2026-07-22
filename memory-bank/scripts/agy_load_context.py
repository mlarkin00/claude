#!/usr/bin/env python3
"""PreInvocation hook (Antigravity) — inject long-term memories once per conversation.

Antigravity has no SessionStart event. PreInvocation is the nearest thing, but
it fires before EVERY model call and blocks the agent loop while it runs, and
load_context.py costs a Vertex AI round-trip (~3.5s measured). Running it
unguarded would put that in front of every turn and re-inject the same facts
each time.

This gates on `conversationId` from the hook payload: the first invocation of a
conversation loads and injects, every later one returns `{}` immediately. That
reproduces the once-per-session semantics load_context.py was written for.

Delegates rather than reimplements — load_context.py already emits the exact
shape PreInvocation wants (`{"injectSteps": [{"ephemeralMessage": ...}]}`), so
its stdout is passed through untouched.

Always prints a JSON object and exits 0. A hook must never break the session.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
LOADER = os.path.join(HERE, "load_context.py")
CACHE_ROOT = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
STATE_DIR = os.path.join(CACHE_ROOT, "memory-bank", "agy-conversations")

# Keep only characters legal in a filename component, so a malformed id cannot
# escape the state directory.
SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
MARKER_TTL = 7 * 24 * 60 * 60


def emit(obj: dict) -> None:
    print(json.dumps(obj))
    sys.exit(0)


def prune(state_dir: str) -> None:
    cutoff = time.time() - MARKER_TTL
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


def claim(conversation_id: str) -> bool:
    """Return True if this is the first invocation of the conversation."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except OSError:
        return False
    prune(STATE_DIR)
    marker = os.path.join(STATE_DIR, conversation_id)
    try:
        # O_EXCL makes the check-and-claim atomic, so two invocations racing at
        # the start of a conversation cannot both decide they are first.
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {}

    conversation_id = ""
    if isinstance(payload, dict):
        conversation_id = str(payload.get("conversationId") or "")

    # No usable id means no way to tell the first invocation from the tenth.
    # Skip rather than pay the round-trip on every model call — the memories are
    # a convenience, the latency would not be.
    if not SAFE_ID.fullmatch(conversation_id):
        emit({})
    if not claim(conversation_id):
        emit({})

    try:
        result = subprocess.run(
            [sys.executable, LOADER],
            input=raw,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        emit({})

    out = (result.stdout or "").strip()
    if not out:
        emit({})
    try:
        parsed = json.loads(out)
    except ValueError:
        emit({})
    emit(parsed if isinstance(parsed, dict) else {})


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        print("{}")
        sys.exit(0)
