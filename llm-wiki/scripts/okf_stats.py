#!/usr/bin/env python3
"""OKF bundle statistics — counts, orphans, broken links, citation coverage.

Usage:
  okf_stats.py <root>

Prints JSON to stdout:
{
  "total_concepts": N,
  "by_type": {"TypeA": N, ...},
  "total_links": N,
  "orphans": ["id1", ...],           # concepts with no inbound links
  "broken_links": [{"from": ..., "to": ...}, ...],
  "citation_coverage": "N/M"         # docs with # Citations / total docs
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from okf_lib.document import OKFDocument

_LINK_RE = re.compile(r"\]\(([^)\s]+\.md)(?:#[^\)]*)?\)")


def compute_stats(bundle_root: Path) -> dict:
    concepts: list[str] = []
    by_type: dict[str, int] = {}
    all_links: list[tuple[str, str]] = []
    cited_count = 0

    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name == "index.md":
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
            doc = OKFDocument.parse(text)
        except Exception:
            continue
        fm = doc.frontmatter
        if not fm.get("type"):
            continue

        concept_id = "/".join(md_path.relative_to(bundle_root).with_suffix("").parts)
        concepts.append(concept_id)

        type_val = str(fm.get("type"))
        by_type[type_val] = by_type.get(type_val, 0) + 1

        if "# Citations" in (doc.body or ""):
            cited_count += 1

        # Resolve file-relative links to concept IDs
        body = doc.body or ""
        for m in _LINK_RE.finditer(body):
            href = m.group(1)
            if "://" in href or href.startswith("/"):
                continue  # external or absolute link
            try:
                target_path = (md_path.parent / href).resolve()
                target_id = "/".join(
                    target_path.relative_to(bundle_root.resolve()).with_suffix("").parts
                )
                all_links.append((concept_id, target_id))
            except ValueError:
                pass

    concept_set = set(concepts)
    inbound: set[str] = set(t for _, t in all_links)
    orphans = [c for c in concepts if c not in inbound]
    broken = [{"from": s, "to": t} for s, t in all_links if t not in concept_set]
    total = len(concepts)

    return {
        "total_concepts": total,
        "by_type": dict(sorted(by_type.items())),
        "total_links": len(all_links),
        "orphans": sorted(orphans),
        "broken_links": broken,
        "citation_coverage": f"{cited_count}/{total}",
    }


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_stats.py")
    p.add_argument("root", help="Bundle root directory.")
    args = p.parse_args()

    bundle_root = Path(args.root).resolve()
    if not bundle_root.is_dir():
        print(f"okf_stats: {bundle_root}: not a directory", file=sys.stderr)
        return 1

    stats = compute_stats(bundle_root)
    json.dump(stats, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
