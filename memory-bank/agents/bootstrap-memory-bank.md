---
name: bootstrap-memory-bank
description: "Use when setting up the memory-bank plugin on a new machine, when the GCP reasoning engine needs to be created, or when load_context.py returns no memories and you suspect the engine ID is wrong. Handles: ADC verification, engine creation/verification, config update, optional CC memory import."
model: sonnet
tools:
  - Bash
  - Read
  - Edit
---

You are bootstrapping the GCP Memory Bank for Claude Code. Every step is idempotent. Print a one-line status for each step: `✓ OK`, `✓ CREATED`, `→ SKIPPED`, or `✗ FAILED`.

## Step 1: Verify ADC

```bash
gcloud auth application-default print-access-token > /dev/null && echo "ADC OK"
```

If this fails, tell the user to run `gcloud auth application-default login` and stop. Do not proceed.

## Step 2: Locate plugin root

```bash
echo "$CLAUDE_PLUGIN_ROOT"
```

If empty, find it:
```bash
find ~/.claude -name "plugin.json" -path "*/memory-bank/.claude-plugin/plugin.json" 2>/dev/null | head -1 | xargs dirname | xargs dirname
```

Use that path as `PLUGIN_ROOT` for the rest of this script.

## Step 3: Read current config

Read `$PLUGIN_ROOT/.claude-plugin/plugin.json`. Note the `config.reasoning_engine_id`.

## Step 4: Verify or create the reasoning engine

```bash
PROJECT=$(python3 -c "import json; d=json.load(open('$PLUGIN_ROOT/.claude-plugin/plugin.json')); print(d['config']['project'])")
LOCATION=$(python3 -c "import json; d=json.load(open('$PLUGIN_ROOT/.claude-plugin/plugin.json')); print(d['config']['location'])")
ENGINE_ID=$(python3 -c "import json; d=json.load(open('$PLUGIN_ROOT/.claude-plugin/plugin.json')); print(d['config']['reasoning_engine_id'])")
TOKEN=$(gcloud auth application-default print-access-token)

curl -sf -H "Authorization: Bearer $TOKEN" \
  -H "X-Goog-User-Project: $PROJECT" \
  "https://$LOCATION-aiplatform.googleapis.com/v1beta1/projects/$PROJECT/locations/$LOCATION/reasoningEngines/$ENGINE_ID" \
  > /dev/null && echo "Engine exists: $ENGINE_ID"
```

If the engine does NOT exist (curl returns non-zero), create it:

```bash
python3 "$PLUGIN_ROOT/scripts/create_engine.py"
```

Note the `Engine ID:` line in the output.

## Step 5: Update plugin.json with engine ID (if newly created)

If a new engine was created in Step 4, use the Edit tool to update `config.reasoning_engine_id` in `$PLUGIN_ROOT/.claude-plugin/plugin.json`.

## Step 6: Verify context loads

```bash
echo '{}' | python3 "$PLUGIN_ROOT/scripts/load_context.py"
```

Output should be `{"injectSteps": [...]}`. If it's `{"injectSteps": []}`, the engine is empty — that's expected on first run. If it's an error, check the engine ID and ADC.

## Step 7: (Optional) Import existing Claude Code memories

Ask the user: "Do you want to import your existing Claude Code memory files (~/.claude/memory/) into the GCP Memory Bank? (yes/no)"

If yes:
```bash
python3 "$PLUGIN_ROOT/scripts/import_cc_memories.py"
```

## Step 8: Verify symlinks are wired

```bash
bash "$PLUGIN_ROOT/scripts/install-symlinks.sh"
ls ~/.claude/scripts/memory-bank/add_memory.py
```

Only the scripts are linked. The plugin's skills are loaded from the plugin
itself, so there is nothing under `~/.claude/skills/` to check.

## Final summary

Print a status table for all 8 steps, then:

> "Memory Bank is ready. GCP memories will be fetched at each session start and consolidated at session end. Use `/memory-bank` to save important facts immediately."
