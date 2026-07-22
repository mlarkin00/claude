#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///

import argparse
import json
import os
import re
import subprocess
import sys

def run_cmd(cmd, cwd=None, check=True):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if check and res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, cmd, res.stdout, res.stderr)
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except Exception as e:
        if check:
            raise e
        return "", str(e), -1

def is_git(cwd):
    _, _, code = run_cmd("git rev-parse --is-inside-work-tree", cwd=cwd, check=False)
    return code == 0

def get_status(cwd):
    if not is_git(cwd):
        return {"is_git": False}

    branch, _, _ = run_cmd("git symbolic-ref --short HEAD", cwd=cwd, check=False)
    if not branch:
        # Check if detached HEAD
        branch, _, _ = run_cmd("git rev-parse --short HEAD", cwd=cwd, check=False)
        branch = f"Detached HEAD ({branch})"

    # Check tracking branch
    upstream, _, _ = run_cmd("git rev-parse --abbrev-ref @{u}", cwd=cwd, check=False)
    
    # Check if working tree is clean
    status_out, _, _ = run_cmd("git status --porcelain", cwd=cwd, check=False)
    is_clean = len(status_out.strip()) == 0

    behind = 0
    ahead = 0
    if upstream:
        try:
            behind_out, _, _ = run_cmd(f"git rev-list --count HEAD..{upstream}", cwd=cwd)
            behind = int(behind_out) if behind_out else 0
            ahead_out, _, _ = run_cmd(f"git rev-list --count {upstream}..HEAD", cwd=cwd)
            ahead = int(ahead_out) if ahead_out else 0
        except Exception:
            pass

    return {
        "is_git": True,
        "branch": branch,
        "upstream": upstream,
        "is_clean": is_clean,
        "behind": behind,
        "ahead": ahead
    }

def parse_conflicts(filepath):
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Find conflict markers using regex
    # Matches <<<<<<< [label] \n [ours] \n ======= \n [theirs] \n >>>>>>> [label]
    pattern = re.compile(
        r'^<<<<<<< (.*?)\n(.*?)^=======\n(.*?)^>>>>>>> (.*?)(?:\n|$)',
        re.MULTILINE | re.DOTALL
    )

    conflicts = []
    matches = list(pattern.finditer(content))
    
    # We also need to map line numbers
    lines = content.splitlines(keepends=True)
    
    for idx, m in enumerate(matches):
        start_char = m.start()
        # count lines before start_char
        lines_before = content[:start_char].count('\n') + 1
        
        label_a = m.group(1).strip()
        side_a = m.group(2)
        side_b = m.group(3)
        label_b = m.group(4).strip()
        
        conflicts.append({
            "id": idx,
            "start_line": lines_before,
            "label_a": label_a,
            "label_b": label_b,
            "side_a_preview": side_a.splitlines()[:10], # preview first 10 lines
            "side_b_preview": side_b.splitlines()[:10],
            "side_a_full": side_a,
            "side_b_full": side_b,
        })
    return conflicts

