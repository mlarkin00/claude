"""Promote stable facts from remember compressed history into memory-bank and agent-memory.

Usage:
  python3 scripts/graduate_memories.py --dry-run   # classify and print, no writes
  python3 scripts/graduate_memories.py             # classify and promote
  python3 scripts/graduate_memories.py --force     # bypass weekly rate-limit

Stability logic: archive.md content has survived >=7 days of Haiku compression — that is
the stability signal. recent.md adds corroboration. today-*.md files are never graduated
(too fresh; they'll appear in archive eventually if stable).
"""

import sys
import os
import json
import re
import time
import subprocess
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
from config import get_plugin_config
from resolve_remember import resolve_remember_dirs

# --- rate limiting ---

_GRADUATION_INTERVAL = 7 * 86400  # weekly

def _state_path():
    d = os.path.join(os.path.expanduser('~'), '.cache', 'memory-bank')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, '.graduation_state.json')

def should_run(force=False):
    if force:
        return True
    p = _state_path()
    if not os.path.exists(p):
        return True
    try:
        with open(p) as f:
            data = json.load(f)
        return time.time() - data.get('last_run', 0) >= _GRADUATION_INTERVAL
    except Exception:
        return True

def save_state():
    try:
        with open(_state_path(), 'w') as f:
            json.dump({"last_run": time.time()}, f)
    except Exception:
        pass

# --- read remember content ---

def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ''

def collect_content(dirs):
    """Aggregate archive and recent content across all discovered remember dirs.

    Returns dict with keys "archive" and "recent" as combined strings.
    today-*.md files are intentionally excluded from graduation candidates.
    """
    archive_parts, recent_parts = [], []
    for d in dirs:
        label = d['project']
        if d['archive_path']:
            text = _read(d['archive_path'])
            if text:
                archive_parts.append(f"[Project: {label}]\n{text}")
        if d['recent_path']:
            text = _read(d['recent_path'])
            if text:
                recent_parts.append(f"[Project: {label}]\n{text}")
    return {
        "archive": "\n\n---\n\n".join(archive_parts) or "(none)",
        "recent":  "\n\n---\n\n".join(recent_parts)  or "(none)",
    }

# --- Gemini classification ---

_GRADUATION_PROMPT = """\
You are reviewing compressed session history files from an AI coding assistant.

ARCHIVE (sessions older than 7 days, already compressed — most stable):
{archive}

RECENT (last 7 days, compressed — moderately stable):
{recent}

Your task: extract facts durable enough for permanent long-term memory.

INCLUDE facts that are:
- User preferences or work-style rules ("Always use Python 3 stdlib only; no pip installs")
- Validated patterns or constraints the user insists on ("Integration tests must hit real DB")
- User identity or expertise facts ("Deep Go expertise; new to React in this codebase")
- Stable project decisions or regulatory constraints ("Legal requires X format for session tokens")
- Stable reference pointers ("Bug tracker is Linear project INGEST")

EXCLUDE facts that are:
- Current task progress or in-progress work ("Currently implementing X", "PR is open for Y")
- Session-specific outcomes ("Fixed the bug in Z today")
- Questions or open investigations ("Need to investigate X")
- Timestamps, run counts, or ephemeral system state

Prefer facts that appear in BOTH archive and recent (highest stability).

For each qualifying fact:
- type: "user" | "feedback" | "project" | "reference"
  - user: who the user is, their role, expertise, preferences
  - feedback: rules about how to work (lead with an imperative: "Always do X")
  - project: stable decisions or constraints for a specific project
  - reference: where to find things (dashboards, trackers, docs)
- scope: "global" (applies across all projects) | "project" (specific to one project)
- fact: one clear imperative-voice sentence; no hedging words
- why: one sentence on why this belongs in permanent memory
- how_to_apply: one sentence on when/how to use it

Return exactly this JSON and nothing else:
{{"to_graduate": [{{"fact": "...", "type": "user|feedback|project|reference", \
"scope": "global|project", "why": "...", "how_to_apply": "..."}}]}}

If nothing qualifies, return: {{"to_graduate": []}}\
"""

