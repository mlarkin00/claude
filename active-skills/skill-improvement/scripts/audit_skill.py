#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Mechanical pre-pass auditor for an Agent Skill directory.

Runs the deterministic, objectively-checkable parts of a skill review so the
agent can spend its judgment on the parts that actually need judgment
(triggering quality, non-obviousness, scoping). Everything here is a check a
human would otherwise re-run by hand every single review.

Emits a machine-readable JSON report to STDOUT and a short human summary to
STDERR. Non-interactive. Exit code is 0 unless --strict is passed, in which
case any error-severity finding exits 1 (useful as a CI gate).

Usage:
    python audit_skill.py <path-to-skill-dir>
    python audit_skill.py <path-to-skill-dir> --strict
    python audit_skill.py --help

The JSON shape:
    {
      "skill": "<name>",
      "path": "<abs path>",
      "summary": {"error": N, "warning": N, "info": N},
      "findings": [
        {"id","severity","dimension","location","message","fix"}
      ]
    }

Severity meaning:
    error   - violates the spec / will break discovery or paths / leaks secrets
    warning - departs from best practice; almost always worth fixing
    info    - a nudge or something for the agent to verify with judgment
"""
import argparse
import json
import os
import re
import sys

VALID_CATEGORIES = {
    "library-reference", "product-verification", "data-analysis",
    "team-automation", "code-scaffolding", "code-quality",
    "cicd-deployment", "runbook", "infra-ops",
}

# Secret patterns. Kept conservative to limit false positives; the agent still
# reviews matches by hand. Placeholders like <...>, {{...}}, YOUR_, xxxx are skipped.
SECRET_PATTERNS = [
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("openai-style-key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("generic-assigned-secret", re.compile(
        r"(?i)(?:api[_-]?key|secret|passwd|password|token|client[_-]?secret)"
        r"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
]
PLACEHOLDER = re.compile(r"(?i)(your_|xxxx|<[^>]+>|\{\{.*\}\}|example|changeme|placeholder|dummy|redacted|\.\.\.)")

# Instructions that smell adversarial (prompt-injection / covert behavior).
ADVERSARIAL_PATTERNS = [
    re.compile(r"(?i)ignore (?:all |any )?(?:previous|prior|above) instructions"),
    re.compile(r"(?i)do not (?:tell|inform|notify|mention (?:this )?to) the user"),
    re.compile(r"(?i)without (?:telling|informing|asking) the user"),
    re.compile(r"(?i)\bexfiltrat"),
    re.compile(r"(?i)hide (?:this|your actions|the output) from"),
    re.compile(r"(?i)disregard (?:the )?(?:safety|security) (?:rules|guidelines)"),
]

NETWORK_HINT = re.compile(r"(?i)\b(curl|wget|https?://|requests\.(get|post|put|delete)|urllib|fetch\()")


def add(findings, severity, dimension, location, message, fix):
    findings.append({
        "id": f"{dimension}-{len(findings) + 1}",
        "severity": severity,
        "dimension": dimension,
        "location": location,
        "message": message,
        "fix": fix,
    })


def parse_frontmatter(text):
    """Return (frontmatter_str, body_str, ok). Frontmatter is between the first
    two '---' fences on their own lines at the top of the file."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text, False
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:]), True
    return "", text, False


def extract_field(frontmatter, field):
    """Pull a top-level (column-0) frontmatter field's value, handling single
    line, quoted, and folded/indented multi-line forms. Returns collapsed str."""
    lines = frontmatter.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.match(rf"^{re.escape(field)}\s*:", line):
            start = idx
            break
    if start is None:
        return None
    first = lines[start].split(":", 1)[1].strip()
    collected = []
    if first and first not in (">", "|", ">-", "|-", "|+", ">+"):
        collected.append(first)
    # Gather indented continuation lines (folded blocks / wrapped values).
    for line in lines[start + 1:]:
        if re.match(r"^[A-Za-z0-9_-]+\s*:", line):  # next top-level key
            break
        if line.strip() == "":
            continue
        collected.append(line.strip())
    value = " ".join(collected).strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    return value


def nested_value(frontmatter, key):
    """Find an indented key anywhere in the frontmatter (e.g. metadata.category)."""
    m = re.search(rf"^\s+{re.escape(key)}\s*:\s*(.+)$", frontmatter, re.MULTILINE)
    if not m:
        return None
    v = m.group(1).strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    return v


