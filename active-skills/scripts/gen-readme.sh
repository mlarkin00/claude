#!/usr/bin/env bash
# Regenerate the auto-managed skill inventory in README.md between the
# <!-- SKILLS:START --> / <!-- SKILLS:END --> markers, from the frontmatter of
# each skills/*/SKILL.md. Run after every sync so the README never drifts.
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="$PLUGIN_ROOT/README.md"
SKILLS_DIR="$PLUGIN_ROOT/skills"

count=0
rows=""
for d in "$SKILLS_DIR"/*/; do
  [ -f "$d/SKILL.md" ] || continue
  name=$(basename "$d")
  # First `description:` line in the frontmatter; strip surrounding quotes and CRs.
  desc=$(awk '/^description:/{sub(/^description:[[:space:]]*/,""); print; exit}' "$d/SKILL.md" \
    | sed -e 's/\r$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
  rows+="- **\`${name}\`** — ${desc}"$'\n'
  count=$((count + 1))
done

block=$'<!-- SKILLS:START -->\n'"**${count} skills** (auto-generated — do not edit by hand):"$'\n\n'"${rows}"$'<!-- SKILLS:END -->'

# Replace everything between the markers (inclusive) with the freshly built block.
python3 - "$README" "$block" <<'PY'
import re, sys
path, block = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
pattern = re.compile(r"<!-- SKILLS:START -->.*?<!-- SKILLS:END -->", re.DOTALL)
if not pattern.search(text):
    raise SystemExit("markers not found in README.md")
text = pattern.sub(lambda _: block, text)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
PY

echo "gen-readme: wrote ${count} skills into README.md"
