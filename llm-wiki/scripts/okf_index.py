#!/usr/bin/env python3
# Adapted from knowledge-catalog/okf/src/enrichment_agent/bundle/index.py +
# bundle/synthesizer.py  —  Apache-2.0 GoogleCloudPlatform/knowledge-catalog
"""OKF index regenerator — bottom-up index.md generation for a bundle.

Usage:
  okf_index.py <root> [--no-llm] [--llm]

Default: deterministic descriptions ("Contains N entries: title1, title2.").
--llm:   attempt Gemini Flash descriptions (falls back to deterministic on error).
--no-llm: same as default, explicit.

Writes one index.md per directory that contains .md files, then prints the list
of written paths to stdout, one per line.
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent))

from okf_lib.document import OKFDocument

log = logging.getLogger(__name__)

_INDEX_FILE = "index.md"
_FALLBACK_MODEL = "gemini-2.0-flash"


def _load_doc(path: Path) -> OKFDocument | None:
    try:
        return OKFDocument.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_index_text(entries: list[tuple[str, str, str, str]]) -> str:
    # entries: (type, title, relative_link, description)
    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for typ, title, link, desc in entries:
        grouped[typ or "Other"].append((title, link, desc))

    sections: list[str] = []
    for typ in sorted(grouped):
        lines = [f"# {typ}", ""]
        for title, link, desc in sorted(grouped[typ], key=lambda e: e[0].lower()):
            suffix = f" - {desc}" if desc else ""
            lines.append(f"* [{title}]({link}){suffix}")
        sections.append("\n".join(lines))
    return "\n\n".join(sections) + "\n"


def _directories_to_index(bundle_root: Path) -> list[Path]:
    dirs: set[Path] = set()
    for md in bundle_root.rglob("*.md"):
        cur = md.parent
        while cur != bundle_root.parent:
            dirs.add(cur)
            if cur == bundle_root:
                break
            cur = cur.parent
    return sorted(dirs)


def _fallback_description(children: list[tuple[str, str]]) -> str:
    titles = ", ".join(t for t, _ in children if t) or "no titled entries"
    return f"Contains {len(children)} entries: {titles}."


def _gemini_description(rel_path: str, children: list[tuple[str, str]], *, model: str) -> str:
    contents_lines = "\n".join(
        f"- {title}: {desc}" if desc else f"- {title}"
        for title, desc in children
    )
    prompt = (
        f"You are summarizing a directory in an Open Knowledge Format bundle in ONE "
        f"sentence (max ~25 words).\n\nDirectory: {rel_path}\nContents:\n{contents_lines}\n\n"
        f"Write one sentence that names what this directory collectively contains. Be "
        f"concrete and factual; do not editorialize. Output the sentence only — no "
        f"preamble, no quotes, no trailing punctuation beyond a single period."
    )
    try:
        from google import genai
        client = genai.Client()
        response = client.models.generate_content(model=model, contents=prompt)
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            return _fallback_description(children)
        return text.splitlines()[0].strip()
    except Exception as exc:
        log.warning("gemini description failed for %s: %s", rel_path, exc)
        return _fallback_description(children)


def regenerate_indexes(
    bundle_root: Path,
    *,
    use_llm: bool = False,
    model: str = _FALLBACK_MODEL,
) -> list[Path]:
    bundle_root = Path(bundle_root)
    written: list[Path] = []
    if not bundle_root.exists():
        return written

    synthesize: Callable[..., str]
    if use_llm:
        def synthesize(rel_path: str, children: list[tuple[str, str]], **kw: object) -> str:
            return _gemini_description(rel_path, children, model=model)
    else:
        def synthesize(rel_path: str, children: list[tuple[str, str]], **kw: object) -> str:
            return _fallback_description(children)

    directories = sorted(
        _directories_to_index(bundle_root),
        key=lambda p: (-len(p.relative_to(bundle_root).parts), str(p)),
    )

    dir_descriptions: dict[Path, str] = {}

    for directory in directories:
        entries: list[tuple[str, str, str, str]] = []

        for child in sorted(directory.iterdir()):
            if child.name == _INDEX_FILE:
                continue
            if child.is_file() and child.suffix == ".md":
                doc = _load_doc(child)
                if doc is None:
                    continue
                fm = doc.frontmatter
                title = str(fm.get("title") or child.stem)
                desc = str(fm.get("description") or "")
                typ = str(fm.get("type") or "")
                entries.append((typ, title, child.name, desc))
            elif child.is_dir():
                desc = dir_descriptions.get(child, "")
                entries.append(("Subdirectories", child.name, f"{child.name}/{_INDEX_FILE}", desc))

        if not entries:
            continue

        index_path = directory / _INDEX_FILE
        index_path.write_text(_build_index_text(entries), encoding="utf-8")
        written.append(index_path)

        if directory == bundle_root:
            continue

        pairs = [(title, desc) for _, title, _, desc in entries]
        if len(pairs) == 1 and pairs[0][1]:
            dir_descriptions[directory] = pairs[0][1]
        else:
            rel = str(directory.relative_to(bundle_root))
            dir_descriptions[directory] = synthesize(rel, pairs)

    return written


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_index.py")
    p.add_argument("root", help="Bundle root directory.")
    llm_group = p.add_mutually_exclusive_group()
    llm_group.add_argument("--llm", action="store_true", help="Use Gemini Flash for directory descriptions.")
    llm_group.add_argument("--no-llm", action="store_true", help="Deterministic descriptions (default).")
    p.add_argument("--model", default=_FALLBACK_MODEL, help=f"Gemini model (default: {_FALLBACK_MODEL}).")
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    bundle_root = Path(args.root).resolve()
    if not bundle_root.is_dir():
        print(f"okf_index: {bundle_root}: not a directory", file=sys.stderr)
        return 1

    written = regenerate_indexes(bundle_root, use_llm=bool(args.llm), model=args.model)
    for path in written:
        print(path)
    print(f"Wrote {len(written)} index file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
