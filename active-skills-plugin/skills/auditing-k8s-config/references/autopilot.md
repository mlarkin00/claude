# GKE Autopilot Best Practices

Read this file when the user's input involves GKE Autopilot specifically — either because they mention Autopilot, or because their cluster config shows `mode: AUTOPILOT` / they describe a fully-managed cluster where they can't SSH into nodes.

Autopilot shifts the shared responsibility model: Google manages nodes, OS patching, and baseline security. The developer is responsible for workload manifests. Most audit findings change character on Autopilot — some Standard checks become irrelevant, others become mandatory, and new Autopilot-native best practices apply.

---

## Table of Contents

1. [What Autopilot Enforces (No Config Needed)](#1-what-autopilot-enforces-no-config-needed)
2. [What Autopilot Blocks (Flag if Present)](#2-what-autopilot-blocks-flag-if-present)
3. [Resource Requests & QoS on Autopilot](#3-resource-requests--qos-on-autopilot)
4. [Compute Classes](#4-compute-classes)
5. [Identity & Secrets](#5-identity--secrets)
6. [Networking & Ingress](#6-networking--ingress)
7. [Observability](#7-observability)
8. [Scaling](#8-scaling)
9. [CI/CD & Image Supply Chain](#9-cicd--image-supply-chain)

---

## 1. What Autopilot Enforces (No Config Needed)

These are handled by the platform — flag them as "Already Handled by Autopilot ✅" rather than recommendations:

| Feature                   | Detail                                                                                                                                                                        |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shielded nodes            | All Autopilot nodes use Secure Boot, vTPM, and Integrity Monitoring. No user config needed.                                                                                   |
| OS patching               | Google SREs manage node OS updates within user-defined maintenance windows.                                                                                                   |
| Baseline Pod Security     | Autopilot enforces the `baseline` Pod Security Standard by default. Pods violating it are rejected.                                                                           |
| Node autoscaling          | Autopilot provisions and deprovisions nodes automatically as pods are scheduled.                                                                                              |
| CAP_NET_RAW dropped       | This capability is removed from all containers by default to prevent network spoofing. If a workload requests it, flag as a Warning unless there is a documented requirement. |
| CAP_NET_ADMIN dropped     | Administrative network operations are blocked cluster-wide.                                                                                                                   |
| SLA covers pod scheduling | Unlike Standard (control-plane SLA only), Autopilot's SLA covers pod capacity and scheduling.                                                                                 |

---

## 2. What Autopilot Blocks (Flag if Present)

These configurations are rejected by Autopilot's admission controller. Flag as 🔴 Critical if found — the workload will not deploy:

| Check                            | Severity    | Why                                                                                                                                                  |
| -------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `privileged: true`               | 🔴 Critical | Blocked by Autopilot. Container will be rejected at admission.                                                                                       |
| `hostPath` volumes               | 🔴 Critical | Blocked. Use `emptyDir`, `configMap`, `secret`, or PVC instead.                                                                                      |
| `hostNetwork: true`              | 🔴 Critical | Blocked.                                                                                                                                             |
| `hostPID: true`                  | 🔴 Critical | Blocked.                                                                                                                                             |
| `hostIPC: true`                  | 🔴 Critical | Blocked.                                                                                                                                             |
| Custom DaemonSets                | 🔴 Critical | User-defined DaemonSets are not supported. Use Deployments or work with the GKE team for node-level concerns.                                        |
| SSH access to nodes              | N/A         | Not possible — flag if user is asking about this to clarify the model.                                                                               |
| `runAsUser: 0` / root containers | 🟡 Warning  | Autopilot enforces `baseline` PSS which blocks this under `restricted`. Proactively flag; it may work on `baseline` but is still a security concern. |

**Example fix — hostPath replaced with emptyDir:**

```yaml
volumes:
  - name: tmp
    emptyDir: {} # use instead of hostPath: /tmp
```

---

## 3. Resource Requests & QoS on Autopilot

Resource management behaves differently on Autopilot than Standard:

| Check                                       | Severity      | Detail                                                                                                                                                                                                                                                                             |
| ------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `resources.requests` set on every container | 🔴 Critical   | Autopilot auto-assigns defaults if absent — but this means uncontrolled cost. Explicit requests are mandatory for predictable billing.                                                                                                                                             |
| CPU request ≥ 250m per container            | 🟡 Warning    | Autopilot enforces a resource floor. Requests below the minimum (typically ~250m CPU, ~512Mi memory) are silently adjusted upward. Flag unrealistically small values as a Warning with an explanation that the billed amount will be higher than requested.                        |
| Memory request set alongside CPU request    | 🔴 Critical   | CPU-only or memory-only requests are not valid on Autopilot — both must be specified together.                                                                                                                                                                                     |
| `limits` set appropriately for QoS class    | 🟡 Warning    | **Guaranteed QoS** (requests = limits): reserved exclusively for the pod — ideal for latency-sensitive or critical services. **Burstable QoS** (limits > requests or limits unset): pod can burst into unused node capacity — ideal for variable web traffic. Choose deliberately. |
| No `limits.cpu` set for Burstable workloads | 🔵 Suggestion | On Autopilot, omitting CPU limits allows bursting. This is often desirable and intentional — note it rather than flagging it as an error.                                                                                                                                          |

**Example — Guaranteed QoS (critical service):**

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "500m" # equal to request = Guaranteed QoS
    memory: "512Mi"
```

**Example — Burstable QoS (web app):**

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    memory: "512Mi" # no cpu limit = burstable; pod can use spare CPU cycles
```

---

## 4. Compute Classes

Autopilot exposes specialized hardware via **Compute Classes** requested through `nodeSelector` or `nodeAffinity`. Flag missing compute class config as a Suggestion when the workload clearly needs non-default hardware:

| Compute Class          | Use Case                                                                                   | How to Request                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **Balanced** (default) | General-purpose, balanced CPU/memory ratio                                                 | No annotation needed — it's the default.                           |
| **Scale-Out**          | High-throughput stateless microservices (Arm/AMD, SMT disabled = 1 vCPU = 1 physical core) | `cloud.google.com/compute-class: scale-out`                        |
| **Accelerator**        | AI/ML workloads needing GPU (T4, L4, A100)                                                 | `resource.limits: nvidia.com/gpu: "1"` + appropriate node selector |

**Example — Scale-Out compute class:**

```yaml
spec:
  nodeSelector:
    cloud.google.com/compute-class: scale-out
  containers:
    - name: app
      resources:
        requests:
          cpu: "2"
          memory: "4Gi"
```

**Example — GPU accelerator:**

```yaml
spec:
  containers:
    - name: trainer
      resources:
        limits:
          nvidia.com/gpu: "1"
        requests:
          cpu: "4"
          memory: "16Gi"
```

---

## 5. Identity & Secrets

| Check                                                | Severity      | Detail                                                                                                                                                                                                           |
| ---------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workload Identity enabled and used                   | 🔴 Critical   | On Autopilot, Workload Identity is the only correct way to grant GCP API access. JSON service account keys mounted as secrets are a credential leak risk and are unnecessary.                                    |
| KSA annotated with GCP service account               | 🟡 Warning    | Without the `iam.gke.io/gcp-service-account` annotation, the KSA cannot impersonate a GSA. The pod silently falls back to no GCP credentials.                                                                    |
| Secret Manager CSI Driver used for sensitive secrets | 🟡 Warning    | Kubernetes Secrets (in etcd) are base64-encoded. Secret Manager CSI mounts secrets as in-memory tmpfs volumes and supports automatic rotation. Prefer this for any secret that rotates or requires audit trails. |
| Raw K8s Secrets only as a compatibility fallback     | 🔵 Suggestion | If the app needs env vars and can't use volume mounts, the CSI driver's `secretObjects` sync is acceptable — note that synced secrets are removed when the pod is deleted.                                       |
| No static JSON service account key files in pods     | 🔴 Critical   | Keys are long-lived and unrevocable without manual rotation. Workload Identity eliminates the need for them.                                                                                                     |

**Example — Workload Identity KSA:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: production
  annotations:
    iam.gke.io/gcp-service-account: my-app@MY_PROJECT.iam.gserviceaccount.com
```

**Example — Secret Manager CSI mount:**

```yaml
volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: my-app-secrets
```

---

## 6. Networking & Ingress

| Check                                                        | Severity   | Detail                                                                                                                                                                                                                          |
| ------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GKE Ingress (class `gce`) used for external traffic          | 🟡 Warning | GKE Ingress provisions a Global Application Load Balancer with Container-Native Load Balancing (NEGs). This routes traffic directly to Pod IPs, removing node hops and improving latency vs raw NodePort/LoadBalancer Services. |
| `ManagedCertificate` resource used for TLS                   | 🟡 Warning | Without managed certs, TLS requires manual cert provisioning and rotation. `ManagedCertificate` automates provisioning and renewal — zero-touch.                                                                                |
| Internal-only services use Internal Load Balancer annotation | 🟡 Warning | External LBs are internet-accessible. Add `cloud.google.com/load-balancer-type: Internal` for services that should not be public.                                                                                               |
| NetworkPolicy enforced via Dataplane V2                      | 🟡 Warning | Autopilot uses Dataplane V2 (eBPF) by default, which supports NetworkPolicy. Still flag if no NetworkPolicy resources exist — the CNI supports them but they must be created explicitly.                                        |

**Example — GKE Ingress with managed cert:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: "gce"
    networking.gke.io/managed-certificates: my-managed-cert
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
---
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: my-managed-cert
spec:
  domains:
    - api.example.com
```

---

## 7. Observability

| Check                                           | Severity      | Detail                                                                                                                                                                                       |
| ----------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Google Managed Prometheus (GMP) configured      | 🟡 Warning    | GMP is enabled by default on Autopilot. Use `PodMonitoring` CRDs (not legacy Prometheus scrape annotations) to configure scraping — this integrates with GMP's collector DaemonSet.          |
| Cloud Logging integration active                | 🔵 Suggestion | Autopilot exports system and workload logs by default. Verify `--logging=SYSTEM,WORKLOAD` is set and logs are reaching Cloud Logging.                                                        |
| Liveness, readiness, and startup probes defined | 🔴 Critical   | Autopilot defaults are robust but probes must be explicit. Without them, pods receive traffic before they're ready and failed pods are not restarted. (Same as Standard — applies here too.) |

**Example — PodMonitoring for GMP:**

```yaml
apiVersion: monitoring.googleapis.com/v1
kind: PodMonitoring
metadata:
  name: my-app
  namespace: production
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
    - port: metrics
      interval: 30s
```

---

## 8. Scaling

| Check                                              | Severity      | Detail                                                                                                                                                                                                          |
| -------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HPA configured for variable-load workloads         | 🟡 Warning    | Fixed replica counts on Autopilot waste money (billed per pod request) or fail under spikes. HPA is especially important on Autopilot because of the per-pod billing model.                                     |
| HPA minimum replicas ≥ 2                           | 🟡 Warning    | HPA scaling to 1 loses high availability.                                                                                                                                                                       |
| KEDA used for event-driven / queue-based workloads | 🔵 Suggestion | CPU-based HPA is a lagging indicator for queue-driven work. KEDA scales on external signals (Pub/Sub queue depth, Cloud Tasks, etc.) and supports scale-to-zero — a powerful cost saver for sporadic workloads. |
| PodDisruptionBudget defined                        | 🟡 Warning    | Autopilot manages node lifecycle including drains. PDBs protect against involuntary disruptions during node upgrades — still needed on Autopilot.                                                               |

**Example — KEDA ScaledObject for Pub/Sub:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: pubsub-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: my-worker
  minReplicaCount: 0 # scale to zero when queue is empty
  maxReplicaCount: 20
  triggers:
    - type: gcp-pubsub
      metadata:
        subscriptionName: my-subscription
        value: "5" # scale up when >5 messages pending
```

---

## 9. CI/CD & Image Supply Chain

These checks apply when the user shares pipeline configs (GitHub Actions, Cloud Build, etc.) alongside Kubernetes manifests:

| Check                                                   | Severity      | Detail                                                                                                                                                                                                                |
| ------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workload Identity Federation used for CI/CD auth        | 🔴 Critical   | Static JSON service account keys in CI/CD (GitHub Actions secrets, etc.) are long-lived and high-risk. WIF issues ephemeral OIDC-based tokens that expire after the job — no keys to rotate or leak.                  |
| Images built with Cloud Native Buildpacks or equivalent | 🔵 Suggestion | Buildpacks (`gcloud builds submit --pack`) produce distroless/minimal images without a Dockerfile. This reduces attack surface (no shell, no package manager in the image) and automates OS patching via rebasing.    |
| Image tag is pinned (not `latest`)                      | 🔴 Critical   | Same as Standard — `latest` breaks reproducibility. Use semver or SHA digest.                                                                                                                                         |
| `gcloudignore` / `.dockerignore` present                | 🔵 Suggestion | Without an ignore file, the entire working directory (including git history, test data, `.env` files) is uploaded to Cloud Build. This slows builds and risks including sensitive files.                              |
| CI/CD pipeline stages: auth → build → deploy            | 🔵 Suggestion | The canonical Autopilot pipeline: (1) `google-github-actions/auth` with WIF, (2) `gcloud builds submit --pack`, (3) `google-github-actions/deploy-gke`. Each stage is decoupled and uses least-privilege credentials. |

**Example — WIF in GitHub Actions:**

```yaml
jobs:
  deploy:
    permissions:
      id-token: write # required for WIF OIDC token
      contents: read
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/PROJECT_NUM/locations/global/workloadIdentityPools/POOL/providers/PROVIDER
          service_account: deployer@MY_PROJECT.iam.gserviceaccount.com
      - run: gcloud builds submit --pack image=us-docker.pkg.dev/MY_PROJECT/repo/app:${{ github.sha }}
```

---

## Autopilot vs Standard: Which Checks Still Apply

When auditing an Autopilot cluster, suppress or reclassify these Standard checks:

| Standard Check                   | On Autopilot                                                            |
| -------------------------------- | ----------------------------------------------------------------------- |
| Node pool auto-repair/upgrade    | ✅ Handled — skip                                                       |
| Shielded nodes                   | ✅ Enforced — skip                                                      |
| OS selection (COS vs Ubuntu)     | ✅ Managed by Google — skip                                             |
| Cluster Autoscaler configuration | ✅ Built-in — skip                                                      |
| Node pool service account        | ✅ Still relevant — check for dedicated minimal SA                      |
| Pod Security Standards           | ✅ `baseline` enforced — still recommend `restricted` explicitly        |
| Workload Identity                | 🔴 Still required — Autopilot doesn't configure WIF bindings for you    |
| NetworkPolicy                    | 🟡 Still required — Dataplane V2 supports them but they must be created |
| Resource requests                | 🔴 More critical than Standard — affects billing directly               |
