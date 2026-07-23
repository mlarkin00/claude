#!/usr/bin/env python3
"""Guard the AGENTS.md / CLAUDE.md twins against silent drift.

Claude Code never reads AGENTS.md and agy never expands `@` imports, so each
runtime gets its own briefing file. They must stay identical EXCEPT in two
places, both deliberate:

  1. The twin-pointer sentence, which names the other file and states which
     discovery mode is used "here" versus "there".
  2. The `<!-- llm-wiki:discovery ... -->` block, which is the inlined catalog
     in AGENTS.md and an `@` import in CLAUDE.md.

Everything else diverging means one runtime is running on stale rules — the
same shape of silent failure the discovery bug itself had, since neither
runtime reads the other's file.

Exits 0 when the twins agree, 1 on drift or a structural problem.
"""

import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The whole discovery block, markers included. Deliberately divergent content.
DISCOVERY_RE = re.compile(
    r"<!-- llm-wiki:discovery .*? START -->.*?<!-- llm-wiki:discovery .*? END -->",
    re.DOTALL,
)

# The twin-pointer sentence: a bold segment naming the twin, through to the end
# of the sentence. `[^*\n]*` keeps the match from crossing into a neighbouring
# bold run, so an edit to the rest of the line is still compared.
TWIN_RE = re.compile(
    r"\*\*[^*\n]*hand-propagated twin[^*\n]*\*\*[^\n]*?made there too\."
)

DISCOVERY_TOKEN = "<<DISCOVERY-BLOCK>>"
TWIN_TOKEN = "<<TWIN-POINTER-SENTENCE>>"


def normalize(path, text, errors):
    """Replace the two deliberately divergent regions with fixed tokens."""
    for name, pattern, token in (
        ("discovery block", DISCOVERY_RE, DISCOVERY_TOKEN),
        ("twin-pointer sentence", TWIN_RE, TWIN_TOKEN),
    ):
        found = pattern.findall(text)
        if len(found) != 1:
            errors.append(
                f"{path.name}: expected exactly 1 {name}, found {len(found)}. "
                f"Without it the twins cannot be compared — restore it."
            )
        text = pattern.sub(token, text)
    return text


def check_discovery_mode(path, text, want_import, errors):
    """Each file must carry the discovery mode its runtime can actually use."""
    match = DISCOVERY_RE.search(text)
    if not match:
        return
    block = match.group(0)
    has_import = re.search(r"^@\S", block, re.MULTILINE) is not None
    if want_import and not has_import:
        errors.append(
            f"{path.name}: discovery block has no `@`-import line. Claude Code "
            f"expands imports; this file must import the catalog, not inline it."
        )
    if not want_import and has_import:
        errors.append(
            f"{path.name}: discovery block contains an `@`-import line. agy never "
            f"expands imports; this file must inline the catalog."
        )
    if not want_import and "](" not in block:
        errors.append(
            f"{path.name}: discovery block inlines no links — the catalog looks "
            f"empty. Regenerate it."
        )


def main():
    agents_path = REPO_ROOT / "AGENTS.md"
    claude_path = REPO_ROOT / "CLAUDE.md"

    errors = []
    for path in (agents_path, claude_path):
        if not path.is_file():
            errors.append(f"{path} is missing.")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    agents_text = agents_path.read_text()
    claude_text = claude_path.read_text()

    check_discovery_mode(agents_path, agents_text, want_import=False, errors=errors)
    check_discovery_mode(claude_path, claude_text, want_import=True, errors=errors)

    agents_norm = normalize(agents_path, agents_text, errors)
    claude_norm = normalize(claude_path, claude_text, errors)

    if agents_norm != claude_norm:
        diff = difflib.unified_diff(
            agents_norm.splitlines(keepends=True),
            claude_norm.splitlines(keepends=True),
            fromfile="AGENTS.md (normalized)",
            tofile="CLAUDE.md (normalized)",
        )
        errors.append(
            "AGENTS.md and CLAUDE.md have drifted outside the two allowed "
            "regions. Every convention edit must be made in BOTH files:\n\n"
            + "".join(diff)
        )

    if errors:
        print("\n\n".join(errors), file=sys.stderr)
        return 1

    print("OK AGENTS.md and CLAUDE.md agree outside the two allowed regions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
