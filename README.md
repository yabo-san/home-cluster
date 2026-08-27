# home-cluster

> GitOps-driven single-node **k3s** homelab — every piece of cluster state lives in this repo and is reconciled by **Flux CD**.
> Identity is centralized through **Keycloak** (OIDC SSO), services are exposed publicly via **Cloudflare Tunnels** (no inbound ports), secrets are **SOPS/age**-encrypted at rest, and observability is defined **as code**.

---

## Live Services

| Service | URL | Auth | Notes |
|---|---|---|---|
| **Grafana** | `monitoring.y4bo.com` | Keycloak OIDC (SSO) | kube-prometheus-stack; dashboards as code; email alerts via SMTP |
| **Keycloak** | `id.y4bo.com` | — (the IdP) | Postgres-backed; realm `y4bo` imported as code; realm-scoped admin console at `/admin/y4bo/console` |
| **Portal** | `login.y4bo.com` | Keycloak OIDC (via oauth2-proxy) | Homepage tile launcher for the hub |

Each service reaches the internet through its own `cloudflared` tunnel — nothing is exposed by opening a firewall port.

---

## Identity & SSO

Keycloak is the single identity provider. The `y4bo` realm is **imported declaratively** on boot (`--import-realm`) and defines:

- **OIDC clients:** `grafana`, `portal`
- **Realm roles:** `grafana-admin`, `grafana-editor`, `sysadmin`, `user`
- **Realm-scoped admins** via the `realm-management` `realm-admin` role — so day-to-day admin happens as a normal SSO user, not the master bootstrap account.

Grafana maps Keycloak realm roles → Grafana roles (`grafana-admin` → Admin). The portal is gated by **oauth2-proxy**, which bounces unauthenticated users to Keycloak before the tiles ever load.

---

## Repository Structure

```
home-cluster/
├── clusters/staging/              # Flux entrypoint — bootstraps all Kustomizations
│   ├── apps.yaml / infrastructure.yaml / monitoring.yaml / storage.yaml
│   ├── .sops.yaml                 # age recipients for secret encryption
│   └── flux-system/
├── apps/
│   ├── base/
│   │   ├── grafana-tunnel/        # cloudflared → Grafana (monitoring.y4bo.com)
│   │   └── portal/                # Homepage + oauth2-proxy + tunnel (login.y4bo.com)
│   └── staging/                   # overlays + SOPS-encrypted tunnel/secret configs
├── infrastructure/
│   ├── controllers/base/
│   │   ├── keycloak/              # Keycloak + Postgres + tunnel + realm import
│   │   └── renovate/              # in-cluster Renovate CronJob
│   └── storage/{base,longhorn}/   # media PV + Longhorn HelmRelease/StorageClass
└── monitoring/
    ├── controllers/               # kube-prometheus-stack HelmRelease (Grafana OIDC + SMTP)
    └── configs/kube-prometheus-stack/
        ├── grafana-{tls,admin,oidc,smtp}-secret.yaml   # SOPS-encrypted
        └── dashboards/            # dashboards as sidecar-loaded ConfigMaps
```

_(Deprecated apps — `audiobookshelf`, `linkding` — remain under `apps/base` but are commented out of the staging kustomization; audiobookshelf now lives on a separate NixOS host.)_

---

## Secret Management

Secrets are encrypted at rest with **[SOPS](https://github.com/getsops/sops)** + **[age](https://github.com/FiloSottile/age)**. `.sops.yaml` encrypts only `data`/`stringData` fields, so the rest of each manifest stays reviewable in diffs. Flux decrypts at reconcile time using the `sops-age` secret in `flux-system`.

Encryption uses **two age recipients** so a push can never produce an undecryptable secret. Encrypt before committing (config lives in `clusters/staging/`):

```bash
sops --config clusters/staging/.sops.yaml --encrypt --in-place path/to/secret.yaml
```

**Never commit an unencrypted secret.**

---

## Observability (as code)

**kube-prometheus-stack** (`v66.2.2`) provides Prometheus, Grafana, and Alertmanager. Everything is version-controlled:

- **Dashboards** are `grafana_dashboard=1`-labeled ConfigMaps, auto-loaded by the Grafana sidecar — add a `.json`, list it in the kustomization, push.
- **Alerting** rides the bundled Prometheus rules (node/filesystem/RAID health, etc.); notifications go out over **SMTP** to email.
- Grafana login is **Keycloak OIDC**, with a SOPS-encrypted admin account as break-glass.

> _Note: this is single-node k3s, so the control-plane component dashboards (scheduler/controller-manager/kube-proxy/etcd) show "No data" by design — k3s bundles those into one binary without separate metrics endpoints._

---

## Access

The cluster is reached over **Tailscale** (`kubectl`/`k9s` against the tailnet IP; the k3s cert SAN includes it). Public service access is via the Cloudflare Tunnels above — no VPN required for end users.

---

## Planned / In Progress

- [ ] Role-based portal tiles (OneLogin-style — render tiles from the user's Keycloak roles)
- [ ] Self-service onboarding (email signup → admin approval → auto-grant media access)
- [ ] Extend monitoring onto the NixOS host (node_exporter → Prometheus scrape)
- [ ] Federate Jellyfin/Seerr into Keycloak SSO
- [ ] Overseerr · Kavita · Romm · LinuxGSM
- [ ] Second cluster node (RAM headroom / HA)
- [ ] YAMS → [Preparr migration](https://robbeverhelst.github.io/Preparr/deployment/helm/)
- [ ] [Stirling-pdf](https://docs.stirlingpdf.com/Installation/Kubernetes%20Install)

## Sources

- [k3s on ubuntu](https://www.digitalocean.com/community/tutorials/how-to-setup-k3s-kubernetes-cluster-on-ubuntu)
- [SOPS with age encryption in fluxCD](https://fluxcd.io/flux/guides/mozilla-sops/#encrypting-secrets-using-age)
- [longhorn on fluxCD](https://oneuptime.com/blog/post/2026-03-06-deploy-longhorn-storage-flux-cd/view)
- [fluxCD monorepo](https://fluxcd.io/flux/guides/repository-structure/#monorepo)
