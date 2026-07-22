#!/usr/bin/env python3
"""OKF discovery installer — wire a bundle into a host repo's briefing files.

A bundle nobody reads is dead weight, and a prose pointer ("read the wiki before
re-deriving history") does not fire: "I am about to re-derive history" is not a
state an agent recognises about itself. The only reliable trigger is content the
harness loads whether the agent decides to or not — the briefing file.

The two runtimes load briefing files differently, verified 2026-07-22 against
Claude Code 2.1.218 and agy 1.1.5 with a codeword fixture:

  | runtime     | CLAUDE.md | AGENTS.md / GEMINI.md | `@path` expanded |
  |-------------|-----------|-----------------------|------------------|
  | Claude Code | loaded    | NOT loaded            | yes              |
  | agy         | n/a       | loaded                | NO               |

So there is no single line that works everywhere:

  * a CLAUDE.md of its own gets an `@<bundle>/index.md` import — one line, never
    goes stale, bodies stay on disk;
  * AGENTS.md / GEMINI.md (and any CLAUDE.md that is the same file as one of
    them) get the catalog **inlined**, because agy will not follow an import.
    Inlined text is a copy, so it must be refreshed — `/llm-wiki:index` does.

Usage:
  okf_discover.py <bundle_root> [--host DIR] [--check] [--sync] [--create]

  (default)  install or refresh discovery in every briefing file found
  --check    report status; exit 1 if discovery is missing or stale
  --sync     refresh blocks that already exist; never create one
  --create   if no briefing file exists, create CLAUDE.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from okf_lib.document import OKFDocument

# Order matters: CLAUDE.md is considered first so a standalone one can claim the
# cheap import mode before the shared-file check demotes it.
BRIEFING_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")

MODE_IMPORT = "import"
MODE_INLINE = "inline"

# An inlined catalog is paid for on every session of every agent in the repo.
# Past this, the bundle has outgrown a briefing file and wants subdirectory
# indexes it can drill into instead.
INLINE_WARN_BYTES = 6000

_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,5})(\s)", re.MULTILINE)


def marker_start(rel: str) -> str:
    return f"<!-- llm-wiki:discovery {rel} START -->"


def marker_end(rel: str) -> str:
    return f"<!-- llm-wiki:discovery {rel} END -->"


def find_host(bundle_root: Path) -> Path:
    """Nearest ancestor holding a .git, else the bundle's parent."""
    for candidate in [bundle_root, *bundle_root.parents]:
        if (candidate / ".git").exists():
            return candidate
    return bundle_root.parent


def briefing_files(host: Path) -> list[Path]:
    """Existing briefing files, one entry per *file*: a CLAUDE.md symlinked to
    AGENTS.md is a single document, and writing it twice would report a spurious
    refresh on the second pass."""
    seen: set[Path] = set()
    found: list[Path] = []
    for name in BRIEFING_FILES:
        path = host / name
        if not path.exists():
            continue
        try:
            key = path.resolve()
        except OSError:
            key = path
        if key in seen:
            continue
        seen.add(key)
        found.append(path)
    return found


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def choose_mode(path: Path, host: Path) -> str:
    """`import` only for a CLAUDE.md that no agy-read file shares."""
    if path.name != "CLAUDE.md":
        return MODE_INLINE
    for other in ("AGENTS.md", "GEMINI.md"):
        sibling = host / other
        if sibling.exists() and _same_file(path, sibling):
            return MODE_INLINE
    return MODE_IMPORT


def _rewrite_links(body: str, rel: str) -> str:
    """Make bundle-relative links resolve from the host repo root instead."""
    def sub(match: re.Match[str]) -> str:
        target = match.group(1)
        if target.startswith(("http://", "https://", "/", "#", "mailto:")):
            return match.group(0)
        return f"]({rel}/{target})"

    return _LINK_RE.sub(sub, body)


def _demote_headings(body: str) -> str:
    """The index owns its file, so its groups are `#`. Inlined, they land under
    the host's own `##` section and must not outrank it."""
    return _HEADING_RE.sub(lambda m: "#" * (len(m.group(1)) + 2) + m.group(2), body)


def catalog_text(bundle_root: Path, rel: str) -> str:
    """The root index body — frontmatter stripped, links rebased on the host."""
    index_path = bundle_root / "index.md"
    if not index_path.exists():
        raise FileNotFoundError(f"{index_path}: no root index.md — run okf_index.py first")
    doc = OKFDocument.parse(index_path.read_text(encoding="utf-8"))
    return _demote_headings(_rewrite_links(doc.body.strip(), rel))


