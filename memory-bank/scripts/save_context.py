import sys
import os
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id
from config import get_plugin_config

def extract_text(content):
    """Handle Claude Code content as string or list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [block.get('text', '') for block in content
                 if isinstance(block, dict) and block.get('type') == 'text']
        return '\n'.join(parts)
    return ''

def send_generation_request(project, location, engine_id, user_hash, project_hash, events):
    url = f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}/memories:generate"
    payload = {
        "scope": {
            "user": user_hash,
            "project": project_hash
        },
        "directContentsSource": {
            "events": events
        }
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": project
    }
    try:
        import subprocess
        p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'],
                           capture_output=True, text=True, check=True)
        token = p.stdout.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except Exception:
        return False

def run():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        return

    # This hook serves both runtimes and they key the payload differently:
    # Antigravity uses protojson camelCase (`transcriptPath`), Claude Code uses
    # snake_case (`transcript_path`). Reading only the camelCase one meant the
    # lookup returned None under Claude Code and the function returned right
    # below — the Stop hook ran, exited 0, and sent nothing, silently, for as
    # long as the plugin has existed.
    transcript_path = (input_data.get('transcriptPath')
                       or input_data.get('transcript_path'))

    if not transcript_path or not os.path.exists(transcript_path):
        return

    events = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    step = json.loads(line.strip())
                except (json.JSONDecodeError, TypeError):
                    continue

                # Support both direct {role, content} and nested {message: {role, content}} formats
                msg = step if 'role' in step else step.get('message', {})
                role = msg.get('role', '')
                content = extract_text(msg.get('content', ''))

                # Memory Bank's directContentsSource.events wants Content-shaped
                # events: {"content": {"role": "user"|"model", "parts": [{"text": ...}]}}.
                if role == 'user' and content:
                    events.append({"content": {"role": "user", "parts": [{"text": content}]}})
                elif role == 'assistant' and content:
                    events.append({"content": {"role": "model", "parts": [{"text": content}]}})
    except Exception:
        return

    if not events:
        return

    user_hash = resolve_user_id()
    # Session-end consolidation is always global scope. The workspace path the
    # payload carries (`workspacePaths` on Antigravity, `cwd` on Claude Code) is
    # deliberately not read: resolving a project scope here would split the
    # session's facts away from where the loader looks for them.
    project_hash = "global"

    cfg = get_plugin_config()
    send_generation_request(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                            user_hash, project_hash, events)

    # Fail-open nudge: ask the deployed memory-minion agent to curate the new facts.
    # Best-effort and non-blocking — if it can't fire, the agent's schedule covers it.
    try:
        import subprocess
        nudge = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nudge_minion.py')
        subprocess.Popen([sys.executable, nudge],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

if __name__ == '__main__':
    run()
