#!/bin/bash
set -euo pipefail

# Analyze — and optionally de-symlink — agent briefing files
# (AGENTS.md, GEMINI.md, CLAUDE.md).
#
# Briefing files MUST be standalone, individual regular files, never symlinks.
# Symlinks prevent tailoring instructions per agent and break silently when
# their target moves or is deleted (dangling links).
#
# Usage:
#   ./analyze-agent-docs.sh [DIRECTORY]          # report status only (default)
#   ./analyze-agent-docs.sh --fix [DIRECTORY]    # report, then de-symlink in place
#
# --fix dereferences each symlinked briefing file: it copies the content the
# symlink currently resolves to into a standalone regular file and removes the
# link. The link's former target is left untouched (removing a symlink never
# deletes what it points at). A dangling symlink (broken target) is replaced
# with an empty standalone file and flagged, since its content is unrecoverable.

FIX="No"
if [[ "${1:-}" == "--fix" ]]; then
    FIX="Yes"
    shift
fi

TARGET_DIR=${1:-'.'}
FILES=("AGENTS.md" "GEMINI.md" "CLAUDE.md")
MAX_LINES=100

if [[ "$FIX" == "Yes" ]]; then
    echo "Analyzing and de-symlinking agent briefing files in $TARGET_DIR..."
else
    echo "Analyzing agent briefing files in $TARGET_DIR..."
fi
echo ""

FIXED_COUNT=0
DANGLING_COUNT=0

for FILE in "${FILES[@]}"; do
    PATH_TO_FILE="$TARGET_DIR/$FILE"
    echo "--- $FILE ---"

    if [[ -L "$PATH_TO_FILE" ]]; then
        TARGET=$(readlink "$PATH_TO_FILE")
        echo "Symlink: Yes -> $TARGET"

        if [[ ! -e "$PATH_TO_FILE" ]]; then
            echo "WARNING: dangling symlink — target '$TARGET' does not exist."
            if [[ "$FIX" == "Yes" ]]; then
                rm "$PATH_TO_FILE"
                : > "$PATH_TO_FILE"
                echo "FIXED: removed dangling symlink and created empty standalone $FILE (content was unrecoverable — populate it manually)."
                DANGLING_COUNT=$((DANGLING_COUNT + 1))
            else
                echo "ACTION: re-run with --fix to remove the dangling link (content is unrecoverable)."
            fi
        elif [[ "$FIX" == "Yes" ]]; then
            MODE=$(stat -L -c '%a' "$PATH_TO_FILE")  # -L follows the link -> target's mode
            TMP=$(mktemp "${PATH_TO_FILE}.desymlink.XXXXXX")
            cat "$PATH_TO_FILE" > "$TMP"   # cat follows the link -> materializes target content
            chmod "$MODE" "$TMP"           # keep the standalone file's perms consistent with the target
            rm "$PATH_TO_FILE"             # removes only the link, not the target
            mv "$TMP" "$PATH_TO_FILE"      # standalone regular file with the same content
            echo "FIXED: de-symlinked $FILE into a standalone regular file ($(wc -l < "$PATH_TO_FILE") lines)."
            FIXED_COUNT=$((FIXED_COUNT + 1))
        else
            echo "WARNING: $FILE is a symlink. Briefing files MUST be standalone. Re-run with --fix to de-symlink."
        fi

    elif [[ -f "$PATH_TO_FILE" ]]; then
        LINE_COUNT=$(wc -l < "$PATH_TO_FILE")
        echo "Symlink: No (standalone file)"
        echo "Lines: $LINE_COUNT"
        if [[ $LINE_COUNT -gt $MAX_LINES ]]; then
            echo "WARNING: $FILE exceeds $MAX_LINES lines ($LINE_COUNT lines). Consider refactoring to use pointers."
        fi
    else
        echo "Status: Not found"
    fi
    echo ""
done

# Check for .local variants
echo "Checking for local overrides..."
find "$TARGET_DIR" -maxdepth 1 \( -name ".claude.local.md" -o -name ".gemini.local.md" \) -printf "Found: %p\n"

if [[ "$FIX" == "Yes" ]]; then
    echo ""
    echo "Done. De-symlinked: $FIXED_COUNT | Dangling links cleared (need manual content): $DANGLING_COUNT"
    if [[ $DANGLING_COUNT -gt 0 ]]; then
        echo "NOTE: dangling-link files were left empty — populate them before relying on them."
    fi
fi
