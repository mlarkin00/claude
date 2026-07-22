#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Inventory a skill portfolio and surface candidate consolidation clusters.

Consolidation judgment (does a set of skills share an *umbrella class*?) is the
agent's job. This script does the mechanical work that would otherwise be
re-done by hand every review across dozens of skills: it inventories every
skill, extracts a term signature, computes TF-IDF cosine similarity between
every pair, groups the high-similarity pairs into candidate clusters, maps
cross-references between skills, records each skill's support-file package (for
package-integrity-safe archiving), and flags narrow/session-artifact names.

The clusters are *candidates*, not verdicts. Two skills scoring high on term
overlap may still be legitimately distinct; two skills that belong under one
umbrella may score low if they use different vocabulary. Read the output as a
map of where to look, then apply the umbrella-class test by judgment.

Emits JSON to STDOUT and a short summary to STDERR. Non-interactive.

Usage:
    python portfolio_scan.py <portfolio-dir>            # e.g. skills/
    python portfolio_scan.py <portfolio-dir> --threshold 0.20
    python portfolio_scan.py --help
"""
import argparse
import json
import math
import os
import re
import sys

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "to", "of", "in", "on", "for",
    "with", "when", "use", "used", "using", "this", "that", "these", "those",
    "should", "must", "will", "can", "it", "its", "is", "are", "be", "as", "at",
    "by", "from", "into", "so", "not", "no", "do", "does", "user", "users",
    "asks", "ask", "want", "wants", "need", "needs", "make", "sure", "even",
    "any", "all", "your", "you", "they", "them", "their", "run", "runs", "e.g",
    "eg", "ie", "etc", "via", "each", "how", "what", "which", "whenever",
    "skill", "skills", "agent", "agents", "claude", "active", "md", "https",
    "http", "com", "org", "www", "like", "also", "before", "after", "than",
    "then", "up", "out", "off", "over", "new", "one", "two", "three", "get",
    "set", "add", "adds", "help", "helps", "work", "works", "working",
}
TOKEN_RE = re.compile(r"[a-z][a-z0-9]{2,}")

# NAME shapes that almost always signal a narrow, session-scoped artifact that
# belongs under an umbrella rather than standing alone as its own skill.
NARROW_NAME_TOKENS = {
    "audit", "diagnosis", "diagnose", "salvage", "triage", "fix", "fixes",
    "hotfix", "patch", "wip", "tmp", "temp", "draft", "old", "backup", "copy",
    "repro", "workaround", "bug", "issue", "ticket", "incident",
}
NARROW_NAME_RE = re.compile(r"(?:^|-)(?:v?\d+|\d{2,})(?:-|$)")  # PR#/version-ish digits


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def fm_field(fm, field):
    lines = fm.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.match(rf"^{re.escape(field)}\s*:", line):
            start = idx
            break
    if start is None:
        return None
    first = lines[start].split(":", 1)[1].strip()
    parts = []
    if first and first not in (">", "|", ">-", "|-"):
        parts.append(first)
    for line in lines[start + 1:]:
        if re.match(r"^[A-Za-z0-9_-]+\s*:", line):
            break
        if line.strip():
            parts.append(line.strip())
    val = " ".join(parts).strip()
    if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
        val = val[1:-1]
    return val


def fm_nested(fm, key):
    m = re.search(rf"^\s+{re.escape(key)}\s*:\s*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip().strip("\"'") if m else None


def tokenize(text):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def headings(body):
    return " ".join(re.findall(r"(?m)^#{1,4}\s+(.*)$", body))


def md_links(body):
    refs = set()
    for m in re.finditer(r"\]\(([^)\s]+)\)", body):
        refs.add(m.group(1))
    for m in re.finditer(r"`([^`]+)`", body):
        tok = m.group(1).strip().split()[0] if m.group(1).strip() else ""
        if re.match(r"^(?:\./)?(references|templates|scripts|assets)/\S+", tok):
            refs.add(tok)
    return sorted(r for r in refs if re.match(r"^(?:\./)?(references|templates|scripts|assets)/", r))


def support_files(skill_dir):
    out = {}
    for sub in ("scripts", "references", "assets", "templates"):
        d = os.path.join(skill_dir, sub)
        if os.path.isdir(d):
            files = []
            for root, dirs, fs in os.walk(d):
                dirs[:] = [x for x in dirs if x != "__pycache__"]
                for f in fs:
                    if not f.endswith(".pyc"):
                        files.append(os.path.relpath(os.path.join(root, f), skill_dir))
            if files:
                out[sub] = sorted(files)
    return out


def discover_skills(portfolio_dir):
    skills = []
    for entry in sorted(os.listdir(portfolio_dir)):
        sd = os.path.join(portfolio_dir, entry)
        smd = os.path.join(sd, "SKILL.md")
        if os.path.isdir(sd) and os.path.isfile(smd):
            with open(smd, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            fm, body = parse_frontmatter(text)
            name = fm_field(fm, "name") or entry
            desc = fm_field(fm, "description") or ""
            support = support_files(sd)
            skills.append({
                "name": entry,
                "fm_name": name,
                "description": desc,
                "category": fm_nested(fm, "category"),
                "body_words": len(body.split()),
                "support": support,
                "support_file_count": sum(len(v) for v in support.values()),
                "skill_md_links": md_links(body),
                "_body": body,
                "_terms": tokenize(entry.replace("-", " ") + " " + name.replace("-", " ")
                                    + " " + desc + " " + headings(body)),
            })
    return skills


def narrow_name(name):
    reasons = []
    toks = set(name.split("-"))
    hit = toks & NARROW_NAME_TOKENS
    if hit:
        reasons.append(f"session-artifact token(s): {', '.join(sorted(hit))}")
    if NARROW_NAME_RE.search(name):
        reasons.append("contains a number/version (PR#, version, or codename)")
    return reasons


def tfidf_vectors(skills):
    n = len(skills)
    df = {}
    for s in skills:
        for t in set(s["_terms"]):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(n / (1 + c)) + 1.0 for t, c in df.items()}
    vectors = []
    for s in skills:
        tf = {}
        for t in s["_terms"]:
            tf[t] = tf.get(t, 0) + 1
        vec = {t: (1 + math.log(c)) * idf[t] for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: v / norm for t, v in vec.items()})
    return vectors, idf


def cosine(a, b):
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return sum(v * big.get(t, 0.0) for t, v in small.items())


def shared_terms(skills, members, idf, k=6):
    counts, weight = {}, {}
    for i in members:
        for t in set(skills[i]["_terms"]):
            counts[t] = counts.get(t, 0) + 1
            weight[t] = idf.get(t, 1.0)
    common = [(t, weight[t]) for t, c in counts.items() if c >= 2]
    common.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in common[:k]]


def cross_references(skills):
    names = {s["name"]: i for i, s in enumerate(skills)}
    refs = {i: set() for i in range(len(skills))}
    for i, s in enumerate(skills):
        body_lower = s["_body"].lower()
        for other, j in names.items():
            if j == i or len(other) <= 3:
                continue
            if re.search(rf"(?<![\w-]){re.escape(other)}(?![\w-])", body_lower):
                refs[i].add(other)
    return refs


def main():
    ap = argparse.ArgumentParser(
        description="Inventory a skill portfolio and surface candidate consolidation clusters.",
        epilog="Example: python portfolio_scan.py skills --threshold 0.18")
    ap.add_argument("portfolio_dir", help="Directory containing skill subdirectories.")
    ap.add_argument("--threshold", type=float, default=0.22,
                    help="Cosine-similarity edge threshold for clustering (default 0.22). "
                         "Lower to surface looser families; raise for only near-duplicates.")
    ap.add_argument("--top-pairs", type=int, default=20,
                    help="How many top-similarity pairs to report regardless of threshold.")
    args = ap.parse_args()

    portfolio_dir = os.path.abspath(args.portfolio_dir)
    if not os.path.isdir(portfolio_dir):
        print(f"Error: not a directory: {portfolio_dir}", file=sys.stderr)
        sys.exit(2)

    skills = discover_skills(portfolio_dir)
    if not skills:
        print(json.dumps({"portfolio_dir": portfolio_dir, "skill_count": 0,
                          "skills": [], "candidate_clusters": [], "top_pairs": []}, indent=2))
        print("No skills found (no immediate subdirectory with a SKILL.md).", file=sys.stderr)
        sys.exit(0)

    vectors, idf = tfidf_vectors(skills)
    xrefs = cross_references(skills)

    # Pairwise similarity.
    pairs = []
    n = len(skills)
    for i in range(n):
        for j in range(i + 1, n):
            sim = cosine(vectors[i], vectors[j])
            if sim > 0:
                pairs.append((sim, i, j))
    pairs.sort(reverse=True)

    # Union-find clustering over edges >= threshold.
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    edges = [(sim, i, j) for sim, i, j in pairs if sim >= args.threshold]
    for sim, i, j in edges:
        union(i, j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    clusters = []
    for members in groups.values():
        if len(members) < 2:
            continue
        sims = [sim for sim, i, j in edges if i in members and j in members]
        clusters.append({
            "members": [skills[i]["name"] for i in members],
            "shared_terms": shared_terms(skills, members, idf),
            "mean_similarity": round(sum(sims) / len(sims), 3) if sims else 0.0,
            "cross_referenced": sorted({
                skills[i]["name"] for i in members
                if any(skills[k]["name"] in xrefs[i] for k in members if k != i)
            }),
        })
    clusters.sort(key=lambda c: (-len(c["members"]), -c["mean_similarity"]))

    top_pairs = [
        {"a": skills[i]["name"], "b": skills[j]["name"], "similarity": round(sim, 3)}
        for sim, i, j in pairs[:args.top_pairs]
    ]

    skills_out = []
    for i, s in enumerate(skills):
        skills_out.append({
            "name": s["name"],
            "category": s["category"],
            "description": s["description"],
            "body_words": s["body_words"],
            "support": s["support"],
            "support_file_count": s["support_file_count"],
            "skill_md_links": s["skill_md_links"],
            "references_other_skills": sorted(xrefs[i]),
            "referenced_by": sorted(skills[j]["name"] for j in range(n) if s["name"] in xrefs[j]),
            "narrow_name_reasons": narrow_name(s["name"]),
            "top_terms": [t for t, _ in sorted(
                {t: idf.get(t, 1.0) for t in set(s["_terms"])}.items(),
                key=lambda x: x[1], reverse=True)[:8]],
        })

    narrow = [s["name"] for s in skills_out if s["narrow_name_reasons"]]
    report = {
        "portfolio_dir": portfolio_dir,
        "skill_count": n,
        "threshold": args.threshold,
        "candidate_clusters": clusters,
        "top_pairs": top_pairs,
        "narrow_named": narrow,
        "skills": skills_out,
        "note": ("Clusters are TF-IDF term-overlap candidates, not verdicts. Confirm each "
                 "by the umbrella-class test; check package integrity (support/skill_md_links) "
                 "before archiving; migrate referenced_by links when consolidating."),
    }
    print(json.dumps(report, indent=2))
    print(f"Scanned {n} skills: {len(clusters)} candidate cluster(s), "
          f"{len(narrow)} narrow-named. Apply the umbrella-class test by judgment.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
