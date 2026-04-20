# home-cluster

> GitOps-driven Kubernetes homelab running on a single-node k3s cluster.
> Managed by [Flux CD](https://fluxcd.io/) with SOPS-encrypted secrets, Kustomize overlays, Longhorn persistent storage, and Cloudflare Tunnel ingress.

---

## Cluster Overview

| Component | Details |
|---|---|
| **Distribution** | k3s |
| **GitOps** | Flux CD v2.8.5 |
| **Storage** | Longhorn |
| **Observability** | kube-prometheus-stack (Prometheus + Grafana) |
| **Secret Management** | SOPS + age |
| **Ingress** | Cloudflare Tunnel |
| **Dependency Updates** | Renovate (in-cluster CronJob, hourly) |

---

## Repository Structure

```
home-cluster/
├── clusters/
│   └── staging/              # Flux entrypoint — bootstraps all Kustomizations
│       ├── apps.yaml
│       ├── infrastructure.yaml
│       ├── monitoring.yaml
│       ├── storage.yaml
│       └── flux-system/
├── apps/
│   ├── base/                 # Base Kubernetes manifests per app
│   │   ├── audiobookshelf/
│   │   └── linkding/
│   └── staging/              # Staging overlays + secrets + Cloudflare tunnel configs
│       ├── audiobookshelf/
│       └── linkding/
├── infrastructure/
│   ├── controllers/
│   │   └── base/renovate/    # In-cluster Renovate CronJob
│   └── storage/
│       ├── base/             # Shared PVs (NFS media mount)
│       └── longhorn/         # Longhorn HelmRelease + StorageClass + recurring snapshots
└── monitoring/
    ├── controllers/          # kube-prometheus-stack HelmRelease
    └── configs/              # Grafana TLS secret, alerting configs
```

---

## Apps

### [Linkding](https://github.com/sissbruecker/linkding)
Self-hosted bookmark manager. Accessible externally via Cloudflare Tunnel.

- **Image:** `sissbruecker/linkding:1.45.0`
- **Storage:** Longhorn-backed PVC
- **Secrets:** SOPS-encrypted env secret via Flux

### [Audiobookshelf](https://www.audiobookshelf.org/)
Self-hosted audiobook and podcast server.

- **Image:** `ghcr.io/advplyr/audiobookshelf:2.33.1`
- **Storage:** Config and metadata on Longhorn PVCs; audiobook library on NFS host mount (`/mnt/media/audiobooks`)
- **Ingress:** Cloudflare Tunnel
- **Timezone:** `America/Los_Angeles`

---

## Storage

Longhorn is the primary StorageClass (`longhorn` default, `longhorn-retain` for stateful workloads requiring reclaim on deletion).

The `longhorn-retain` class is configured with:
- 3 volume replicas
- `best-effort` data locality
- `ext4` filesystem
- Daily automated snapshots via Longhorn recurring jobs

A static PV (`media-pv`) maps the host's NFS media share into the cluster for media library access.

---

## Secret Management

Secrets are encrypted at rest using [SOPS](https://github.com/getsops/sops) with an [age](https://github.com/FiloSottile/age) key.

The `.sops.yaml` config encrypts only `data` and `stringData` fields in YAML files, keeping the rest of the manifest readable. Flux decrypts secrets at reconciliation time using a `sops-age` Kubernetes Secret in the `flux-system` namespace.

**Never commit unencrypted secrets.** Encrypt before pushing:

```bash
sops --encrypt --in-place path/to/secret.yaml
```

---

## Observability

[kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) (`v66.2.2`) provides:

- Prometheus for metrics collection
- Grafana for dashboards (TLS-terminated)
- Alertmanager for alerting

Longhorn exposes a ServiceMonitor so storage metrics are scraped automatically.

---

## Dependency Management

[Renovate](https://docs.renovatebot.com/) runs in-cluster as a CronJob on an hourly schedule. It watches all `.yaml` files for image tags and Helm chart versions and opens PRs to keep dependencies current.

Config: [`renovate.json`](./renovate.json)

---

## Flux Reconciliation

The cluster entrypoint is `clusters/staging/`. Flux watches this path and reconciles all child Kustomizations from there. Reconciliation intervals:

| Kustomization | Interval |
|---|---|
| apps | 1m |
| infrastructure-controllers | 1m |
| infrastructure-storage | 1m |
| monitoring | 1m |
| longhorn | 10m |

To manually trigger reconciliation:

```bash
flux reconcile kustomization flux-system --with-source
```

To check status across all Kustomizations:

```bash
flux get kustomizations
flux get helmreleases -A
```

---

## Prerequisites

- k3s installed on target node
- Flux CLI (`flux`)
- SOPS + age key configured locally
- `kubectl` with kubeconfig pointed at the cluster
- Cloudflare account with Tunnel credentials

---

## Bootstrap

```bash
flux bootstrap github \
  --owner=yabo-san \
  --repository=home-cluster \
  --branch=main \
  --path=clusters/staging \
  --personal
```

After bootstrap, create the SOPS age secret:

```bash
kubectl create secret generic sops-age \
  --namespace=flux-system \
  --from-file=age.agekey=/path/to/age.key
```

---

## Planned / In Progress

- [ ] Overseer
- [ ] Kavita
- [ ] Romm
- [ ] LinuxGSM
- [ ] [Protonmail bridge using traefik](https://rossjr.dev/blog/proton-bridge-tailscale/)
- [ ] Second cluster node (RAM expansion)
- [ ] YAMS to [Preparr migration
](https://robbeverhelst.github.io/Preparr/deployment/helm/)
## Sources

- [k3s on ubuntu](https://www.digitalocean.com/community/tutorials/how-to-setup-k3s-kubernetes-cluster-on-ubuntu)
- [SOPS with age encryption in fluxCD](https://fluxcd.io/flux/guides/mozilla-sops/#encrypting-secrets-using-age)
- [longhorn on fluxCD](https://oneuptime.com/blog/post/2026-03-06-deploy-longhorn-storage-flux-cd/view)
- [fluxCD monorepo](https://fluxcd.io/flux/guides/repository-structure/#monorepo)
