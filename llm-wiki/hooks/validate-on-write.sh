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

# Walk up for a bundle root: an index.md carrying `okf_version` (per the OKF
# spec, the only index.md with frontmatter). Not under one => not an OKF file.
dir=$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && pwd) || exit 0
while [[ -n "$dir" && "$dir" != "/" ]]; do
    if [[ -f "$dir/index.md" ]] && grep -qs '^okf_version:' "$dir/index.md"; then
        exec python3 "$CLAUDE_PLUGIN_ROOT/scripts/okf_validate.py" --file "$FILE_PATH"
    fi
    dir=$(dirname "$dir")
done

exit 0
