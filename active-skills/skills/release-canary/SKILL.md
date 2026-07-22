---
name: release-canary
description: Temporary no-op skill used to verify the release pipeline end to end. Not for use; it is deleted immediately after the check.
disable-model-invocation: true
---

# release-canary

A throwaway skill that exists only to make a real change under `skills/`, so the
release pipeline can be exercised end to end:

1. `release.yml` patch-bumps **both** manifests (a `skills/**` change is runtime-neutral).
2. It tags `claude-v*` and `agy-v*` and cuts GitHub releases.
3. Its bump commit re-fires `notify-marketplace.yml`, which dispatches to `mlarkin00/plugins`.
4. That mirrors the change and restamps `marketplace.json` to the new Claude version.

This file is deleted as soon as those four steps are confirmed. If you are
reading it in an installed plugin, the cleanup push has not reached you yet —
ignore it.