def _get_access_token():
    try:
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True, timeout=10)
        return p.stdout.strip()
    except Exception:
        return None

def call_gemini(content, gcp_project):
    archive = content['archive']
    recent  = content['recent']
    if archive == '(none)' and recent == '(none)':
        return []

    prompt = _GRADUATION_PROMPT.format(archive=archive, recent=recent)
    url = (f"https://aiplatform.googleapis.com/v1/projects/{gcp_project}"
           f"/locations/global/publishers/google/models/gemini-3.5-flash:generateContent")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    token = _get_access_token()
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": gcp_project,
        "Authorization": f"Bearer {token}" if token else "",
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=60) as res:
            data = json.loads(res.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(text).get('to_graduate', [])
    except Exception as e:
        sys.stderr.write(f"[memory-bank] graduate: gemini call failed: {e}\n")
        return []

# --- promote to memory-bank (GCP) ---

def _add_memory_bank_fact(fact, scope_value, gcp_project, location, engine_id, user_hash):
    url = (f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{gcp_project}"
           f"/locations/{location}/reasoningEngines/{engine_id}/memories")
    payload = {
        "fact": fact,
        "scope": {"user": user_hash, "project": scope_value},
        "ttl": "2592000s",
    }
    token = _get_access_token()
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": gcp_project,
        "Authorization": f"Bearer {token}" if token else "",
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            result = json.loads(res.read().decode('utf-8'))
            return result.get('name', '').split('/')[-1]
    except Exception as e:
        sys.stderr.write(f"[memory-bank] graduate: failed to add memory-bank fact: {e}\n")
        return None


def promote_to_memory_bank(candidates, cfg, user_hash):
    gcp_project = cfg['project']
    location    = cfg['location']
    engine_id   = cfg['reasoning_engine_id']
    project_hash = resolve_project_id(os.getcwd())

    added = 0
    for c in candidates:
        fact  = c.get('fact', '').strip()
        scope = c.get('scope', 'global')
        if not fact:
            continue
        scope_value = 'global' if scope == 'global' else project_hash
        memory_id = _add_memory_bank_fact(fact, scope_value, gcp_project, location, engine_id, user_hash)
        if memory_id:
            added += 1
    return added


# --- promote to agent-memory (GitHub-backed Markdown) ---

def _slugify(text):
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')[:40]


def _agent_memory_repo():
    """Return the real path of the agent-memory git repo (resolves the ~/.claude/memory symlink)."""
    link = os.path.join(os.path.expanduser('~'), '.claude', 'memory')
    if os.path.islink(link):
        return os.path.realpath(link)
    if os.path.isdir(link):
        return link
    return None


def promote_to_agent_memory(candidates):
    repo = _agent_memory_repo()
    if not repo or not os.path.isdir(os.path.join(repo, '.git')):
        sys.stderr.write(f"[memory-bank] graduate: agent-memory repo not found; skipping.\n")
        return 0

    index_path = os.path.join(repo, 'MEMORY.md')
    existing_index = ''
    if os.path.isfile(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            existing_index = f.read()

    new_files = []
    index_additions = []

    for c in candidates:
        fact     = c.get('fact', '').strip()
        typ      = c.get('type', 'feedback')
        why      = c.get('why', '')
        how      = c.get('how_to_apply', '')
        if not fact:
            continue

        slug     = _slugify(fact[:50])
        filename = f"{typ}_{slug}.md"
        filepath = os.path.join(repo, filename)

        # Skip if already present in the repo (simple filename-based idempotency;
        # sidecar dedup handles semantic duplicates introduced by repeated graduation runs).
        if os.path.exists(filepath):
            continue

        # Short title: first 5 words, no trailing period
        title = ' '.join(fact.split()[:5]).rstrip('.')

        body = f"""---
name: {title}
description: {fact}
type: {typ}
---

{fact}

**Why:** {why}
**How to apply:** {how}
"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(body)
            new_files.append(filename)
            hook = f"{fact[:80]}..." if len(fact) > 80 else fact
            index_additions.append(f"- [{title}]({filename}) — {hook}")
        except Exception as e:
            sys.stderr.write(f"[memory-bank] graduate: failed to write {filename}: {e}\n")

    if not new_files:
        return 0

    # Append new entries to MEMORY.md
    try:
        separator = '\n' if existing_index and not existing_index.endswith('\n') else ''
        with open(index_path, 'a', encoding='utf-8') as f:
            f.write(separator + '\n'.join(index_additions) + '\n')
    except Exception as e:
        sys.stderr.write(f"[memory-bank] graduate: failed to update MEMORY.md: {e}\n")

    # Commit and push so agent-memory's GitHub copy stays in sync
    _git_commit_push(repo, new_files)
    return len(new_files)


def _git_user_identity():
    """Return (name, email) from gcloud config, falling back to generic defaults."""
    try:
        p = subprocess.run(['gcloud', 'config', 'get-value', 'account', '--quiet'],
                           capture_output=True, text=True, timeout=5)
        email = p.stdout.strip()
        if email and '@' in email:
            name = email.split('@')[0].replace('.', ' ').title()
            return name, email
    except Exception:
        pass
    return 'memory-bank', 'memory-bank@localhost'


def _git_commit_push(repo, new_files):
    import datetime
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    files_str = ', '.join(new_files[:3])
    if len(new_files) > 3:
        files_str += f' (+{len(new_files) - 3} more)'
    msg = f"memory: graduated from remember — {files_str} @ {ts}"
    name, email = _git_user_identity()
    try:
        subprocess.run(['git', '-C', repo, 'add', '--', '*.md'],
                       check=True, capture_output=True, timeout=15)
        subprocess.run(
            ['git', '-C', repo,
             '-c', f'user.name={name}', '-c', f'user.email={email}',
             'commit', '-m', msg],
            check=True, capture_output=True, timeout=15,
        )
        subprocess.run(['git', '-C', repo, 'push', 'origin', 'main'],
                       check=True, capture_output=True, timeout=30)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"[memory-bank] graduate: git commit/push failed: {e.stderr.decode() if e.stderr else e}\n")
    except Exception as e:
        sys.stderr.write(f"[memory-bank] graduate: git error: {e}\n")


# --- dry-run output ---

def print_findings(candidates):
    if not candidates:
        print("[memory-bank] graduate: nothing qualifies for graduation.")
        return
    print(f"[memory-bank] graduate: {len(candidates)} candidate(s) to promote:\n")
    for i, c in enumerate(candidates, 1):
        scope_label = f"{c.get('type', '?')} / {c.get('scope', '?')}"
        print(f"  {i}. [{scope_label}]")
        print(f"     fact:          {c.get('fact', '')}")
        print(f"     why:           {c.get('why', '')}")
        print(f"     how_to_apply:  {c.get('how_to_apply', '')}")
        print()


# --- main ---

def run(dry_run=False, force=False):
    if not force and not should_run():
        sys.stderr.write("[memory-bank] graduate: skipping (ran within last 7 days; use --force to override).\n")
        return

    dirs = resolve_remember_dirs()
    if not dirs:
        sys.stderr.write("[memory-bank] graduate: no remember directories with content found.\n")
        return

    content = collect_content(dirs)
    if content['archive'] == '(none)' and content['recent'] == '(none)':
        sys.stderr.write("[memory-bank] graduate: archive and recent are empty; nothing to graduate.\n")
        return

    cfg      = get_plugin_config()
    user_hash = resolve_user_id()
    candidates = call_gemini(content, cfg['project'])

    if dry_run:
        print_findings(candidates)
        return

    if not candidates:
        sys.stderr.write("[memory-bank] graduate: nothing qualifies for graduation.\n")
        save_state()
        return

    mb_added  = promote_to_memory_bank(candidates, cfg, user_hash)
    am_added  = promote_to_agent_memory(candidates)
    save_state()
    sys.stderr.write(
        f"[memory-bank] graduate: done — {mb_added} added to memory-bank, "
        f"{am_added} added to agent-memory.\n"
    )


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    force   = '--force' in sys.argv
    run(dry_run=dry_run, force=force)
