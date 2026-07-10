---
name: auditing-k8s-config
description: Use when the user shares Kubernetes or GKE configuration (YAML manifests, Helm values, Terraform, or a description of their setup) and wants a review, audit, or recommendations for production-readiness, best practices, or hardening. Trigger on phrases like "review my k8s config", "is this production ready", "harden my deployment", "what's wrong with my yaml", "improve my GKE setup", "kubernetes best practices", or when the user pastes any Deployment/StatefulSet/Service/Pod manifest and asks for feedback. Also trigger when the user describes a Kubernetes architecture and asks whether it follows best practices.
---

# Auditing Kubernetes / GKE Configurations

This skill reviews user-provided Kubernetes or GKE configuration against production best practices and produces a prioritized, actionable report.

## Accepting Input

Accept any of these forms — never ask the user to reformat first:

- Raw YAML/JSON manifests (single resource or multi-document)
- Helm `values.yaml` or rendered templates
- Terraform HCL for GKE resources
- A written description of the cluster/workload setup
- A mix of the above

If the user's input is a description rather than concrete YAML, make reasonable inferences and flag where you'd need to see actual manifests to give a definitive verdict.

## Audit Workflow

1. **Parse and inventory** what resources are present (Deployment, Service, HPA, NetworkPolicy, etc.) and what is notably absent.
2. **Check each category** from the checklist in `references/checklist.md`. Read that file now — it contains the full list of checks with severity ratings.
3. **For GKE-specific inputs** (GKE cluster configs, Workload Identity, Binary Authorization, etc.), also read `references/gke-extras.md`.
4. **For GKE Autopilot inputs** (user mentions Autopilot, cluster is `mode: AUTOPILOT`, or they describe a fully-managed cluster), read `references/autopilot.md` instead of or in addition to `gke-extras.md`. Autopilot changes what's blocked, what's mandatory, and which Standard checks no longer apply.
5. **Produce the report** using the format below.

## Report Format

Always use this exact structure:

---

## Kubernetes Config Audit

### Summary

| Severity      | Count |
| ------------- | ----- |
| 🔴 Critical   | N     |
| 🟡 Warning    | N     |
| 🔵 Suggestion | N     |

**What was reviewed:** [list the resources/files analyzed]

---

### 🔴 Critical Findings

> Critical findings are misconfigurations that will cause outages, data loss, security breaches, or failed deployments under realistic production conditions.

#### [Finding title]

- **Resource:** `<kind>/<name>`
- **Issue:** What is wrong and why it matters in production.
- **Fix:**

```yaml
# Corrected snippet
```

_(repeat for each critical finding)_

---

### 🟡 Warnings

> Warnings are configurations that work but violate established best practices and will likely cause problems at scale or under failure conditions.

#### [Finding title]

- **Resource:** `<kind>/<name>`
- **Issue:** Brief explanation.
- **Fix:**

```yaml
# Corrected snippet
```

---

### 🔵 Suggestions

> Suggestions improve observability, cost efficiency, or operational maturity. Not urgent, but worth addressing before going to production.

#### [Finding title]

- **Resource:** `<kind>/<name>`
- **Issue:** Brief explanation.
- **Fix:**

```yaml
# Corrected snippet
```

---

### What Looks Good ✅

List things the user is already doing correctly. This section matters — it builds trust and tells the user what not to change.

---

### Next Steps

Ordered list of the 3–5 highest-priority actions to take first.

---

## Severity Guide

Use these criteria consistently:

| Severity      | Criteria                                                                                                                   |
| ------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 🔴 Critical   | Single point of failure, privilege escalation risk, OOMKill guaranteed, no health probes, `latest` image tag in production |
| 🟡 Warning    | No resource limits, no PDB, no anti-affinity, missing network policies, service account with excessive permissions         |
| 🔵 Suggestion | No topology spread, suboptimal QoS class, missing annotations/labels, no HPA, hardcoded secrets in env vars                |

When in doubt, escalate severity — it is better to over-flag and let the user decide.

## Output Tone

- Be direct and specific. "Add `resources.limits`" is better than "consider adding resource limits."
- Always show a corrected YAML snippet, not just a description of the fix.
- Keep finding titles short and scannable (≤ 8 words).
- Never pad with generic Kubernetes background — the user wants findings, not a tutorial.

## Gotchas & Anti-Patterns

| Rationalization                                             | Reality                                                                                                            |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| "They didn't share the whole manifest, so I'll skip checks" | Make inferences from what's present; flag what can't be verified. Partial input is normal.                         |
| "This is a dev config, production rules don't apply"        | Unless the user explicitly says it's dev-only, audit for production. Dev configs become production configs.        |
| "The image tag issue is minor"                              | `latest` tags are Critical — they break reproducibility and can silently pull breaking changes.                    |
| "They're on GKE so security is handled"                     | GKE provides defaults, not guarantees. Pod security, RBAC, and network policies still need explicit configuration. |
| "No NetworkPolicy means open — that might be fine"          | Default-allow is a Warning at minimum; flag it every time.                                                         |
| "Resource limits might slow down the app"                   | Unconstrained containers cause noisy-neighbor evictions. Flag missing limits as Warning, explain the tradeoff.     |
| "I'll skip the ✅ section to save space"                    | The "What Looks Good" section is not optional — omitting it leaves users unsure what to keep.                      |
