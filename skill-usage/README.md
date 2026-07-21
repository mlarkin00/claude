# skill-usage

Counts how often each skill is invoked and commits the totals to a git repository you choose.

Works in both Claude Code and Antigravity, and ships **no skills of its own** — it counts every skill invocation, whichever plugin provided it. That is what removes the need to maintain a list of skill names or scope against a particular bundle.

## Install

**Claude Code:**

```
/plugin marketplace add mlarkin00/claude
/plugin install skill-usage@mlarkin00-claude
```

**Antigravity:**

```
agy plugin install https://github.com/mlarkin00/claude
```

## Configure

Tracking is **opt-in**. Point `SKILL_USAGE_REPO` at a git work tree:

```json
"env": { "SKILL_USAGE_REPO": "/path/to/a/private/repo" }
```

in `~/.claude/settings.json`, which keeps a machine-specific path out of the plugin. Counts are written to `skill-usage.json` at that repo's root:

```json
{
  "systematic-debugging": { "count": 12, "last_used_at": "2026-07-21T19:49:08Z" }
}
```

With the variable unset, counts fall back to `~/.claude/skill-usage.json` and no git command runs. `ACTIVE_SKILLS_USAGE_REPO` is still honoured, so installs predating the split out of `active-skills` keep working.

**Usage counts are personal telemetry — point this at a private repo.**

## How it works

The two runtimes dispatch skills differently, so each gets its own thin adapter over a shared core:

| | Claude Code | Antigravity |
|---|---|---|
| A skill use appears as | a `Skill` tool call | a read of `skills/<name>/SKILL.md` — there is no skill-activation tool |
| Detected from | `tool_input.skill` | `toolCall.args` path, falling back to the transcript |
| Flush | `SessionEnd` hook | `sidecars/sync-usage` on a schedule |

`active-skills:gcloud` and `gcloud` share one counter, so the two runtimes agree on a single key per skill.

Counts accumulate during a session and are committed once at the end rather than per invocation. The commit is scoped with `git commit --only` so unrelated staged work is untouched, the sync skips a repo that is mid-merge or mid-rebase, and a failed push simply leaves the commit for next time. Writes are atomic and taken under an exclusive `flock`, since parallel sessions share the file.

Every hook exits 0 on every path — malformed input, a missing or non-git repo, a failed push. A tracker that blocks a session is worse than one that misses a count.

## Antigravity quirks worth knowing

Both fail silently, and both cost real debugging time to find:

- A `Stop` block anywhere in a plugin's `hooks.json` prevents `PostToolUse` from firing. The plugin installs, `agy` reports the hooks processed, nothing errors, and counts simply never appear. A separate named hook block does not avoid it. This is why the flush here is a scheduled sidecar.
- `PostToolUse` handlers must use the nested `{"matcher", "hooks"}` form. The flat `{"type", "command"}` form installs but never fires.

Verified against `agy` 1.1.5.
