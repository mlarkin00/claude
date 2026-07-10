# GKE-Specific Best Practices

Read this file when the user's input involves GKE clusters, GKE node pools, GKE-specific APIs, or Google Cloud resources (VPCs, IAM, Cloud SQL, GCS, etc.) alongside Kubernetes config.

---

## Table of Contents

1. [Cluster Configuration](#1-cluster-configuration)
2. [Identity & Access](#2-identity--access)
3. [Node Pool Configuration](#3-node-pool-configuration)
4. [Networking (GKE)](#4-networking-gke)
5. [Security (GKE)](#5-security-gke)
6. [Autopilot vs Standard](#6-autopilot-vs-standard)
7. [Observability (GKE)](#7-observability-gke)
8. [Cost & Efficiency](#8-cost--efficiency)

---

## 1. Cluster Configuration

| Check                                       | Severity    | Details                                                                                                                                        |
| ------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Release channel set (not static version)    | 🟡 Warning  | Release channels (Regular, Stable, Rapid) automate patch upgrades. Static versions require manual upgrades and frequently fall behind on CVEs. |
| Cluster not running end-of-life version     | 🔴 Critical | EoL versions receive no security patches. Check current supported versions.                                                                    |
| Private cluster enabled                     | 🟡 Warning  | Public endpoint clusters expose the API server to the internet. Private clusters limit access to VPC-internal traffic.                         |
| Control plane authorized networks set       | 🟡 Warning  | If using a public endpoint, restrict it to known CIDR ranges.                                                                                  |
| Workload metadata protection enabled        | 🟡 Warning  | `metadata.concealment.enabled: true` prevents pods from reading node-level GCE metadata (including the node service account token).            |
| Cluster has at least 3 nodes across 3 zones | 🔴 Critical | Single-zone clusters lose workloads entirely during zonal outages. Regional clusters spread control plane and node pools across zones.         |
| Shielded nodes enabled                      | 🟡 Warning  | Shielded GKE Nodes use Secure Boot, vTPM, and Integrity Monitoring to protect against rootkit/bootkit attacks.                                 |
| Binary Authorization enabled                | 🟡 Warning  | Enforces that only cryptographically signed and approved images can be deployed. Critical for supply-chain security.                           |

---

## 2. Identity & Access

| Check                                               | Severity    | Details                                                                                                                                                                              |
| --------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Workload Identity enabled on cluster                | 🔴 Critical | Without Workload Identity, pods use the node's service account, which typically has broad GCP permissions. Workload Identity binds a Kubernetes SA to a GCP SA with least privilege. |
| No service account JSON keys mounted in pods        | 🔴 Critical | JSON keys are long-lived credentials. Workload Identity eliminates the need for them entirely.                                                                                       |
| Node pool service account is not default compute SA | 🟡 Warning  | The default Compute Engine SA has Editor role on the project — far too permissive for a GKE node. Create a dedicated, minimal node SA.                                               |
| GKE RBAC and GCP IAM are both configured            | 🟡 Warning  | GCP IAM controls who can call the GKE API; Kubernetes RBAC controls what they can do inside the cluster. Both layers are needed.                                                     |

**Example fix — Workload Identity annotation:**

```yaml
# Kubernetes ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app
  namespace: production
  annotations:
    iam.gke.io/gcp-service-account: my-app@my-project.iam.gserviceaccount.com
```

---

## 3. Node Pool Configuration

| Check                                                     | Severity      | Details                                                                                                                                                                    |
| --------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Node pools use auto-repair and auto-upgrade               | 🟡 Warning    | Auto-repair replaces unhealthy nodes automatically. Auto-upgrade keeps node versions current with the control plane.                                                       |
| Node pool has surge upgrade configured                    | 🔵 Suggestion | `max-surge-upgrade` and `max-unavailable-upgrade` control disruption during node pool upgrades. Default (1 surge, 0 unavailable) is conservative but slow for large pools. |
| Spot/Preemptible nodes only used with tolerations and PDB | 🟡 Warning    | Spot nodes are reclaimed with 30s notice. Use them only for fault-tolerant workloads with PDBs and appropriate tolerations.                                                |
| Node pool size matches workload demand                    | 🔵 Suggestion | Oversized fixed node pools waste money; undersized ones cause pending pods. Use Cluster Autoscaler with appropriate min/max bounds.                                        |
| Cluster Autoscaler enabled                                | 🟡 Warning    | Without CAS, the cluster cannot scale nodes to meet demand or shrink to save cost.                                                                                         |
| Node pool uses containerd runtime                         | 🔵 Suggestion | Docker-shim is deprecated. All GKE 1.24+ node pools default to containerd — verify no legacy config pins Docker.                                                           |
| Node taints match workload tolerations                    | 🟡 Warning    | Mismatched taints/tolerations cause pods to remain Pending indefinitely.                                                                                                   |

---

## 4. Networking (GKE)

| Check                                                                | Severity      | Details                                                                                                                                   |
| -------------------------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| VPC-native cluster (alias IP) enabled                                | 🟡 Warning    | Routes-based clusters are deprecated and do not support all GKE networking features (e.g., Network Policies via Dataplane V2, multi-NIC). |
| Dataplane V2 (eBPF) or Calico enabled for NetworkPolicy              | 🟡 Warning    | NetworkPolicy objects have no effect without a supported CNI. GKE's Dataplane V2 is the recommended default.                              |
| Services use Internal Load Balancer where external access not needed | 🟡 Warning    | External LBs are publicly accessible. Use `cloud.google.com/load-balancer-type: Internal` annotation for internal-only services.          |
| GKE Ingress or Gateway API used instead of raw LB Services           | 🔵 Suggestion | Ingress/Gateway manages TLS, routing, and health checks more efficiently than per-Service LBs.                                            |
| Cloud NAT used for egress from private nodes                         | 🔵 Suggestion | Private nodes have no public IP; without Cloud NAT they cannot reach external services (e.g., Docker Hub, external APIs).                 |

---

## 5. Security (GKE)

| Check                                                   | Severity      | Details                                                                                                                                 |
| ------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| GKE Security Posture scanning enabled                   | 🟡 Warning    | GKE Security Posture provides continuous vulnerability scanning for workloads and OS packages.                                          |
| Container-Optimized OS (COS) used as node OS            | 🟡 Warning    | COS is hardened, minimal, and maintained by Google. Ubuntu nodes have a larger attack surface.                                          |
| Audit logging enabled                                   | 🔴 Critical   | Without GKE audit logs forwarded to Cloud Logging, there is no forensic record of API calls (kubectl exec, pod creation, RBAC changes). |
| Secret Manager used for secrets (not K8s Secrets alone) | 🟡 Warning    | GKE integrates with Secret Manager via the Secrets Store CSI driver or ESO. Secrets in etcd should be encrypted at rest (CMEK).         |
| CMEK for etcd enabled                                   | 🟡 Warning    | Customer-Managed Encryption Keys for etcd ensure that GCP cannot decrypt secrets without your key.                                      |
| Intranode visibility enabled for VPC flow logs          | 🔵 Suggestion | Without intranode visibility, pod-to-pod traffic on the same node is invisible to VPC Flow Logs.                                        |

---

## 6. Autopilot vs Standard

**If the user is on GKE Autopilot, read `references/autopilot.md` now.** It covers Autopilot-specific blocked configs, resource floor requirements, compute classes, Secret Manager CSI, managed certs, KEDA, Workload Identity Federation for CI/CD, and the full mapping of which Standard checks still apply vs. can be skipped.

Quick reference for the most common Autopilot differences:

| Topic                  | Autopilot Behavior                                                            |
| ---------------------- | ----------------------------------------------------------------------------- |
| Resource requests      | Required + billed per pod — affects cost directly, not just scheduling.       |
| Node management        | Fully managed — node pool, OS, and autoscaler checks don't apply.             |
| Privileged containers  | Blocked at admission. Flag as Critical if present.                            |
| `hostPath` volumes     | Blocked. Suggest `emptyDir` or PVC.                                           |
| Custom DaemonSets      | Not supported. Use Deployments.                                               |
| `CAP_NET_RAW`          | Dropped by default. Flag if workload tries to re-add it.                      |
| Cluster Autoscaler     | Built-in — no manual config needed.                                           |
| Pod Security Standards | Autopilot enforces `baseline` by default; recommend `restricted` explicitly.  |
| Shielded nodes         | Always on — no user action needed.                                            |
| Billing model          | Per pod request, not per node — right-sizing requests has direct cost impact. |

---

## 7. Observability (GKE)

| Check                                                                            | Severity      | Details                                                                                                        |
| -------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------- |
| Google Cloud Managed Service for Prometheus (GMP) or kube-state-metrics deployed | 🔵 Suggestion | Without cluster-level metrics, there is no visibility into node pressure, pending pods, or scheduler behavior. |
| Cloud Logging integration enabled (system + workload logs)                       | 🟡 Warning    | GKE can export container logs automatically to Cloud Logging. Disabling this creates blind spots.              |
| GKE Dashboard / Fleet monitoring configured                                      | 🔵 Suggestion | Provides unified view across multiple clusters and workloads.                                                  |

---

## 8. Cost & Efficiency

| Check                                                         | Severity      | Details                                                                                                                    |
| ------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Vertical Pod Autoscaler (VPA) used to right-size requests     | 🔵 Suggestion | VPA in recommendation mode (not auto) helps identify over- or under-provisioned request values without risk of disruption. |
| Committed Use Discounts (CUDs) applied to baseline node count | 🔵 Suggestion | 1- or 3-year CUDs offer 37–55% savings on baseline capacity. Spot/Preemptible covers variable load.                        |
| Resource efficiency tracked (requests vs. actual usage)       | 🔵 Suggestion | High request-to-actual ratios mean wasted spend. Use GKE Cost Optimization insights or Kubecost.                           |
| Namespace-level cost labels present                           | 🔵 Suggestion | GCP billing labels on namespaces/nodes enable per-team cost attribution in Cloud Billing.                                  |
