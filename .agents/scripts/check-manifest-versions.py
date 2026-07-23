#!/usr/bin/env python3
"""Verify every marketplace entry resolves on disk and its THREE versions agree.

For each plugin listed in `.claude-plugin/marketplace.json`, the marketplace
entry, the Claude manifest (`<plugin>/.claude-plugin/plugin.json`), and the
optional Antigravity manifest (`<plugin>/plugin.json`) must all carry the same
version — one directory serves both runtimes, so one version describes it. The
Antigravity manifest is optional; a plugin without one is fine.

Also flags any directory on disk that has a `.claude-plugin/` but is not listed
in the marketplace — an unlisted plugin nothing releases.

Paths resolve relative to the repo root, so this runs from any cwd. Prints one
`OK`/`BAD` line per plugin; exits 0 when everything agrees, 1 otherwise.
"""

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NO_AGY = "(no agy manifest)"


def main():
    marketplace = json.load(open(REPO_ROOT / ".claude-plugin" / "marketplace.json"))
    ok_all = True

    for p in marketplace["plugins"]:
        s = p["source"].lstrip("./")
        cf = REPO_ROOT / s / ".claude-plugin" / "plugin.json"
        af = REPO_ROOT / s / "plugin.json"
        cv = json.load(open(cf))["version"] if cf.is_file() else None
        av = json.load(open(af))["version"] if af.is_file() else NO_AGY
        ok = cv == p["version"] and av in (cv, NO_AGY)
        ok_all = ok_all and ok
        print(("OK " if ok else "BAD"), p["name"],
              "mkt=" + p["version"], "claude=" + str(cv), "agy=" + av)

    on_disk = {x for x in os.listdir(REPO_ROOT)
               if (REPO_ROOT / x / ".claude-plugin").is_dir()}
    unlisted = on_disk - {p["name"] for p in marketplace["plugins"]}
    print("unlisted on disk:", unlisted or "none")

    return 0 if ok_all and not unlisted else 1


if __name__ == "__main__":
    sys.exit(main())
