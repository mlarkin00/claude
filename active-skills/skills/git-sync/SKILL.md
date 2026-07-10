---
name: git-sync
description: Use this skill when the user asks to sync, update, pull, push, fetch, merge, or rebase the codebase with the remote GitHub repository, or when they run the slash command /git-sync with optional parameters (e.g., "/git-sync", "/git-sync prefer remote", "/git-sync prefer local"). This skill handles git merge or rebase operations safely, ensuring local changes are preserved and prompting the user only if there are irreconcilable merge conflicts, or automatically resolving conflicts if a preference (local/remote) is specified. Make sure to use this skill whenever the user mentions git, remote, syncing, pushing, pulling, or keeping the workspace up to date.
metadata:
  category: team-automation
---

# Git Sync Skill

Synchronize the local repository state with the remote tracking branch safely and robustly.

**Core Principles:**
1.  **Safety First:** Always preserve any uncommitted changes by stashing them automatically before syncing.
2.  **No Unintended Force Pushing:** Never force push changes to remote unless the user explicitly requested it.
3.  **No Confusion on Conflicts:** Abstract git's rebase/merge conflict naming quirks (`--ours`/`--theirs`) into standard `local` and `remote` choices so the agent and user can make safe decisions.
4.  **Automatic Resolution Preferences:** Support resolving conflicts automatically when the user expresses a preference (e.g. `prefer remote` or `prefer local`), prompting the user ONLY for interactive conflicts.

---

## Interactive Workflow

Follow these steps exactly to perform a Git synchronization.

### Step 1: Initialize and Check Status

Run the helper script's `status` command to assess the current repository state:

```bash
active-skills/git-sync/scripts/git_sync.py status
```

Check the JSON output:
- If `is_git` is `false`, notify the user that git is not initialized and stop.
- If `upstream` is null, look at `branch`. If there is an origin branch with the same name, the script will automatically set upstream. If it cannot, prompt the user to set upstream.
- Note if `is_clean` is `false`. The script will automatically stash local changes on sync.

### Step 2: Determine Preference and Sync Mode

1.  **Preference Check:**
    -   If the user's prompt or instruction mentions "prefer remote", "prefer theirs", "incoming", or starts/contains the slash command `/git-sync prefer remote` or `/git-sync prefer theirs`, use `--prefer remote`.
    -   If the user's prompt or instruction mentions "prefer local", "prefer ours", "current", or starts/contains the slash command `/git-sync prefer local` or `/git-sync prefer ours`, use `--prefer local`.
    -   Otherwise, use `--prefer interactive`.
2.  **Sync Mode Check:**
    -   Unless the user explicitly asks for "merge", default to `--mode rebase` to maintain a clean linear git history.

### Step 3: Run the Sync Command

Execute the sync command with the configured flags:

```bash
active-skills/git-sync/scripts/git_sync.py sync --mode <rebase|merge> --prefer <local|remote|interactive>
```

#### Scenario A: Success
If the JSON response returns `"status": "success"`:
- Print the success message.
- If `"stashed": true`, notify the user that their uncommitted changes were safely stashed and restored.
- Complete the sync.

#### Scenario B: Conflict
If the JSON response returns `"status": "conflict"`:
- **If `--prefer` was `local` or `remote`:** The script attempted auto-resolution but failed to complete. Inspect the error and prompt the user.
- **If `--prefer` was `interactive`:**
  - Read the `conflicted_files` and `conflicts` fields in the JSON response.
  - For each conflicted file and conflict hunk, present a clean markdown preview of the choices to the user:
    - **Local Version (Current / ours)**
    - **Remote Version (Incoming / theirs)**
  - Ask the user to choose which version to keep. Do NOT guess or make assumptions for interactive conflicts.
  - To resolve a file to all local or all remote:
    ```bash
    active-skills/git-sync/scripts/git_sync.py resolve --file <filepath> --choice <local|remote>
    ```
  - To resolve hunk-by-hunk, construct a JSON map of hunk choices (e.g., `{"0": "local", "1": "remote"}`) and run:
    ```bash
    active-skills/git-sync/scripts/git_sync.py resolve --file <filepath> --hunk-choices '<json_choices>'
    ```
  - Once all conflicted files are resolved, continue the synchronization:
    ```bash
    active-skills/git-sync/scripts/git_sync.py continue
    ```
  - If any step fails or the user wants to cancel, abort the sync and restore the previous state:
    ```bash
    active-skills/git-sync/scripts/git_sync.py abort
    ```

---

## Gotchas & Anti-Patterns

| Excuse | Reality |
| :--- | :--- |
| "I can just force-push to align local and remote" | Force-pushing can overwrite other developers' work. Never force-push during sync. |
| "I don't need to stash first because git will tell me if there's a conflict" | Uncommitted changes can block rebase/merge entirely or get mixed with conflict markers, leading to data loss. |
| "I'll just let the user edit the file themselves" | Proactively parse conflict files using the helper script and present a clean, structured choice (Local/Remote) to minimize friction. |
| "The branch has no remote tracking branch, so I'll create one" | Always confirm if the user wants to set an upstream tracking branch first. |
| "During rebase, --ours is local" | FALSE. During rebase, `--ours` is the remote (upstream) commit and `--theirs` is local! Always use the helper script to shield yourself and the user from this quirk. |