def resolve_hunks_in_file(filepath, choice_map, op_type):
    """
    choice_map is a dict of hunk_id -> 'local' | 'remote'
    op_type is 'rebase' or 'merge'
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    pattern = re.compile(
        r'^<<<<<<< (.*?)\n(.*?)^=======\n(.*?)^>>>>>>> (.*?)(?:\n|$)',
        re.MULTILINE | re.DOTALL
    )

    matches = list(pattern.finditer(content))
    if not matches:
        return False

    new_content = ""
    last_end = 0
    
    for idx, m in enumerate(matches):
        new_content += content[last_end:m.start()]
        
        # Decide which side to keep
        choice = choice_map.get(idx) or choice_map.get(str(idx))
        if not choice:
            # If no choice is specified for this hunk, keep the conflict markers intact
            new_content += m.group(0)
        else:
            # Map 'local' / 'remote' to side_a / side_b based on op_type
            # In both rebase and merge, side_a is HEAD (the first block)
            # In rebase: HEAD is remote (upstream), so side_a is remote, side_b is local.
            # In merge: HEAD is local, so side_a is local, side_b is remote.
            if op_type == "rebase":
                keep_side = m.group(3) if choice == "local" else m.group(2)
            else: # merge
                keep_side = m.group(2) if choice == "local" else m.group(3)
            new_content += keep_side
            
        last_end = m.end()
        
    new_content += content[last_end:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    return True

def auto_resolve_all_conflicts(cwd, op_type, preference):
    """
    Finds all conflicted files and automatically resolves all their hunks to local or remote.
    """
    conflicted_files = get_conflicted_files(cwd)
    for file in conflicted_files:
        filepath = os.path.join(cwd, file)
        hunks = parse_conflicts(filepath)
        if not hunks:
            raise Exception(f"Git reported conflict on {file} but parser found no conflict markers")
        choice_map = {h["id"]: preference for h in hunks}
        resolve_hunks_in_file(filepath, choice_map, op_type)
        
        # Verify that all conflict markers are gone
        remaining = parse_conflicts(filepath)
        if remaining:
            raise Exception(f"Failed to resolve all conflict markers in {file}")
            
        run_cmd(f"git add {file}", cwd=cwd)

def pop_stash_and_resolve(cwd, prefer, stashed=True):
    """
    Safely pops the stash. If a conflict occurs, auto-resolves it if prefer is local or remote.
    Returns: (success_bool, message, was_resolved)
    """
    if not stashed:
        return True, "No stash to restore", False
        
    stdout, stderr, code = run_cmd("git stash pop", cwd=cwd, check=False)
    if code == 0:
        return True, "Stash popped cleanly", False
        
    # Check if there are conflicted files
    conflicted = get_conflicted_files(cwd)
    if not conflicted:
        # Some other pop error (e.g. no stash)
        return False, f"Failed to pop stash: {stderr}", False
        
    if prefer in ["local", "remote"]:
        try:
            # Stash pop conflict markers are oriented like rebase (HEAD = remote, Stash = local)
            auto_resolve_all_conflicts(cwd, "rebase", prefer)
            # Since resolved, stage the files
            for f in conflicted:
                run_cmd(f"git add {f}", cwd=cwd)
            # Drop the stash since git stash pop doesn't drop on conflict
            run_cmd("git stash drop", cwd=cwd)
            return True, f"Stash pop conflicted but was auto-resolved keeping '{prefer}'", True
        except Exception as e:
            return False, f"Failed to auto-resolve stash pop conflicts: {str(e)}", False
            
    # Interactive conflict
    return False, "Stash pop resulted in conflicts. Please resolve them interactively.", False

def get_conflicted_files(cwd):
    out, _, _ = run_cmd("git diff --name-only --diff-filter=U", cwd=cwd, check=False)
    return [f.strip() for f in out.splitlines() if f.strip()]

def check_active_rebase_or_merge(cwd):
    # Check if rebase in progress
    if os.path.exists(os.path.join(cwd, ".git", "rebase-merge")) or os.path.exists(os.path.join(cwd, ".git", "rebase-apply")):
        return "rebase"
    # Check if merge in progress
    if os.path.exists(os.path.join(cwd, ".git", "MERGE_HEAD")):
        return "merge"
    return None

def main():
    parser = argparse.ArgumentParser(description="Git Sync Helper Script")
    parser.add_argument("--cwd", default=".", help="Working directory")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing them")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # status command
    subparsers.add_parser("status", help="Get git repository sync status")
    
    # sync command
    sync_parser = subparsers.add_parser("sync", help="Synchronize with remote")
    sync_parser.add_argument("--mode", choices=["rebase", "merge"], default="rebase", help="Sync method")
    sync_parser.add_argument("--no-stash", action="store_true", help="Disable automatic stashing")
    sync_parser.add_argument("--prefer", choices=["local", "remote", "interactive"], default="interactive", help="Conflict resolution preference")
    
    # resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve conflicts in a file")
    resolve_parser.add_argument("--file", required=True, help="Conflicted file path")
    resolve_parser.add_argument("--choice", choices=["local", "remote"], help="Resolve all hunks in file to local/remote")
    resolve_parser.add_argument("--hunk-choices", help="JSON map of hunk ID to local/remote (e.g. '{\"0\": \"local\", \"1\": \"remote\"}')")
    
    # continue command
    continue_parser = subparsers.add_parser("continue", help="Continue current rebase or merge")
    continue_parser.add_argument("--prefer", choices=["local", "remote", "interactive"], default="interactive", help="Conflict resolution preference")
    
    # abort command
    subparsers.add_parser("abort", help="Abort current rebase or merge")
    
    args = parser.parse_args()
    cwd = args.cwd

    if args.command == "status":
        status_info = get_status(cwd)
        print(json.dumps(status_info, indent=2))
        return

    if args.command == "sync":
        if not is_git(cwd):
            print(json.dumps({"error": "Not a git repository"}, indent=2))
            sys.exit(1)
            
        status_info = get_status(cwd)
        if not status_info["upstream"]:
            # Attempt to set upstream to origin/branch
            branch = status_info["branch"]
            # Check if origin has this branch
            _, _, code = run_cmd(f"git rev-parse origin/{branch}", cwd=cwd, check=False)
            if code == 0:
                if not args.dry_run:
                    run_cmd(f"git branch --set-upstream-to=origin/{branch} {branch}", cwd=cwd)
                status_info = get_status(cwd)
            else:
                print(json.dumps({"error": "No remote tracking branch configured and origin branch not found"}, indent=2))
                sys.exit(1)

        # Handle stashing if not clean
        stashed = False
        if not status_info["is_clean"] and not args.no_stash:
            if args.dry_run:
                print(f"[dry-run] Stashing uncommitted changes")
            else:
                out, _, _ = run_cmd("git stash save -u 'git-sync: auto-stash before sync'", cwd=cwd)
                if "Saved working directory" in out:
                    stashed = True
            
        # Fetch latest
        if args.dry_run:
            print("[dry-run] git fetch")
        else:
            run_cmd("git fetch", cwd=cwd)
            
        # Recalculate divergence
        status_info = get_status(cwd)
        behind = status_info["behind"]
        ahead = status_info["ahead"]
        
        if behind == 0:
            # Local is up-to-date or ahead
            stash_success = True
            stash_msg = ""
            if stashed and not args.dry_run:
                stash_success, stash_msg, _ = pop_stash_and_resolve(cwd, args.prefer, stashed)
            if stash_success:
                print(json.dumps({
                    "status": "success",
                    "message": "Already up to date with remote",
                    "stashed": stashed,
                    "ahead": ahead,
                    "behind": behind
                }, indent=2))
            else:
                conflicted_files = get_conflicted_files(cwd)
                conflicts_data = {}
                for f in conflicted_files:
                    filepath = os.path.join(cwd, f)
                    conflicts_data[f] = parse_conflicts(filepath)
                print(json.dumps({
                    "status": "conflict",
                    "op_type": "stash",
                    "stashed": stashed,
                    "conflicted_files": conflicted_files,
                    "conflicts": conflicts_data
                }, indent=2))
            return
            
        # We are behind. Perform sync
        op_type = args.mode
        sync_cmd = f"git rebase @{{u}}" if op_type == "rebase" else f"git merge @{{u}}"
        
        if args.dry_run:
            print(f"[dry-run] {sync_cmd}")
            return
            
        # Run sync command
        stdout, stderr, code = run_cmd(sync_cmd, cwd=cwd, check=False)
        
        if code == 0:
            # Success! Pop stash if stashed
            stash_success = True
            stash_msg = ""
            if stashed:
                stash_success, stash_msg, _ = pop_stash_and_resolve(cwd, args.prefer, stashed)
            if stash_success:
                print(json.dumps({
                    "status": "success",
                    "message": "Successfully synchronized with remote branch",
                    "stashed": stashed,
                    "op_type": op_type
                }, indent=2))
            else:
                # Stash pop conflict
                conflicted_files = get_conflicted_files(cwd)
                conflicts_data = {}
                for f in conflicted_files:
                    filepath = os.path.join(cwd, f)
                    conflicts_data[f] = parse_conflicts(filepath)
                print(json.dumps({
                    "status": "conflict",
                    "op_type": "stash",
                    "stashed": stashed,
                    "conflicted_files": conflicted_files,
                    "conflicts": conflicts_data
                }, indent=2))
            return
            
        # Conflict occurred!
        # Check active operation type
        active_op = check_active_rebase_or_merge(cwd)
        if not active_op:
            active_op = op_type
            
        if args.prefer in ["local", "remote"]:
            # Auto-resolve conflicts
            try:
                auto_resolve_all_conflicts(cwd, active_op, args.prefer)
                # Continue rebase/merge
                cont_cmd = "git rebase --continue" if active_op == "rebase" else "git commit --no-edit"
                # For rebase continue, git might open editor or require GIT_EDITOR=cat
                # Let's set GIT_EDITOR=cat
                stdout, stderr, code = run_cmd(f"GIT_EDITOR=cat {cont_cmd}", cwd=cwd, check=False)
                if code == 0:
                    stash_success = True
                    stash_msg = ""
                    if stashed:
                        stash_success, stash_msg, _ = pop_stash_and_resolve(cwd, args.prefer, stashed)
                    if stash_success:
                        print(json.dumps({
                            "status": "success",
                            "message": f"Conflicts auto-resolved using preference '{args.prefer}'",
                            "stashed": stashed,
                            "op_type": active_op
                        }, indent=2))
                    else:
                        conflicted_files = get_conflicted_files(cwd)
                        conflicts_data = {}
                        for f in conflicted_files:
                            filepath = os.path.join(cwd, f)
                            conflicts_data[f] = parse_conflicts(filepath)
                        print(json.dumps({
                            "status": "conflict",
                            "op_type": "stash",
                            "stashed": stashed,
                            "conflicted_files": conflicted_files,
                            "conflicts": conflicts_data
                        }, indent=2))
                    return
            except Exception as e:
                pass
                
        # If interactive or auto-resolve failed, collect conflict details
        conflicted_files = get_conflicted_files(cwd)
        conflicts_data = {}
        for f in conflicted_files:
            filepath = os.path.join(cwd, f)
            conflicts_data[f] = parse_conflicts(filepath)
            
        print(json.dumps({
            "status": "conflict",
            "op_type": active_op,
            "stashed": stashed,
            "conflicted_files": conflicted_files,
            "conflicts": conflicts_data
        }, indent=2))
        return

    if args.command == "resolve":
        if args.dry_run:
            print(f"[dry-run] Resolving conflicts in {args.file}")
            return
            
        op_type = check_active_rebase_or_merge(cwd)
        if not op_type:
            # If no active rebase or merge, see if we have conflicted files (e.g. from stash pop)
            if get_conflicted_files(cwd):
                op_type = "rebase"  # Stash pop conflicts use rebase orientation mapping
            else:
                print(json.dumps({"error": "No active rebase, merge, or stash pop in progress"}, indent=2))
                sys.exit(1)
            
        filepath = os.path.join(cwd, args.file)
        if not os.path.exists(filepath):
            print(json.dumps({"error": f"File {args.file} not found"}, indent=2))
            sys.exit(1)
            
        if args.choice:
            hunks = parse_conflicts(filepath)
            choice_map = {h["id"]: args.choice for h in hunks}
            resolved = resolve_hunks_in_file(filepath, choice_map, op_type)
        elif args.hunk_choices:
            try:
                choice_map = json.loads(args.hunk_choices)
                resolved = resolve_hunks_in_file(filepath, choice_map, op_type)
            except Exception as e:
                print(json.dumps({"error": f"Invalid hunk choices JSON: {str(e)}"}, indent=2))
                sys.exit(1)
        else:
            print(json.dumps({"error": "Must specify either --choice or --hunk-choices"}, indent=2))
            sys.exit(1)
            
        # Add to git
        if resolved:
            run_cmd(f"git add {args.file}", cwd=cwd)
            
        print(json.dumps({
            "status": "success",
            "file": args.file,
            "remaining_conflicts": len(get_conflicted_files(cwd))
        }, indent=2))
        return

    if args.command == "continue":
        op_type = check_active_rebase_or_merge(cwd)
        if not op_type:
            # Check if we are continuing from a resolved stash pop conflict
            stash_list, _, _ = run_cmd("git stash list", cwd=cwd, check=False)
            stashed = "git-sync: auto-stash" in stash_list
            if stashed:
                conflicted_files = get_conflicted_files(cwd)
                if not conflicted_files:
                    # All conflicts resolved! We can drop the stash and complete.
                    run_cmd("git stash drop", cwd=cwd)
                    print(json.dumps({
                        "status": "success",
                        "message": "Successfully resolved stash conflicts and completed sync.",
                        "stashed": True
                    }, indent=2))
                else:
                    conflicts_data = {}
                    for f in conflicted_files:
                        filepath = os.path.join(cwd, f)
                        conflicts_data[f] = parse_conflicts(filepath)
                    print(json.dumps({
                        "status": "conflict",
                        "op_type": "stash",
                        "message": "Continue failed. Still have unresolved stash conflicts.",
                        "conflicted_files": conflicted_files,
                        "conflicts": conflicts_data
                    }, indent=2))
                return
            else:
                print(json.dumps({"error": "No active rebase, merge, or stash pop in progress"}, indent=2))
                sys.exit(1)
                
        # We are in rebase/merge. Auto-resolve conflicts first if prefer is set
        if args.prefer in ["local", "remote"]:
            try:
                auto_resolve_all_conflicts(cwd, op_type, args.prefer)
            except Exception:
                pass
                
        cont_cmd = "git rebase --continue" if op_type == "rebase" else "git commit --no-edit"
        stdout, stderr, code = run_cmd(f"GIT_EDITOR=cat {cont_cmd}", cwd=cwd, check=False)
        
        if code == 0:
            # Check if we stashed earlier (we can look at stash list if it has our signature)
            stash_list, _, _ = run_cmd("git stash list", cwd=cwd, check=False)
            stashed = "git-sync: auto-stash" in stash_list
            stash_success = True
            stash_msg = ""
            if stashed:
                stash_success, stash_msg, _ = pop_stash_and_resolve(cwd, args.prefer, stashed)
            if stash_success:
                print(json.dumps({
                    "status": "success",
                    "message": f"Successfully continued and completed {op_type}",
                    "stashed": stashed
                }, indent=2))
            else:
                conflicted_files = get_conflicted_files(cwd)
                conflicts_data = {}
                for f in conflicted_files:
                    filepath = os.path.join(cwd, f)
                    conflicts_data[f] = parse_conflicts(filepath)
                print(json.dumps({
                    "status": "conflict",
                    "op_type": "stash",
                    "stashed": stashed,
                    "conflicted_files": conflicted_files,
                    "conflicts": conflicts_data
                }, indent=2))
        else:
            # Still in conflict or other error
            conflicted_files = get_conflicted_files(cwd)
            conflicts_data = {}
            for f in conflicted_files:
                filepath = os.path.join(cwd, f)
                conflicts_data[f] = parse_conflicts(filepath)
            print(json.dumps({
                "status": "conflict",
                "op_type": op_type,
                "message": "Continue failed. Still have unresolved conflicts.",
                "conflicted_files": conflicted_files,
                "conflicts": conflicts_data
            }, indent=2))
        return

    if args.command == "abort":
        op_type = check_active_rebase_or_merge(cwd)
        if not op_type:
            print(json.dumps({"error": "No active rebase or merge in progress"}, indent=2))
            sys.exit(1)
            
        abort_cmd = "git rebase --abort" if op_type == "rebase" else "git merge --abort"
        run_cmd(abort_cmd, cwd=cwd)
        
        # Pop stash if we did one
        stash_list, _, _ = run_cmd("git stash list", cwd=cwd, check=False)
        stashed = False
        if "git-sync: auto-stash" in stash_list:
            run_cmd("git stash pop", cwd=cwd, check=False)
            stashed = True
            
        print(json.dumps({
            "status": "aborted",
            "message": f"Aborted active {op_type} and restored state.",
            "stashed": stashed
        }, indent=2))
        return

if __name__ == "__main__":
    main()
