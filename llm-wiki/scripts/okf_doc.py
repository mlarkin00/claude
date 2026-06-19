#!/usr/bin/env python3
# Adapted from knowledge-catalog/okf src/enrichment_agent/bundle/document.py +
# tools/bundle_tools.py  —  Apache-2.0 GoogleCloudPlatform/knowledge-catalog
"""OKF document I/O — standalone CLI for reading and writing concept docs.

Usage:
  okf_doc.py read  <root> <concept-id>           → JSON {frontmatter, body} | null
  okf_doc.py write <root> <concept-id>           ← JSON on stdin {frontmatter, body}
             [--web-pass]     enable augmentation guard for web-pass writes
             [--allow-shrink] bypass augmentation guard

Exits 0 on success, 1 on validation or augmentation-guard failure (error in JSON).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from okf_lib.document import OKFDocument, OKFDocumentError, REQUIRED_FRONTMATTER_KEYS
from okf_lib.paths import concept_id_to_path, parse_concept_id

_PREFERRED_KEY_ORDER = ("type", "resource", "title", "description", "tags", "timestamp")
_FIELD_NAME_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]*)`")


def _section_content_lines(body: str, heading: str) -> list[str]:
    in_section = False
    out: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            in_section = stripped == heading
            continue
        if in_section and stripped:
            out.append(line)
    return out


def _schema_field_names(body: str) -> set[str]:
    names: set[str] = set()
    for line in _section_content_lines(body, "# Schema"):
        names.update(_FIELD_NAME_RE.findall(line))
    return names


def _citation_entry_count(body: str) -> int:
    return len(_section_content_lines(body, "# Citations"))


def _reorder_frontmatter(fm: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in _PREFERRED_KEY_ORDER:
        if key in fm:
            ordered[key] = fm[key]
    for key, value in fm.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _fail(msg: str, concept_id: str | None = None) -> int:
    obj: dict[str, Any] = {"error": msg}
    if concept_id:
        obj["concept_id"] = concept_id
    json.dump(obj, sys.stdout)
    print()
    return 1


def cmd_read(args: argparse.Namespace) -> int:
    bundle_root = Path(args.root)
    cid = parse_concept_id(args.concept_id)
    path = concept_id_to_path(bundle_root, cid)
    if not path.exists():
        print("null")
        return 0
    try:
        doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
    except OKFDocumentError as e:
        return _fail(str(e))
    json.dump({"frontmatter": doc.frontmatter, "body": doc.body}, sys.stdout)
    print()
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    bundle_root = Path(args.root)
    cid = parse_concept_id(args.concept_id)
    path = concept_id_to_path(bundle_root, cid)

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        return _fail(f"Invalid JSON on stdin: {e}", args.concept_id)

    fm = dict(payload.get("frontmatter", {}))
    body = str(payload.get("body", ""))

    if not fm.get("timestamp"):
        fm["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fm = _reorder_frontmatter(fm)

    doc = OKFDocument(frontmatter=fm, body=body)
    try:
        doc.validate()
    except OKFDocumentError as e:
        return _fail(
            f"Refusing to write document with invalid frontmatter: {e}. "
            f"Required keys: {', '.join(REQUIRED_FRONTMATTER_KEYS)}.",
            args.concept_id,
        )

    # Augmentation guard: in web-pass mode, refuse writes that shrink an existing
    # BigQuery Table doc's # Schema field set or # Citations entry count.
    if args.web_pass and path.exists() and not args.allow_shrink:
        try:
            existing = OKFDocument.parse(path.read_text(encoding="utf-8"))
        except Exception:
            existing = None
        if existing is not None and existing.frontmatter.get("type") == "BigQuery Table":
            old_fields = _schema_field_names(existing.body)
            new_fields = _schema_field_names(body)
            missing = sorted(old_fields - new_fields)
            if missing:
                shown = ", ".join(f"`{m}`" for m in missing[:10])
                tail = " (and more)" if len(missing) > 10 else ""
                return _fail(
                    f"Refusing to write: the existing # Schema section lists "
                    f"{len(old_fields)} field(s) from BigQuery metadata, but your "
                    f"new # Schema is missing {len(missing)} of them: {shown}{tail}. "
                    f"Augment by extending the existing schema, not replacing it. "
                    f"Re-read with 'okf_doc.py read' then resubmit with the full field list.",
                    args.concept_id,
                )
            old_cites = _citation_entry_count(existing.body)
            new_cites = _citation_entry_count(body)
            if new_cites < old_cites:
                return _fail(
                    f"Refusing to write: the existing # Citations section had "
                    f"{old_cites} entries, but your new # Citations has only "
                    f"{new_cites}. Append your new citation rather than replacing the list.",
                    args.concept_id,
                )

    path.parent.mkdir(parents=True, exist_ok=True)
    text = doc.serialize()
    path.write_text(text, encoding="utf-8")
    json.dump({"path": str(path.relative_to(bundle_root)), "bytes": len(text.encode())}, sys.stdout)
    print()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_doc.py")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("read")
    r.add_argument("root")
    r.add_argument("concept_id")

    w = sub.add_parser("write")
    w.add_argument("root")
    w.add_argument("concept_id")
    w.add_argument("--web-pass", action="store_true")
    w.add_argument("--allow-shrink", action="store_true")

    args = p.parse_args()
    if args.command == "read":
        return cmd_read(args)
    return cmd_write(args)


if __name__ == "__main__":
    sys.exit(main())
