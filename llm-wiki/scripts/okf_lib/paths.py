# Vendored from knowledge-catalog/okf/src/enrichment_agent/bundle/paths.py
# Apache-2.0 — GoogleCloudPlatform/knowledge-catalog
from __future__ import annotations

import re
from pathlib import Path

_SEGMENT_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")

# Bundle scaffolding, not concept docs. Every consumer must agree on this set:
# the validator skipping a file the index still lists is how `CLAUDE.md` ended up
# catalogued as a nameless "Other" entry in the one file that is loaded into
# every session.
RESERVED_FILENAMES = frozenset({"index.md", "log.md", "CLAUDE.md"})


def _validate_segment(seg: str) -> None:
    if not _SEGMENT_RE.fullmatch(seg):
        raise ValueError(f"Invalid concept id segment: {seg!r}")


def concept_id_to_path(bundle_root: Path, concept_id: tuple[str, ...]) -> Path:
    if not concept_id:
        raise ValueError("concept_id must have at least one segment")
    for seg in concept_id:
        _validate_segment(seg)
    *dirs, name = concept_id
    return bundle_root.joinpath(*dirs, f"{name}.md")


def path_to_concept_id(bundle_root: Path, path: Path) -> tuple[str, ...]:
    rel = path.relative_to(bundle_root).with_suffix("")
    return tuple(rel.parts)


def parse_concept_id(s: str) -> tuple[str, ...]:
    parts = tuple(p for p in s.split("/") if p)
    if not parts:
        raise ValueError(f"Empty concept id: {s!r}")
    for p in parts:
        _validate_segment(p)
    return parts
