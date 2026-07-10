# Kubernetes Best-Practices Checklist

This is the full audit checklist. Work through every category for each resource reviewed. Skip checks that are not applicable to the resource type (e.g., PDB checks don't apply to a single-replica Job).

---

## Table of Contents

1. [Workload Configuration](#1-workload-configuration)
2. [Resource Management](#2-resource-management)
3. [Health Probes](#3-health-probes)
4. [Security Context](#4-security-context)
5. [RBAC & Service Accounts](#5-rbac--service-accounts)
6. [Networking](#6-networking)
7. [Reliability & Availability](#7-reliability--availability)
8. [Observability & Labels](#8-observability--labels)
9. [Images & Supply Chain](#9-images--supply-chain)
10. [Namespace Hygiene](#10-namespace-hygiene)
11. [Secrets Management](#11-secrets-management)

---

## 1. Workload Configuration

| Check                                          | Severity      | Details                                                                                                |
| ---------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------ |
| No naked Pods                                  | 🔴 Critical   | Pods without a controller (Deployment/StatefulSet/DaemonSet) will not reschedule after node failure.   |
| Use Deployment for stateless apps              | 🔴 Critical   | Provides rolling updates, replica management, and rollback.                                            |
| Use StatefulSet for stateful apps              | 🔴 Critical   | Required for stable network identity and ordered deployment.                                           |
| `replicas ≥ 2` in production                   | 🔴 Critical   | Single-replica workloads have zero tolerance for node failure or rolling update disruption.            |
| `strategy.type: RollingUpdate`                 | 🟡 Warning    | `Recreate` causes downtime. Use `RollingUpdate` unless the app cannot run two versions simultaneously. |
| `maxUnavailable: 0` during rollout             | 🟡 Warning    | Without this, rolling updates can temporarily reduce capacity below acceptable levels.                 |
| `maxSurge` set appropriately                   | 🔵 Suggestion | Default (25%) is fine; set explicitly for clarity and to match capacity budget.                        |
| `progressDeadlineSeconds` set                  | 🔵 Suggestion | Without a deadline, a stuck rollout never surfaces as failed. 600s is a reasonable default.            |
| `revisionHistoryLimit` set                     | 🔵 Suggestion | Default 10 is fine; tune down for very large deployments to save etcd space.                           |
| Jobs use `restartPolicy: Never` or `OnFailure` | 🟡 Warning    | `Always` is invalid for Jobs and causes unexpected behavior.                                           |
| CronJobs set `concurrencyPolicy`               | 🟡 Warning    | Without `Forbid` or `Replace`, long-running jobs stack and exhaust resources.                          |

---

## 2. Resource Management

| Check                                              | Severity      | Details                                                                                                                           |
| -------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `resources.requests.cpu` set on every container    | 🔴 Critical   | Without requests, the scheduler cannot place pods correctly; workloads starve or evict.                                           |
| `resources.requests.memory` set on every container | 🔴 Critical   | Same as CPU — required for correct scheduling and eviction ordering.                                                              |
| `resources.limits.memory` set                      | 🟡 Warning    | Without memory limits, one container can OOM the node and evict unrelated pods.                                                   |
| `resources.limits.cpu` set (with nuance)           | 🔵 Suggestion | CPU limits cause throttling; consider setting them for tenant isolation but not for latency-sensitive apps. Explain the tradeoff. |
| Requests and limits are proportionate              | 🟡 Warning    | Limits more than 4× requests inflates the scheduling footprint vs. actual usage.                                                  |
| QoS class is appropriate for criticality           | 🔵 Suggestion | Critical workloads should target `Guaranteed` QoS (requests = limits). `BestEffort` (no requests/limits) is evicted first.        |
| LimitRange defined in namespace                    | 🟡 Warning    | Without LimitRange defaults, containers without explicit requests get BestEffort QoS.                                             |
| ResourceQuota defined in namespace                 | 🟡 Warning    | Without quotas, a single runaway workload can exhaust the entire cluster.                                                         |
| CPU values use milliCPU notation                   | 🔵 Suggestion | `500m` is clearer than `0.5`; `0.001` is below the minimum precision — use `1m`.                                                  |

**Example fix — resource block:**

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    memory: "512Mi" # omit cpu limit for latency-sensitive apps
```

---

## 3. Health Probes

| Check                                              | Severity      | Details                                                                                                                                   |
| -------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `readinessProbe` defined                           | 🔴 Critical   | Without a readiness probe, traffic is sent to pods that are still initializing. This causes errors at every deployment.                   |
| `livenessProbe` defined                            | 🟡 Warning    | Without a liveness probe, deadlocked pods stay in `Running` state and receive traffic forever.                                            |
| `startupProbe` for slow-starting containers        | 🟡 Warning    | Without a startup probe, a slow app triggers liveness restarts before it finishes booting.                                                |
| Probes use HTTP or gRPC, not `exec` for hot paths  | 🔵 Suggestion | `exec` probes spawn a process per check; under high replica counts this is expensive.                                                     |
| `initialDelaySeconds` accounts for startup time    | 🟡 Warning    | Too short: premature restarts. Too long: slow failure detection. Tune to actual p95 startup time.                                         |
| Liveness probe is not identical to readiness probe | 🟡 Warning    | Liveness probes should check "is the app alive", not "is it ready for traffic". Using the same endpoint conflates two different concerns. |
| Probe `failureThreshold` set                       | 🔵 Suggestion | Default (3) is fine; increase for bursty apps that have transient slowdowns.                                                              |

**Example fix — probes:**

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30
  periodSeconds: 5
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 10
```

---

## 4. Security Context

| Check                                        | Severity    | Details                                                                                                                  |
| -------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| `privileged: true` absent                    | 🔴 Critical | Privileged containers have full host access — equivalent to root on the node.                                            |
| `allowPrivilegeEscalation: false`            | 🔴 Critical | Prevents a process from gaining more privileges than its parent. Should be set on every container.                       |
| `runAsNonRoot: true`                         | 🔴 Critical | Running as root inside a container is dangerous if container escape occurs.                                              |
| `runAsUser` is non-zero                      | 🔴 Critical | UID 0 is root; use a non-zero UID (e.g., 1000).                                                                          |
| `capabilities.drop: [ALL]`                   | 🟡 Warning  | Containers start with a default capability set. Drop all, then add back only what's needed.                              |
| `capabilities.add` is minimal                | 🟡 Warning  | Adding `NET_ADMIN`, `SYS_ADMIN`, etc. significantly increases attack surface.                                            |
| `readOnlyRootFilesystem: true`               | 🟡 Warning  | Prevents runtime writes to the container filesystem; forces explicit volume mounts for writable paths.                   |
| `hostNetwork: false`                         | 🔴 Critical | `hostNetwork: true` exposes all node network interfaces to the container.                                                |
| `hostPID: false`                             | 🔴 Critical | `hostPID: true` lets the container see all processes on the node.                                                        |
| `hostIPC: false`                             | 🔴 Critical | `hostIPC: true` allows shared memory access to all IPC namespaces on the node.                                           |
| `hostPath` volumes absent                    | 🟡 Warning  | hostPath mounts the node filesystem; a misconfigured mount can expose sensitive host files.                              |
| Pod Security Standard label set on namespace | 🟡 Warning  | Without PSS labels, no admission enforcement occurs. Use `pod-security.kubernetes.io/enforce: restricted` or `baseline`. |
| Seccomp profile set                          | 🟡 Warning  | Without a seccomp profile, the container can make any syscall. Use `RuntimeDefault` or a custom profile.                 |

**Example fix — security context:**

```yaml
securityContext: # pod-level
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 2000
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    securityContext: # container-level
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
```

**Namespace PSS label:**

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## 5. RBAC & Service Accounts

| Check                                                  | Severity    | Details                                                                                                             |
| ------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------- |
| Dedicated ServiceAccount per workload                  | 🟡 Warning  | Using the `default` SA for multiple workloads means a single SA compromise affects all of them.                     |
| `automountServiceAccountToken: false` where not needed | 🟡 Warning  | If the app doesn't talk to the API server, mounting the token is unnecessary attack surface.                        |
| Roles use least privilege                              | 🟡 Warning  | Avoid `*` verbs or resources. Grant exactly what the workload needs.                                                |
| No ClusterRole when a Role suffices                    | 🟡 Warning  | Namespace-scoped roles limit blast radius.                                                                          |
| No wildcard in `resources` or `verbs`                  | 🔴 Critical | `resources: ["*"]` + `verbs: ["*"]` is effectively cluster admin.                                                   |
| ServiceAccount is not cluster-admin                    | 🔴 Critical | Binding a workload SA to cluster-admin is a privilege escalation vector.                                            |
| GKE: Workload Identity used instead of node SA keys    | 🟡 Warning  | (GKE-specific) Service account JSON keys mounted in pods are a credential leak risk. Use Workload Identity instead. |

---

## 6. Networking

| Check                                                 | Severity      | Details                                                                              |
| ----------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------ |
| `hostPort` not used                                   | 🟡 Warning    | `hostPort` pins pods to specific nodes and breaks scheduling. Use a Service instead. |
| `hostNetwork: false`                                  | 🔴 Critical   | (also in security — listed here for networking completeness)                         |
| NetworkPolicy defined (ingress)                       | 🟡 Warning    | Default-allow means any pod in the cluster can reach this workload.                  |
| NetworkPolicy defined (egress)                        | 🔵 Suggestion | Egress policies limit blast radius if a pod is compromised.                          |
| Default-deny NetworkPolicy exists in namespace        | 🟡 Warning    | Without a baseline deny policy, all newly created pods are open by default.          |
| Services use DNS names, not hardcoded IPs             | 🔵 Suggestion | IP addresses change; DNS names are stable.                                           |
| LoadBalancer Services have `loadBalancerSourceRanges` | 🟡 Warning    | Without source ranges, the LB is open to the internet.                               |
| Ingress has TLS configured                            | 🟡 Warning    | Plain HTTP in production exposes traffic to interception.                            |

**Example fix — default-deny NetworkPolicy:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

---

## 7. Reliability & Availability

| Check                                                   | Severity      | Details                                                                                                            |
| ------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| PodDisruptionBudget defined                             | 🟡 Warning    | Without a PDB, cluster upgrades or node drains can take down all replicas simultaneously.                          |
| PDB `minAvailable` ≥ 1 (or `maxUnavailable` < replicas) | 🔴 Critical   | A PDB that allows zero available pods defeats its purpose.                                                         |
| Pod anti-affinity or topology spread constraints        | 🟡 Warning    | Without these, all replicas may land on the same node. A single node failure removes the entire workload.          |
| HPA defined for variable-load workloads                 | 🔵 Suggestion | Fixed replica counts waste resources during low traffic and fail under spikes.                                     |
| HPA min replicas ≥ 2                                    | 🟡 Warning    | HPA scaling to 1 replica loses high availability.                                                                  |
| HPA and VPA not both managing the same resource         | 🔴 Critical   | Concurrent HPA (CPU-based) + VPA (request-based) fights can cause oscillation and OOM kills.                       |
| `terminationGracePeriodSeconds` is adequate             | 🟡 Warning    | Too short (or 0) forces hard kills mid-request. Default (30s) is usually fine; tune to actual drain time.          |
| `preStop` hook for graceful shutdown                    | 🔵 Suggestion | Kubernetes sends SIGTERM and routes traffic simultaneously; a short `sleep` in preStop gives the LB time to drain. |
| Pod priority class set for critical workloads           | 🔵 Suggestion | Without PriorityClass, critical workloads can be evicted by low-priority batch jobs under resource pressure.       |

**Example fix — PDB + anti-affinity:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: my-app
---
# In Deployment pod spec:
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: my-app
          topologyKey: kubernetes.io/hostname
```

---

## 8. Observability & Labels

| Check                                       | Severity      | Details                                                                                                                                                                                                                       |
| ------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Standard labels present                     | 🔵 Suggestion | `app.kubernetes.io/name`, `app.kubernetes.io/version`, `app.kubernetes.io/component`, `app.kubernetes.io/part-of` are the Kubernetes recommended label set. They enable tooling (dashboards, selectors) to work consistently. |
| `environment` label present                 | 🔵 Suggestion | Enables cost attribution and policy targeting (e.g., `env: production`).                                                                                                                                                      |
| Annotations include `description`           | 🔵 Suggestion | `kubernetes.io/description` improves discoverability in `kubectl describe`.                                                                                                                                                   |
| Prometheus scrape annotations or PodMonitor | 🔵 Suggestion | Without scrape config, the workload is invisible to cluster-level monitoring.                                                                                                                                                 |
| Structured logging (JSON)                   | 🔵 Suggestion | Unstructured logs are hard to query in Cloud Logging / Loki. Recommend JSON output.                                                                                                                                           |

**Example fix — recommended labels:**

```yaml
metadata:
  labels:
    app.kubernetes.io/name: my-app
    app.kubernetes.io/version: "1.4.2"
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: my-platform
    environment: production
```

---

## 9. Images & Supply Chain

| Check                                             | Severity    | Details                                                                                                                                |
| ------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| No `latest` image tag                             | 🔴 Critical | `latest` is not pinned — a pull after a new push silently changes what's running. Breaks reproducibility and rollback.                 |
| Image tag is a digest or semantic version         | 🟡 Warning  | Semver tags can be mutated. SHA digest (`image:sha256-...`) is fully immutable.                                                        |
| `imagePullPolicy: Always` not used without digest | 🟡 Warning  | `Always` causes unnecessary registry traffic and can fail deployments if the registry is down. Use `IfNotPresent` with immutable tags. |
| Image comes from a trusted registry               | 🟡 Warning  | Pulling from Docker Hub or arbitrary registries bypasses image scanning. Use a private registry with vulnerability scanning.           |
| No `command` or `args` injection from env vars    | 🟡 Warning  | Constructing commands from user-supplied env vars risks command injection.                                                             |

---

## 10. Namespace Hygiene

| Check                                             | Severity    | Details                                                                                               |
| ------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------- |
| Workloads not in `default` namespace              | 🟡 Warning  | `default` has no RBAC isolation or resource quotas. Use dedicated namespaces per team or environment. |
| Namespace has ResourceQuota                       | 🟡 Warning  | (see Resource Management)                                                                             |
| Namespace has LimitRange                          | 🟡 Warning  | (see Resource Management)                                                                             |
| Namespaces are not shared across trust boundaries | 🔴 Critical | Different teams or tenants sharing a namespace share RBAC, quotas, and NetworkPolicies.               |

---

## 11. Secrets Management

| Check                                                                  | Severity      | Details                                                                                                                                            |
| ---------------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Secrets not hardcoded in `env.value`                                   | 🔴 Critical   | Literal secret values in manifests end up in version control and etcd in plaintext.                                                                |
| Secrets use `secretKeyRef`, not `configMapKeyRef` for sensitive values | 🔴 Critical   | ConfigMaps are not encrypted at rest by default.                                                                                                   |
| Secrets not stored in image layers                                     | 🔴 Critical   | Image layers are inspectable; never bake secrets into images.                                                                                      |
| External secrets manager used (ESO, Vault, GCP Secret Manager)         | 🔵 Suggestion | Kubernetes Secrets are base64-encoded (not encrypted) by default. An external secrets operator with encryption at rest is the production standard. |
| `etcd` encryption at rest enabled                                      | 🟡 Warning    | (Cluster-level) Without encryption-at-rest, Secret data in etcd is stored in plaintext.                                                            |

**Example fix — correct secret reference:**

```yaml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password
```