def iter_text_files(skill_dir):
    """Yield (relpath, abspath) for text-ish files in the skill."""
    text_ext = {".md", ".py", ".sh", ".js", ".ts", ".json", ".txt", ".yaml", ".yml", ".toml"}
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in text_ext:
                ap = os.path.join(root, f)
                yield os.path.relpath(ap, skill_dir), ap


def check_frontmatter(findings, skill_dir, skill_md_text):
    name_dir = os.path.basename(os.path.abspath(skill_dir))
    fm, body, ok = parse_frontmatter(skill_md_text)
    if not ok:
        add(findings, "error", "structure", "SKILL.md",
            "SKILL.md has no valid YAML frontmatter (missing '---' fences at the top).",
            "Add a frontmatter block delimited by '---' lines with 'name' and 'description'.")
        return body

    name = extract_field(fm, "name")
    desc = extract_field(fm, "description")
    category = nested_value(fm, "category")

    if not name:
        add(findings, "error", "structure", "SKILL.md frontmatter",
            "Missing required 'name' field.", "Add 'name: <kebab-case-name>'.")
    else:
        if name != name_dir:
            add(findings, "error", "triggering", "SKILL.md frontmatter",
                f"name '{name}' does not match directory '{name_dir}'; mismatched names cause silent discovery failures.",
                f"Set name to '{name_dir}' (or rename the directory to match the name).")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            add(findings, "error", "triggering", "SKILL.md frontmatter",
                f"name '{name}' is not kebab-case (lowercase alphanumerics and hyphens only).",
                "Rename using only lowercase letters, digits, and hyphens.")
        if len(name) > 64:
            add(findings, "warning", "triggering", "SKILL.md frontmatter",
                f"name is {len(name)} chars; spec limit is 64.", "Shorten the name.")

    if not desc:
        add(findings, "error", "triggering", "SKILL.md frontmatter",
            "Missing required 'description' field — this is the primary trigger signal.",
            "Add a description covering WHAT the skill does and WHEN to use it, with concrete trigger phrases.")
    else:
        if len(desc) > 1024:
            add(findings, "warning", "triggering", "SKILL.md frontmatter",
                f"description is {len(desc)} chars; spec limit is 1024.", "Tighten it.")
        if len(desc) < 40:
            add(findings, "warning", "triggering", "SKILL.md frontmatter",
                f"description is only {len(desc)} chars — likely too thin to trigger reliably.",
                "Expand with what-it-does + when-to-use + specific trigger phrases.")
        low = desc.lower()
        if not (low.startswith("use when") or low.startswith("use this skill")):
            add(findings, "info", "triggering", "SKILL.md frontmatter",
                "description does not start with 'Use when...' / 'Use this skill when...' (repo convention for strong triggering).",
                "Reframe to lead with the triggering condition.")
        if not re.search(r"(?i)\b(use when|when the user|use this skill when|whenever)\b", desc):
            add(findings, "warning", "triggering", "SKILL.md frontmatter",
                "description states what the skill does but no explicit WHEN-to-use condition.",
                "Add concrete triggering contexts/phrases the user would actually say.")

    if category is None:
        add(findings, "warning", "structure", "SKILL.md frontmatter",
            "No 'category' under metadata (repo convention requires one of the 9 categories).",
            "Add 'metadata:\\n  category: <one-of-9>'.")
    elif category not in VALID_CATEGORIES:
        add(findings, "warning", "structure", "SKILL.md frontmatter",
            f"category '{category}' is not one of the 9 allowed categories.",
            f"Use one of: {', '.join(sorted(VALID_CATEGORIES))}.")
    return body


def check_body(findings, body):
    body_lines = body.count("\n") + 1
    if body_lines > 500:
        add(findings, "warning", "progressive-disclosure", "SKILL.md body",
            f"SKILL.md body is ~{body_lines} lines (>500). Large bodies load fully on every trigger and dilute attention.",
            "Move detailed patterns/edge-cases into references/ and keep the body to core workflow + pointers.")
    if not re.search(r"(?im)^#{1,4}\s*(gotcha|anti-?pattern|common mistake|pitfall|failure mode)", body):
        add(findings, "warning", "content", "SKILL.md body",
            "No Gotchas / Anti-Patterns / Common Mistakes section. These map the excuses agents use to skip steps to the counter-rule.",
            "Add a 'Gotchas & Anti-Patterns' section (a rationalization|reality table works well).")


