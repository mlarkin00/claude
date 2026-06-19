#!/usr/bin/env python3
"""OKF bundle search — index-first lookup with BM25-style fallback.

Usage:
  okf_search.py <root> <query> [--k N]

Prints JSON array of hits, ranked by relevance, to stdout.
Each hit: {id, title, type, description, score}
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from okf_lib.document import OKFDocument


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _tf(tokens: list[str], term: str) -> float:
    count = tokens.count(term)
    return count / len(tokens) if tokens else 0.0


def _bm25_score(query_terms: list[str], title: str, desc: str, body: str) -> float:
    """Simple BM25-inspired score: title matches worth 3x, desc 2x, body 1x."""
    title_tokens = _tokenize(title)
    desc_tokens = _tokenize(desc)
    body_tokens = _tokenize(body)
    score = 0.0
    for term in query_terms:
        score += _tf(title_tokens, term) * 3.0
        score += _tf(desc_tokens, term) * 2.0
        score += _tf(body_tokens, term) * 1.0
        # Exact substring match in title is high value
        if term in title.lower():
            score += 1.0
    return score


def search(bundle_root: Path, query: str, k: int = 10) -> list[dict]:
    query_terms = _tokenize(query)
    if not query_terms:
        return []

    results = []
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name == "index.md":
            continue
        try:
            doc = OKFDocument.parse(md_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        fm = doc.frontmatter
        if not fm.get("type"):
            continue

        concept_id = "/".join(md_path.relative_to(bundle_root).with_suffix("").parts)
        title = str(fm.get("title") or concept_id)
        desc = str(fm.get("description") or "")
        body = doc.body or ""

        score = _bm25_score(query_terms, title, desc, body)
        if score > 0:
            results.append({
                "id": concept_id,
                "title": title,
                "type": fm.get("type"),
                "description": desc,
                "score": round(score, 4),
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_search.py")
    p.add_argument("root", help="Bundle root directory.")
    p.add_argument("query", help="Search query.")
    p.add_argument("--k", type=int, default=10, help="Max results (default: 10).")
    args = p.parse_args()

    bundle_root = Path(args.root).resolve()
    if not bundle_root.is_dir():
        print(f"okf_search: {bundle_root}: not a directory", file=sys.stderr)
        return 1

    hits = search(bundle_root, args.query, args.k)
    json.dump(hits, sys.stdout, indent=2)
    print()
    print(f"Found {len(hits)} result(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
