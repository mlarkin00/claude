#!/usr/bin/env bash
# PostToolUse hook: validate OKF §9 conformance on .md writes INSIDE an OKF bundle.
# Reads tool-use JSON from stdin; extracts file_path; exits 1 on violation.
# A non-zero exit surfaces the validator's stderr to Claude as a required fix.
#
# Scoped to bundles on purpose. This hook is global — it sees every .md write on
# the machine — but `type` is an OKF requirement, not a markdown one. Plenty of
# legitimate markdown carries non-OKF frontmatter: every Claude Code SKILL.md
# (name/description) and every google/design.md DESIGN.md (name/version/colors).
# Validating those blocked 79 files in one repo alone, turning an unrelated
# SKILL.md edit into a hook failure. Outside a bundle we have no business
# enforcing OKF.

HOOK_JSON=$(cat)

# Claude Code sends snake_case `tool_input`; Antigravity sends protojson
# camelCase `toolCall.args`, keyed differently per tool. Report which shape the
# path came from as well as the path — the two runtimes want different replies.
EXTRACT=$(echo "$HOOK_JSON" | python3 -c "
import json, sys
CLAUDE_KEYS = ('file_path', 'path')
AGY_KEYS = ('AbsolutePath', 'TargetFile', 'file_path', 'path', 'Path')
runtime, path = 'claude', ''
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input')
    if isinstance(ti, dict):
        path = next((str(ti[k]) for k in CLAUDE_KEYS if ti.get(k)), '')
    if not path:
        args = (d.get('toolCall') or {}).get('args')
        if isinstance(args, dict):
            path = next((str(args[k]) for k in AGY_KEYS if args.get(k)), '')
            if path:
                runtime = 'agy'
except Exception:
    pass
print(runtime)
print(path)
" 2>/dev/null)

{ read -r RUNTIME; read -r FILE_PATH; } <<< "$EXTRACT"

# Antigravity's PostToolUse reply is a bare {} — it can neither block the step
# nor feed anything back to the model — so it gets one on every exit path.
finish() {
    [[ "$RUNTIME" == "agy" ]] && printf '{}\n'
    exit "${1:-0}"
}

[[ -z "${FILE_PATH:-}" ]] && finish 0
[[ "$FILE_PATH" != *.md ]] && finish 0
[[ ! -f "$FILE_PATH" ]] && finish 0

# Resolve the validator from this script's own location, not $CLAUDE_PLUGIN_ROOT
# — Antigravity does not define that variable, and an unset one expanded to a
# bare "/scripts/okf_validate.py". readlink -f, not dirname alone, so the path
# survives being reached through a symlink.
PLUGIN_ROOT=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd) \
    || PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
VALIDATOR="$PLUGIN_ROOT/scripts/okf_validate.py"
[[ -f "$VALIDATOR" ]] || finish 0

# Walk up for a bundle root: an index.md carrying `okf_version` (per the OKF
# spec, the only index.md with frontmatter). Not under one => not an OKF file.
dir=$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && pwd) || finish 0
while [[ -n "$dir" && "$dir" != "/" ]]; do
    if [[ -f "$dir/index.md" ]] && grep -qs '^okf_version:' "$dir/index.md"; then
        if [[ "$RUNTIME" == "agy" ]]; then
            # Non-zero cannot surface a fix there, so report and let it stand.
            python3 "$VALIDATOR" --file "$FILE_PATH" >&2 || true
            finish 0
        fi
        exec python3 "$VALIDATOR" --file "$FILE_PATH"
    fi
    dir=$(dirname "$dir")
done

finish 0
