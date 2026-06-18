"""
Imports existing Claude Code markdown memory files (~/.claude/memory/*.md)
into the GCP Memory Bank as global-scoped facts.
"""
import sys
import os
import json
import re
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id
from config import get_plugin_config

MEMORY_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'memory')

def parse_frontmatter(text):
    """Extract YAML frontmatter values as a flat dict (name, description, type)."""
    match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip()
    return fm

def parse_body(text):
    """Return everything after the frontmatter block."""
    match = re.match(r'^---\n.*?\n---\n(.*)', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

def fact_from_memory_file(path):
    """Construct a fact string from a memory markdown file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    fm = parse_frontmatter(content)
    body = parse_body(content)

    name = fm.get('name', os.path.basename(path))
    description = fm.get('description', '')
    mem_type = fm.get('type', '')

    parts = [f"[{mem_type.upper()}] {name}" if mem_type else name]
    if description:
        parts.append(description)
    if body:
        parts.append(body)
    return '\n'.join(parts)

def get_access_token():
    import subprocess
    try:
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return None

def save_fact(project, location, engine_id, user_hash, fact):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories"
    payload = {
        "scope": {"user": user_hash, "project": "global"},
        "fact": fact,
        "ttl": "2592000s"
    }
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": project}
    token = get_access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status in (200, 201)
    except Exception as e:
        print(f"  Error: {e}")
        return False

def main():
    if not os.path.exists(MEMORY_DIR):
        print(f"No memory directory found at {MEMORY_DIR}")
        return

    files = [f for f in os.listdir(MEMORY_DIR)
             if f.endswith('.md') and f != 'MEMORY.md']

    if not files:
        print("No memory files to import.")
        return

    cfg = get_plugin_config()
    user_hash = resolve_user_id()

    print(f"Importing {len(files)} memory file(s) from {MEMORY_DIR} → GCP Memory Bank...")
    saved, failed = 0, 0
    for fname in sorted(files):
        path = os.path.join(MEMORY_DIR, fname)
        fact = fact_from_memory_file(path)
        if not fact:
            print(f"  SKIP  {fname} (could not parse)")
            continue
        ok = save_fact(cfg["project"], cfg["location"], cfg["reasoning_engine_id"], user_hash, fact)
        if ok:
            print(f"  OK    {fname}")
            saved += 1
        else:
            print(f"  FAIL  {fname}")
            failed += 1

    print(f"\nDone: {saved} imported, {failed} failed.")

if __name__ == '__main__':
    main()
