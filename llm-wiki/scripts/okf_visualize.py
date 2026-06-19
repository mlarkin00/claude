#!/usr/bin/env python3
# Adapted from knowledge-catalog/okf/src/enrichment_agent/viewer/
# Apache-2.0 — GoogleCloudPlatform/knowledge-catalog
"""OKF bundle visualizer — generates a self-contained Cytoscape HTML graph.

Usage:
  okf_visualize.py <root> [--out <path>] [--name <label>]

Output HTML requires zero runtime deps (Cytoscape + marked loaded from CDN).
Prints JSON stats to stdout: {"concepts": N, "edges": M, "bytes": K}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from viewer.generator import generate_visualization


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_visualize.py")
    p.add_argument("root", help="Bundle root directory.")
    p.add_argument("--out", type=Path, default=None, help="Output HTML path (default: <root>/viz.html).")
    p.add_argument("--name", default=None, help="Display name for the bundle.")
    args = p.parse_args()

    bundle_root = Path(args.root).resolve()
    out_path = args.out or (bundle_root / "viz.html")

    try:
        stats = generate_visualization(bundle_root, out_path, bundle_name=args.name)
    except FileNotFoundError as e:
        print(f"okf_visualize: {e}", file=sys.stderr)
        return 1

    json.dump(stats, sys.stdout)
    print()
    print(
        f"Wrote {stats['concepts']} concept(s), {stats['edges']} edge(s), "
        f"{stats['bytes']} bytes → {out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
