#!/usr/bin/env python3
"""PostToolUse(Skill) hook — increment the counter for an active-skills skill.

Reads a Claude Code hook payload on stdin. Counts only skills that ship in this
plugin; invocations of skills from other plugins are ignored.

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
    if not usage_lib.is_plugin_skill(name):
        return 0

    usage_lib.increment(name)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        sys.exit(0)
