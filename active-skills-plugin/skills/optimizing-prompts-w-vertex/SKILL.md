---
name: optimizing-prompts
description: Use when a user wants to iteratively improve a prompt using Vertex AI Prompt Optimizer with zero-shot optimization and steering hints between iterations.
---

# Optimizing Prompts

This workflow runs the Vertex AI Prompt Optimizer in an interactive loop. The agent MUST call the real API each iteration — manual rewrites are never a substitute.

## Prerequisites

- [ ] **Detect GCP environment**: Run `python scripts/optimize_prompt.py --detect-env` and show the output to the user. This probes `gcloud` for active project, region, and auth status. Only ask the user to specify missing values — never ask for values that were successfully detected.
- [ ] **Confirm detected values**: Present detected project/location to the user and ask: "Are these correct, or do you want to override?" Proceed with overrides if provided.
- [ ] **Confirm dependencies**: Attempt `pip install "google-cloud-aiplatform>=1.87.0"`. If the install fails (e.g., corp network policy, Airlock, permission error), use the Docker runner instead — see **Docker Execution** below. Never block on a failed pip install; switch modes and proceed.
- [ ] **Confirm prompt**: Collect the full system prompt or user prompt to optimize.
- [ ] **Confirm task description** (optional): Ask what the prompt is trying to accomplish. Attach as context for the optimizer.

## Optimization Loop

Each iteration MUST follow this sequence exactly:

### Step 1 — Call the API

Run `scripts/optimize_prompt.py` with the current prompt and any accumulated steering hints:

```
python scripts/optimize_prompt.py --project <project_id> --location <location> --prompt "<current_prompt>" [--steering "<accumulated_hints>"] [--task-description "<task_description>"]
```

The script outputs JSON to stdout:

```json
{
  "iteration": 1,
  "original_prompt": "...",
  "suggested_prompt": "...",
  "optimization_metadata": {}
}
```

### Step 2 — Present Results

After receiving the JSON output, walk through each change before showing the menu. Parse the `changes` field (unified diff lines) and group consecutive hunk lines. Cross-reference each hunk against `optimization_metadata.applicable_guidelines` (match by overlapping text in `text_before_change` / `text_after_change`). For each hunk:

1. Print a header: `Change N of M`
2. Render the hunk as a fenced diff block — lines starting with `-` are removed, `+` are added, ` ` (space) are unchanged context. Example:

```diff
  ## Mode: Design Authoring Only

- You may:
+ **Permitted actions:**

- - Read any file
+ - Read any file (`Read`, `Glob`, `Grep`)
```

3. Immediately after the diff block, print a **Why this is better** line citing the matched guideline and its `suggested_improvement` explanation. Example:

> **Why this is better** (Ambiguity): The original used an undefined acronym. The revision spells it out, removing the need for the reader to infer meaning.

If no matching guideline exists for a hunk, omit the **Why** line rather than fabricating an explanation.

4. After all hunks are shown, present the menu:

```
Iteration N — N changes
───────────────────────────
Options:
  [A] Accept and finish
  [S] Add steering hint and re-optimize
  [R] Revert to original and restart
  [Q] Quit without saving
```

If `changes` is empty (no diff), note "No textual changes detected" and still show the menu.

### Step 3 — Collect Steering Hints

If the user selects `[S]`:

- Ask: "What must the next iteration improve or avoid?"
- Append the user's response to the cumulative steering list.
- Carry ALL prior steering hints into the next iteration (never discard prior hints).
- Return to Step 1 using the **optimized prompt from the current iteration** as the new input.

### Step 4 — Finalize

When the user accepts (`[A]`):

- Summarize the steering hints applied across all iterations.
- **If the prompt was supplied via `--prompt-file`:** Write the final optimized prompt directly back to that same file (overwriting it), then confirm: "Saved to `<path>`."
- **If the prompt was supplied inline (typed or pasted):** Display the final optimized prompt in a fenced code block, then offer to save it to a file.

## Testing Optimized Prompts

After accepting an optimized prompt, validate it against realistic inputs before deploying:

- **Use production-representative examples**: Edge cases and diverse inputs surface failures that the optimizer's training examples may not cover.
- **Positive example test**: If the optimization added negative constraints ("don't do X"), verify the prompt also shows what correct output looks like — negative-only constraints are lossy.
- **Scope check**: Confirm any new instructions state their scope explicitly (e.g., "apply to every section"). Models do not silently generalize.
- **Verbosity check**: Run 3–5 diverse inputs and verify length/style is consistent. If not, add a positive example of well-calibrated output to the prompt rather than adding more negative instructions.

## Steering Hint Guidelines

Present these guidelines when asking for steering input:

- Be specific: "Avoid jargon" beats "Make it clearer."
- Scope the target: "Only change the tone, not the structure."
- Quantify where possible: "Reduce to under 100 words."
- Specify what to preserve: "Keep the XML structure intact."

## Docker Execution

Use Docker when `pip install` fails (corp network policy, Airlock, missing permissions). The runner mounts gcloud ADC credentials so the container authenticates identically to the host.

**Build and run (first time — image is cached after):**

```
bash scripts/run_docker.sh --detect-env
bash scripts/run_docker.sh --prompt "<prompt>" [--steering "..."] [--project <id>] [--location <region>]
bash scripts/run_docker.sh --dry-run --prompt "<prompt>"
```

**Requirements:** Docker installed and daemon running. ADC credentials at `~/.config/gcloud` (or `$CLOUDSDK_CONFIG`). If permission denied, run `chmod +x scripts/run_docker.sh` first.

**Rebuild after script changes:**

```
docker rmi vertex-prompt-optimizer
bash scripts/run_docker.sh --prompt "..."
```

The JSON contract (stdout/stderr split) is identical to the direct `python` invocation — all loop steps work unchanged.

## Gotchas & Anti-Patterns

| Rationalization                                                       | Reality                                                                            |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| "Manual rewrite gives the same result"                                | The optimizer must be invoked; manual rewrites bypass model-based optimization.    |
| "This is a simple prompt, the API is overkill"                        | Prompt complexity is not the criterion. The user requested the optimizer — use it. |
| "One iteration is enough"                                             | The loop continues until the user explicitly accepts or quits.                     |
| "Run the optimizer once and add steering hints on behalf of the user" | Only the user provides steering hints. Never inject agent-authored hints.          |
| "The steering hints from iteration 1 no longer apply"                 | ALL accumulated hints carry forward. Never discard prior iterations' hints.        |
| "API call failed — approximate the result instead"                    | Surface the API error to the user and ask how to proceed. Never fake output.       |

## Error Handling

- **Auth error**: Instruct user to run `gcloud auth application-default login`.
- **Quota exceeded**: Surface the error verbatim; suggest retrying after a delay.
- **Invalid prompt**: Show the API error message; ask the user to revise the input prompt.
- **Script not found**: Instruct user to run from the skill root directory.
