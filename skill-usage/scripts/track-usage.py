#!/usr/bin/env python3
"""PostToolUse(Skill) hook (Claude Code) — increment a skill's counter.

Reads a Claude Code hook payload on stdin. Every skill invocation is counted,
whichever plugin provided it; this plugin ships no skills of its own.

Always exits 0. A tracker must never block a session.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import usage_lib  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Skill":
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0

    name = usage_lib.normalize(str(tool_input.get("skill") or ""))
    if not name:
        return 0

    usage_lib.increment(name)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        sys.exit(0)
