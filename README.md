# home-cluster

GitOps k3s cluster on two nodes, reconciled by **Flux CD** from this repo. Single sign-on through
**Keycloak** on an **LLDAP** directory, public access through **Cloudflare Tunnels** (no inbound
ports), secrets encrypted with **SOPS/age**, monitoring as code.

## Services

| App | Who can open it |
|---|---|
| Portal (Keycloak account theme) | every user; shows only the apps their groups allow |
| Keycloak | the identity provider, federated to LLDAP |
| LLDAP admin | `platform-admin`, then LLDAP's own login |
| Grafana | `platform-admin` |
| RomM | group `roms` |
| Drop | group `games` |

Accounts exist only in LLDAP; there is no self sign-up. Groups decide which apps a user can open.

## Layout

```
clusters/staging/          Flux entrypoint (infrastructure, apps, monitoring Kustomizations)
infrastructure/            Keycloak + Postgres, Renovate, storage classes
apps/base, apps/staging    one folder per app; staging holds SOPS-encrypted secrets
monitoring/                kube-prometheus-stack, Loki, Tempo, blackbox, OpenTelemetry Operator,
                           alert rules and dashboards as code
docs/runbooks/             step-by-step procedures
```

Features are switched off by commenting out their line in a `kustomization.yaml`, not by deleting files.

## Monitoring

- **Metrics:** Prometheus scrapes nodes, pods, four database exporters and the tunnels.
- **Logs:** Promtail to Loki.
- **Traces / APM:** OpenTelemetry (built in or injected by the operator) to Tempo, which derives
  per-service rate, errors and latency for the APM dashboards.
- **Alerts:** rules written for failures this cluster has actually had, routed by Alertmanager to
  email, plus a dead man's switch to healthchecks.io so a dead cluster still pages.

## Secrets

Only `data` / `stringData` are encrypted, so diffs stay reviewable. Flux decrypts with the `sops-age`
key in `flux-system`.

```bash
sops --encrypt --in-place path/to/secret.yaml
```
