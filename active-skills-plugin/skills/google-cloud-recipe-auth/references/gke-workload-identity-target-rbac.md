# GKE Multi-Cluster Workload Identity & Target Cluster RBAC Mapping

When building multi-cluster GKE agent systems, an agent hosted on a central management cluster (e.g. `agent-cluster`) often needs to execute `gcloud` and `kubectl` operations against a target managed cluster.

This reference outlines the exact identity propagation mechanism and the required GCP IAM and Kubernetes RBAC configurations to make this work securely without static service account keys.

---

## 1. Identity Propagation Chain

When a pod in GKE Cluster A (host) runs a command targeting GKE Cluster B (target), the authentication and authorization flow behaves as follows:

```
[Agent Pod (Cluster A)]
       │
       │ (Workload Identity / GSA Token Exchange)
       ▼
[operator-agent-gsa (GCP IAM)]
       │
       ├── (gcloud container clusters get-credentials) ──▶ Generates Kubeconfig for Cluster B
       │
       ▼
[GKE Cluster B API Server]
       │
       │ (GKE IAM/OIDC Authenticator maps GCP Principal to k8s User)
       ▼
[Kubernetes User: operator-agent-gsa@PROJECT_ID.iam.gserviceaccount.com]
       │
       │ (ClusterRoleBinding / RoleBinding)
       ▼
[Target Cluster Role: e.g. view or edit]
```

1. **Host-Side Authentication (KSA ↔ GSA):** The host cluster's pod runs under a Kubernetes ServiceAccount (KSA) annotated with Workload Identity, mapping it to a GCP Service Account (GSA), e.g. `operator-agent-gsa`.
2. **GCP API Authentication (GSA ↔ GCP):** The GSA authenticates to GCP APIs. To run `gcloud container clusters get-credentials`, the GSA must hold project-level permissions to describe the target GKE cluster.
3. **Target-Side Mapping (GCP ↔ target k8s User):** GKE API servers automatically delegate authentication to GCP IAM via an internal OIDC/TokenAuthenticator. GKE maps the calling GSA's identity to a Kubernetes **`User`** principal whose name is the GSA's full email address:
   `operator-agent-gsa@PROJECT_ID.iam.gserviceaccount.com`
4. **Target-Side Authorization (k8s User ↔ RBAC):** To run `kubectl` against Cluster B, the target GKE cluster must have a `RoleBinding` or `ClusterRoleBinding` mapping that exact `User` email (NOT a ServiceAccount!) to a Kubernetes ClusterRole.

---

## 2. GCP IAM Configuration (SOP Remediation)

To execute cluster lifecycle modifications (such as upgrading the control plane or resizing node pools via GKE's regional APIs), the calling GSA needs GCP permissions beyond read-only visibility:

*   **`roles/container.developer`** is project-wide and allows reading/creating clusters and updating node pools, but **excludes GKE control plane modifications** (e.g., upgrading Kubernetes master versions).
*   **`roles/container.admin`** on the target cluster's project is required to successfully run:
    *   `gke_upgrade_cluster` (`gcloud container clusters upgrade`)
    *   `gke_resize_node_pool` (`gcloud container clusters resize`)

Verify/grant this on the GSA:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:operator-agent-gsa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.admin" \
  --condition=None --quiet
```

---

## 3. Target-Cluster RBAC Configuration

To authorize the operator's read/write `kubectl` actions on the target cluster, apply RBAC bindings targeting the GSA's email address as a **`User`** subject.

### Operator Scoped Read-Only ClusterRoleBinding
Operators primarily audit cluster configuration and node health. Since `gke_upgrade_cluster` and `gke_resize_node_pool` operate on GKE control plane APIs (outside the k8s resource space, guarded by GCP IAM), the operator's k8s API surface remains read-only. Map it to GKE's built-in `view` ClusterRole:

```yaml
# manifests/rbac/operator-target-rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: operator-agent-readonly
  labels:
    app.kubernetes.io/managed-by: kube-agents
    app.kubernetes.io/component: operator-target-rbac
    kube-agents.io/tier: operator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: view               # built-in: cluster-scoped read-only
subjects:
  - kind: User
    name: operator-agent-gsa@PROJECT_ID.iam.gserviceaccount.com
    apiGroup: rbac.authorization.k8s.io
```

### Devteam Scoped Read/Write RoleBinding
Devteam agents manage application workloads in a single namespace (e.g. `online-shop-ns`). To prevent cross-namespace privilege escalation, map the devteam GSA User to GKE's built-in namespace-scoped `edit` ClusterRole inside their assigned namespace only:

```yaml
# manifests/rbac/devteam-target-rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: devteam-agent-edit
  namespace: TARGET_NAMESPACE
  labels:
    app.kubernetes.io/managed-by: kube-agents
    app.kubernetes.io/component: devteam-target-rbac
    kube-agents.io/tier: devteam
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit               # built-in: namespace-scoped read/write
subjects:
  - kind: User
    name: devteam-agent-gsa@PROJECT_ID.iam.gserviceaccount.com
    apiGroup: rbac.authorization.k8s.io
```

---

## 4. Troubleshooting and Verification

If the agent pod encounters `Forbidden` or `Unauthorized` errors when calling target cluster resources:

1.  **Verify GSA Email Mapping:** Ensure the `kubectl` subject `name` matches the GSA's email exactly (any typo in the domain or project prefix breaks mapping).
2.  **Verify Kubernetes Subject Kind:** Ensure the `kind` in the target ClusterRoleBinding/RoleBinding is `User` (and `apiGroup` is `rbac.authorization.k8s.io`), **not `ServiceAccount`**.
3.  **Validate Token Generation:** Run a test command inside the host pod to confirm credential retrieval is functional:
    ```bash
    gcloud container clusters get-credentials <cluster> --region=<location> --project=<project>
    kubectl get nodes
    ```
4.  **Check Scope restrictions:** Legacy nodes may limit OAuth access scopes. Confirm GKE node pools have the `https://www.googleapis.com/auth/cloud-platform` access scope enabled so Workload Identity tokens can negotiate GKE APIs.
