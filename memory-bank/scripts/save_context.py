import sys
import os
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resolve_scope import resolve_user_id, resolve_project_id
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

    transcript_path = input_data.get('transcriptPath')
    workspace_paths = input_data.get('workspacePaths', [])
    workspace_path = workspace_paths[0] if workspace_paths else None

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
    project_hash = "global"  # default scope for session-end consolidation

    cfg = get_plugin_config()
    send_generation_request(cfg["project"], cfg["location"], cfg["reasoning_engine_id"],
                            user_hash, project_hash, events)

if __name__ == '__main__':
    run()
