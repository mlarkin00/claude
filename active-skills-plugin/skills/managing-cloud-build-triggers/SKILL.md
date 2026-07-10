---
name: managing-cloud-build-triggers
description: Use when creating, updating, or managing Google Cloud Build triggers. This skill handles 1st Gen and 2nd Gen GitHub connections, branch patterns, and mandatory IAM validation.
---

# Managing Cloud Build Triggers

Manage the end-to-end lifecycle of Google Cloud Build triggers with absolute technical rigor.

## Core Mandate: The Connection Rule

**Never attempt to create a trigger without first verifying the repository connection.**

- **Symptoms:** User provides a repository URL and asks for a trigger "immediately."
- **Rationalization:** "I'll skip the connection check to hit the deadline." — **FORBIDDEN.**
- **Action:** You MUST run `gcloud builds connections list` (2nd Gen) or verify mirroring (1st Gen) before drafting the command.

## Step-by-Step Commands

### 1. Verify Connection (Mandatory)

Before creating a trigger, identify the connection:

```bash
# List all 2nd Gen connections and their regions
gcloud builds connections list --region=[LOCATION]
```

### 2. Verify IAM Permissions

Ensure the caller has `roles/cloudbuild.builds.editor`:

```bash
gcloud projects get-iam-policy [PROJECT_ID] \
    --flatten="bindings[].members" \
    --format='table(bindings.role)' \
    --filter="bindings.members:user:[YOUR_EMAIL]"
```

### 3. Create Trigger (GitHub 2nd Gen)

Use the `repository` resource type. Triggers MUST specify a service account.

```bash
gcloud builds triggers create repository \
    --name="[TRIGGER_NAME]" \
    --repository="projects/[PROJECT_ID]/locations/[LOCATION]/connections/[CONNECTION_NAME]/repositories/[REPO_NAME]" \
    --branch-pattern="^[BRANCH_NAME]$" \
    --build-config="[PATH_TO_YAML]" \
    --substitutions="_VAR=VALUE" \
    --service-account="projects/[PROJECT_ID]/serviceAccounts/[SA_EMAIL]" \
    --region=[LOCATION]
```

## Critical Placement Rules

- **Regex Patterns:** Always use RE2 syntax (e.g., `^main$` instead of `main`).
- **Service Accounts:** Triggers IGNORE the service account inside the build config YAML. You MUST define it in the trigger command.
- **Regions:** 2nd Gen triggers are regional. Ensure the connection, repository, and trigger regions match.

## No Exceptions Table

| Excuse                                | Reality                                                                                                        |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| "User said don't worry about IAM"     | Skipping IAM leads to "Permission Denied" failures that waste context turns.                                   |
| "I'll use a placeholder for [REGION]" | Placeholders prevent the user from running the command. Use `gcloud compute regions list` to find the default. |
| "This is a simple 1st Gen mirror"     | Mirrored repos are deprecated. Always recommend 2nd Gen connections for new triggers.                          |

## The Arc

After drafting the trigger command, suggest the next logical step:
"I have verified the connection and drafted the command. Would you like me to run it now and then trigger a manual test build?"

## Accessibility

Add this to your global stylesheet for reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  ::view-transition-old(*),
  ::view-transition-new(*),
  ::view-transition-group(*) {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
  }
}
```