def collect_path_refs(text):
    """Return candidate in-skill relative path references from markdown/backticks."""
    refs = set()
    for m in re.finditer(r"\]\(([^)\s]+)\)", text):  # markdown links
        refs.add(m.group(1))
    for m in re.finditer(r"`([^`]+)`", text):  # inline code
        tok = m.group(1).strip()
        if re.match(r"^(?:\./)?(scripts|references|assets|templates)/\S+", tok):
            refs.add(tok.split()[0])
    # Bare mentions, but not when the token is a tail of a longer path
    # (e.g. '<repo>/active-skills/other/scripts/x.py' references another skill).
    for m in re.finditer(r"(?<![\w`(/>=\-])(?:\./)?(?:scripts|references|assets|templates)/[\w./\-]+", text):
        refs.add(m.group(0))
    return refs


def check_paths(findings, skill_dir, skill_md_text):
    for ref in sorted(collect_path_refs(skill_md_text)):
        # Drop trailing prose punctuation so "references/." / "scripts/foo.py)." from
        # sentences don't read as real paths.
        clean = ref.split("#", 1)[0].strip().rstrip(".,;:)]}`\"'")
        if not clean or clean.startswith(("http://", "https://", "mailto:")):
            continue
        if "\\" in clean:
            add(findings, "warning", "path-integrity", "SKILL.md",
                f"path '{clean}' uses backslashes; use forward slashes for cross-platform correctness.",
                "Replace '\\\\' with '/'.")
        if clean.startswith("/"):
            add(findings, "warning", "path-integrity", "SKILL.md",
                f"path '{clean}' is absolute; skills must use relative paths.",
                "Make it relative to the skill root (e.g. 'scripts/foo.py').")
            continue
        target = os.path.normpath(os.path.join(skill_dir, clean.lstrip("./")))
        last = os.path.basename(clean.rstrip("/"))
        # Only treat as a file reference when the final segment has a real
        # extension (foo.md); bare 'references/' or 'references/templates' in
        # prose is a directory mention, not a broken file link.
        looks_like_file = bool(re.match(r".+\.[A-Za-z0-9]+$", last))
        is_dir_ref = clean.endswith("/")
        if looks_like_file and not os.path.isfile(target):
            add(findings, "error", "path-integrity", "SKILL.md",
                f"referenced file '{clean}' does not exist.",
                "Fix the path or create the file. Every referenced path must resolve.")
        elif is_dir_ref and not os.path.isdir(target):
            add(findings, "warning", "path-integrity", "SKILL.md",
                f"referenced directory '{clean}' does not exist.", "Fix the path or create the directory.")


def check_nesting(findings, skill_dir):
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}]
        rel = os.path.relpath(root, skill_dir)
        depth = 0 if rel == "." else len(rel.split(os.sep))
        if depth >= 2 and files:
            add(findings, "info", "progressive-disclosure", rel,
                f"resources nested {depth} levels deep; the spec favors a flat layout one level from SKILL.md.",
                "Flatten to scripts/ references/ assets/ unless the depth genuinely aids retrieval.")


