#!/usr/bin/env bash
# PostToolUse hook: validate OKF §9 conformance on every .md write or edit.
# Reads tool-use JSON from stdin; extracts file_path; exits 1 on violation.
# A non-zero exit surfaces the validator's stderr to Claude as a required fix.

HOOK_JSON=$(cat)

FILE_PATH=$(echo "$HOOK_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('file_path', ti.get('path', '')))
except Exception:
    print('')
" 2>/dev/null)

[[ -z "$FILE_PATH" ]] && exit 0
[[ "$FILE_PATH" != *.md ]] && exit 0
[[ ! -f "$FILE_PATH" ]] && exit 0

exec python3 "$CLAUDE_PLUGIN_ROOT/scripts/okf_validate.py" --file "$FILE_PATH"
