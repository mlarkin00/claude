#!/usr/bin/env python3
"""Print skill usage totals, summed across every machine's shard.

Counts are stored one file per machine (`skill-usage/<machine-id>.json`) so
that machines never write the same file and can never conflict. The tradeoff is
that no single file answers "how often have I used this skill", which is what
this prints.

    report-usage.py              # totals, most used first
    report-usage.py --by-machine # per-machine breakdown
    report-usage.py --json       # machine-readable totals
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import usage_lib  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--by-machine", action="store_true",
                        help="show each machine's contribution")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit totals as JSON")
    args = parser.parse_args()

    repo = usage_lib.resolve_repo()
    paths = usage_lib.shard_paths(repo)
    if not paths:
        print("No counts yet." if repo else
              "No counts yet (SKILL_USAGE_REPO is unset; counting locally).")
        return 0

    totals = usage_lib.totals(repo)
    if args.as_json:
        json.dump(totals, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if not totals:
        print("No counts yet.")
        return 0

    width = max(len(name) for name in totals)
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1]["count"], kv[0]))
    grand = sum(entry["count"] for entry in totals.values())
    print("%-*s  %5s  %s" % (width, "SKILL", "USES", "LAST USED"))
    for name, entry in ranked:
        print("%-*s  %5d  %s" % (width, name, entry["count"], entry["last_used_at"]))
    print("\n%d skills, %d uses, %d shard(s)" % (len(totals), grand, len(paths)))

    if args.by_machine:
        print()
        for path in paths:
            label = os.path.basename(path)
            if os.path.basename(os.path.dirname(path)) != usage_lib.COUNTS_DIRNAME:
                label += "  (pre-sharding)"
            try:
                counts = usage_lib.load(path)
            except usage_lib.CorruptCounts as exc:
                print("%s: UNREADABLE — %s" % (label, exc))
                continue
            uses = sum(int(v.get("count", 0) or 0)
                       for v in counts.values() if isinstance(v, dict))
            print("%s: %d skills, %d uses" % (label, len(counts), uses))
    return 0


if __name__ == "__main__":
    sys.exit(main())