def check_scripts(findings, skill_dir):
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return
    for f in sorted(os.listdir(scripts_dir)):
        ap = os.path.join(scripts_dir, f)
        if not os.path.isfile(ap):
            continue
        try:
            with open(ap, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue
        ext = os.path.splitext(f)[1].lower()
        loc = f"scripts/{f}"
        if ext == ".sh":
            if not re.search(r"set\s+-e", content):
                add(findings, "warning", "scripts", loc,
                    "Bash script lacks 'set -e'; without fail-fast the agent may proceed on corrupt/partial data.",
                    "Add 'set -euo pipefail' near the top.")
            if re.search(r"(?m)^\s*read\s+(-p|-r|[A-Za-z_])", content):
                add(findings, "warning", "scripts", loc,
                    "Bash script appears to prompt interactively ('read'); agents cannot answer prompts and will hang.",
                    "Accept all input via CLI args/flags; remove interactive 'read'.")
            if not re.search(r"(?i)(--help|-h\b|usage[:)])", content):
                add(findings, "info", "scripts", loc,
                    "No --help / usage text detected.", "Add a --help flag with an example invocation.")
        elif ext == ".py":
            if re.search(r"(?<![\w.])input\s*\(", content):
                add(findings, "warning", "scripts", loc,
                    "Python script calls input(); agents cannot answer interactive prompts.",
                    "Take input via argparse instead of input().")
            if "argparse" not in content and not re.search(r"(?i)(--help|usage[:)])", content):
                add(findings, "info", "scripts", loc,
                    "No argparse/--help detected.", "Add argparse with a --help description and usage example.")


def check_security(findings, skill_dir):
    for rel, ap in iter_text_files(skill_dir):
        try:
            with open(ap, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        is_script = rel.startswith("scripts" + os.sep) or rel.startswith("scripts/")
        for lineno, line in enumerate(lines, 1):
            for label, pat in SECRET_PATTERNS:
                m = pat.search(line)
                if m and not PLACEHOLDER.search(m.group(0)):
                    add(findings, "error", "security", f"{rel}:{lineno}",
                        f"possible hardcoded secret ({label}): '{m.group(0)[:40]}...'.",
                        "Remove the credential; read it from an environment variable at runtime.")
            for pat in ADVERSARIAL_PATTERNS:
                if pat.search(line):
                    add(findings, "warning", "security", f"{rel}:{lineno}",
                        "instruction looks adversarial (covert action / injection / safety bypass).",
                        "Remove it; skills must not hide actions from the user or bypass safety.")
            if is_script and NETWORK_HINT.search(line):
                add(findings, "info", "security", f"{rel}:{lineno}",
                    "outbound network call in a script — verify the destination is expected and allow-listed.",
                    "Confirm the domain is trusted; document why the call is needed.")


def check_reference_tocs(findings, skill_dir):
    refs_dir = os.path.join(skill_dir, "references")
    if not os.path.isdir(refs_dir):
        return
    for f in sorted(os.listdir(refs_dir)):
        if not f.endswith(".md"):
            continue
        ap = os.path.join(refs_dir, f)
        try:
            with open(ap, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        n = text.count("\n") + 1
        if n > 100:
            head = "\n".join(text.splitlines()[:30]).lower()
            if "table of contents" not in head and "contents" not in head:
                add(findings, "warning", "progressive-disclosure", f"references/{f}",
                    f"reference file is ~{n} lines (>100) but has no table of contents near the top.",
                    "Add a TOC so the agent can jump to the relevant section without reading the whole file.")


def main():
    parser = argparse.ArgumentParser(
        description="Mechanical best-practices auditor for an Agent Skill directory.",
        epilog="Example: python audit_skill.py active-skills/gcloud --strict")
    parser.add_argument("skill_dir", help="Path to the skill directory (the one containing SKILL.md).")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any error-severity finding is present (CI gate).")
    args = parser.parse_args()

    skill_dir = os.path.abspath(args.skill_dir)
    findings = []

    if not os.path.isdir(skill_dir):
        print(f"Error: not a directory: {skill_dir}", file=sys.stderr)
        sys.exit(2)

    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        add(findings, "error", "structure", skill_dir,
            "No SKILL.md found — a skill must have SKILL.md at its root.",
            "Create SKILL.md with frontmatter (name, description) and a Markdown body.")
        report = {"skill": os.path.basename(skill_dir), "path": skill_dir,
                  "summary": {"error": 1, "warning": 0, "info": 0}, "findings": findings}
        print(json.dumps(report, indent=2))
        print("FAIL: no SKILL.md", file=sys.stderr)
        sys.exit(1 if args.strict else 0)

    with open(skill_md, encoding="utf-8", errors="replace") as fh:
        skill_md_text = fh.read()

    body = check_frontmatter(findings, skill_dir, skill_md_text)
    check_body(findings, body)
    check_paths(findings, skill_dir, skill_md_text)
    check_nesting(findings, skill_dir)
    check_scripts(findings, skill_dir)
    check_security(findings, skill_dir)
    check_reference_tocs(findings, skill_dir)

    summary = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1

    report = {
        "skill": os.path.basename(skill_dir),
        "path": skill_dir,
        "summary": summary,
        "findings": findings,
    }
    print(json.dumps(report, indent=2))
    print(f"Audit: {summary['error']} error(s), {summary['warning']} warning(s), "
          f"{summary['info']} info. Mechanical checks only — now apply the rubric.",
          file=sys.stderr)

    if args.strict and summary["error"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
