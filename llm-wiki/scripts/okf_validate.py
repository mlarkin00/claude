#!/usr/bin/env python3
"""OKF §9 conformance checker.

Usage:
  okf_validate.py <root>             check all non-reserved .md files in bundle
  okf_validate.py --file <path>      check a single file (hook mode)

Exit 0 = conformant; exit 1 = violations found (messages on stderr).

§9 requires every non-reserved .md file to have:
  - parseable YAML frontmatter
  - a non-empty 'type' field

Reserved files (index.md, log.md) are skipped.
Hook mode: also skips files with no frontmatter block at all (may be plain notes).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from okf_lib.document import OKFDocument, OKFDocumentError

_RESERVED = {"index.md", "log.md"}


def _check_file_strict(path: Path, bundle_root: Path) -> list[str]:
    """Full-bundle mode: every non-reserved .md must have frontmatter + type."""
    if path.name in _RESERVED:
        return []
    rel = path.relative_to(bundle_root)
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{rel}: cannot read: {e}"]
    try:
        doc = OKFDocument.parse(text)
    except OKFDocumentError as e:
        return [f"{rel}: unparseable frontmatter: {e}"]
    if not doc.frontmatter:
        return [f"{rel}: missing frontmatter block"]
    type_val = doc.frontmatter.get("type")
    if not type_val or (isinstance(type_val, str) and not type_val.strip()):
        return [f"{rel}: frontmatter 'type' is missing or empty"]
    return []


def _check_file_hook(path: Path) -> list[str]:
    """Hook mode: skip files with no frontmatter (may be plain notes).
    Only enforce 'type' when frontmatter is present."""
    if path.name in _RESERVED:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []  # no frontmatter — not an OKF doc, skip
    try:
        doc = OKFDocument.parse(text)
    except OKFDocumentError as e:
        return [f"{path}: unparseable frontmatter: {e}"]
    if not doc.frontmatter:
        return []
    type_val = doc.frontmatter.get("type")
    if not type_val or (isinstance(type_val, str) and not type_val.strip()):
        return [f"{path}: frontmatter 'type' is missing or empty (required by OKF §9)"]
    return []


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_validate.py")
    p.add_argument("root", nargs="?", help="Bundle root directory (required without --file).")
    p.add_argument("--file", dest="single_file", metavar="PATH", help="Check a single file (hook mode).")
    args = p.parse_args()

    violations: list[str] = []

    if args.single_file:
        target = Path(args.single_file)
        if target.is_file():
            violations = _check_file_hook(target)
    elif args.root:
        bundle_root = Path(args.root).resolve()
        if not bundle_root.is_dir():
            print(f"okf_validate: {bundle_root}: not a directory", file=sys.stderr)
            return 1
        for md in sorted(bundle_root.rglob("*.md")):
            violations.extend(_check_file_strict(md, bundle_root))
    else:
        p.print_usage(sys.stderr)
        return 1

    if violations:
        for v in violations:
            print(f"OKF §9 violation: {v}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
