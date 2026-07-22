---
name: refresh-skills
description: "Use this skill when the user asks to sync, update, or refresh the local agent-skills repository with its remote tracking branch on GitHub, or when they mention 'refresh skills', 'update agent skills', 'pull latest skills', 'sync agent skills repo with github', or similar commands. This skill looks for the repository at ~/agent-skills, runs the sync using the git-sync helper script with the 'prefer remote' configuration, and guides conflict resolution if any issues arise."
metadata:
  category: team-automation
---

# Refresh Skills Skill

Synchronize the local `agent-skills` repository with its upstream tracking branch on GitHub safely, robustly, and automatically prioritizing remote tracking state.

---

## Interactive Workflow

Follow these steps exactly to perform a synchronization of the `agent-skills` repository.

### Step 1: Locate the Repository Path

- [ ] **Verify** if the default directory `~/agent-skills` (resolved to `/home/matthewlarkin/agent-skills`) exists and contains a `.git` sub-directory.
- [ ] **Handle Missing Directory**: If the directory does NOT exist:
  - [ ] **Prompt** the user: *"The agent-skills repository was not found at `~/agent-skills`. Please provide the absolute path to the local `agent-skills` directory."*
  - [ ] **Wait** for the user to provide the path, then verify it.
  - [ ] **Set** this verified path as `<path-to-repo>`.

### Step 2: Execute Sync with Prefer Remote

- [ ] **Locate and execute the git-sync script** inside the located repository using:
  ```bash
  python3 <path-to-repo>/active-skills/git-sync/scripts/git_sync.py --cwd <path-to-repo> sync --mode rebase --prefer remote
  ```
- [ ] **Read and parse** the JSON output from the command.

### Step 3: Handle the Output Results

- [ ] **Evaluate status**:
  - [ ] **Scenario A: Successful Sync**
    - [ ] If the JSON response returns `"status": "success"`:
      - [ ] **Present** the success message to the user.
      - [ ] If `"stashed": true`, **notify** the user that their uncommitted local changes were safely stashed and restored.
  - [ ] **Scenario B: Sync Conflict**
    - [ ] If the JSON response returns `"status": "conflict"`:
      - [ ] **Case 1: Rebase or Merge Conflict**
        - [ ] If `op_type` is `rebase` or `merge` and there are conflicted files:
          - [ ] **Attempt to auto-resolve** each conflicted file to remote:
            ```bash
            python3 <path-to-repo>/active-skills/git-sync/scripts/git_sync.py --cwd <path-to-repo> resolve --file <filepath> --choice remote
            ```
          - [ ] **Continue** the sync:
            ```bash
            python3 <path-to-repo>/active-skills/git-sync/scripts/git_sync.py --cwd <path-to-repo> continue --prefer remote
            ```
      - [ ] **Case 2: Auto-resolution Fails or User Decision Required**
        - [ ] If the operation still fails or cannot be automatically resolved using `remote`:
          - [ ] **List** the conflicted files to the user.
          - [ ] **Ask** the user if they want to **force override** their local files with remote changes or **abort** the synchronization.
          - [ ] If they choose to abort:
            ```bash
            python3 <path-to-repo>/active-skills/git-sync/scripts/git_sync.py --cwd <path-to-repo> abort
            ```

---

## Gotchas & Anti-Patterns

| Excuse | Reality |
| :--- | :--- |
| "The directory `~/agent-skills` does not exist, so a new repository will be initialized." | **NEVER** initialize a new repository. Always prompt the user for the correct repository path first. |
| "Running standard `git pull --rebase` directly instead of using the helper script." | **NEVER** run raw git commands for pulling/rebasing. `git_sync.py` handles stashing, auto-resolution, and conflict mapping safely. |