def render_block(mode: str, rel: str, bundle_root: Path) -> str:
    lines = [marker_start(rel), ""]
    lines.append(f"## Knowledge bundle — `{rel}`")
    lines.append("")
    # Every line here is paid for in every session of every agent in the repo,
    # so the preamble earns exactly one.
    lines.append("Open the concept before re-deriving anything it covers.")
    lines.append("")
    if mode == MODE_IMPORT:
        lines.append(f"@{rel}/index.md")
    else:
        lines.append(catalog_text(bundle_root, rel))
    lines += ["", marker_end(rel), ""]
    return "\n".join(lines)


def apply_block(text: str, block: str, rel: str) -> str:
    """Replace an existing block, else append one. Idempotent."""
    start, end = marker_start(rel), marker_end(rel)
    if start in text and end in text:
        head = text[: text.index(start)]
        tail = text[text.index(end) + len(end):]
        return head + block.rstrip("\n") + tail
    separator = "" if text.endswith("\n\n") or not text else ("\n" if text.endswith("\n") else "\n\n")
    return text + separator + block


def has_block(text: str, rel: str) -> bool:
    return marker_start(rel) in text and marker_end(rel) in text


def relative_bundle_path(bundle_root: Path, host: Path) -> str:
    try:
        return bundle_root.resolve().relative_to(host.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"{bundle_root} is not inside host repo {host}") from exc


def plan(bundle_root: Path, host: Path) -> list[tuple[Path, str]]:
    files = briefing_files(host)
    # agy discovers AGENTS.md *and* GEMINI.md, so inlining into both would put the
    # catalog in its context twice, every turn. AGENTS.md is the cross-tool name.
    names = {p.name for p in files}
    if {"AGENTS.md", "GEMINI.md"} <= names:
        files = [p for p in files if p.name != "GEMINI.md"]
    return [(path, choose_mode(path, host)) for path in files]


def main() -> int:
    p = argparse.ArgumentParser(prog="okf_discover.py")
    p.add_argument("root", help="Bundle root directory.")
    p.add_argument("--host", help="Repo root holding the briefing files (default: nearest .git).")
    p.add_argument("--check", action="store_true", help="Report status only; exit 1 if missing or stale.")
    p.add_argument("--sync", action="store_true", help="Refresh existing blocks only; never create one.")
    p.add_argument("--create", action="store_true", help="Create CLAUDE.md if no briefing file exists.")
    args = p.parse_args()

    bundle_root = Path(args.root).resolve()
    if not bundle_root.is_dir():
        print(f"okf_discover: {bundle_root}: not a directory", file=sys.stderr)
        return 1

    host = Path(args.host).resolve() if args.host else find_host(bundle_root)
    try:
        rel = relative_bundle_path(bundle_root, host)
    except ValueError as exc:
        print(f"okf_discover: {exc}", file=sys.stderr)
        return 1

    targets = plan(bundle_root, host)
    if not targets:
        if args.create and not args.check and not args.sync:
            targets = [(host / "CLAUDE.md", MODE_IMPORT)]
            (host / "CLAUDE.md").write_text(f"# {host.name}\n", encoding="utf-8")
        else:
            print(f"okf_discover: no briefing file in {host} "
                  f"({', '.join(BRIEFING_FILES)}) — nothing reads {rel} on any runtime.",
                  file=sys.stderr)
            return 1

    stale = False
    for path, mode in targets:
        text = path.read_text(encoding="utf-8")
        try:
            block = render_block(mode, rel, bundle_root)
        except FileNotFoundError as exc:
            print(f"okf_discover: {exc}", file=sys.stderr)
            return 1
        present = has_block(text, rel)
        updated = apply_block(text, block, rel)

        if args.check:
            if not present:
                print(f"{path.name}: MISSING ({mode})")
                stale = True
            elif updated != text:
                print(f"{path.name}: STALE ({mode}) — re-run okf_discover.py --sync")
                stale = True
            else:
                print(f"{path.name}: ok ({mode})")
            continue

        if args.sync and not present:
            print(f"{path.name}: skipped (no block; --sync will not create one)")
            continue

        if updated == text:
            print(f"{path.name}: unchanged ({mode})")
            continue

        path.write_text(updated, encoding="utf-8")
        print(f"{path.name}: {'refreshed' if present else 'installed'} ({mode})")

        if mode == MODE_INLINE and len(block.encode("utf-8")) > INLINE_WARN_BYTES:
            print(f"okf_discover: warning: inlined catalog is "
                  f"{len(block.encode('utf-8'))} bytes in {path.name}, paid on every "
                  f"session — consider splitting the bundle into subdirectories so the "
                  f"root index stays a catalog.", file=sys.stderr)

    if not any(mode == MODE_IMPORT or path.name == "CLAUDE.md" for path, mode in targets):
        print("okf_discover: warning: no CLAUDE.md in "
              f"{host} — Claude Code does not read AGENTS.md, so it will not see "
              f"{rel}. Add a CLAUDE.md (a symlink to AGENTS.md is enough).",
              file=sys.stderr)

    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
