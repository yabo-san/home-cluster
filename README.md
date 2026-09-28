# home-cluster

A self-hosted, open-source take on the SSO and observability I used in production (OneLogin, New Relic):

- **SSO:** Keycloak on an LLDAP directory, with a custom portal theme built in GitHub Actions and pinned by digest from GHCR
- **Observability:** the LGTM stack with Prometheus in place of Mimir (Loki, Grafana, Tempo), OpenTelemetry for traces and APM
- **Platform:** k3s managed with Flux CD, public apps behind Cloudflare Tunnels, secrets encrypted with SOPS + age, dependency updates by Renovate

## Apps and how each is monitored

Every app gets container metrics, logs and restart/OOM alerts. Beyond that:

| App | Uptime probe | APM (traces) | Database metrics |
|---|---|---|---|
| Keycloak (SSO, custom portal theme) | yes | yes | Postgres |
| LLDAP (user directory) | yes | no | n/a |
| RomM | yes | yes | MariaDB |
| Drop | yes | yes | Postgres |
| Paperless | no | no | Redis |
| Cloudflare Tunnels | via each app's probe | no | tunnel connection metrics |
| Renovate (dependency updates) | no | no | n/a |
| Grafana | yes | no | n/a |
| Prometheus, Alertmanager, Loki, Tempo, blackbox exporter, OpenTelemetry Operator | no | no | n/a |

Alertmanager also sends a heartbeat to healthchecks.io, so the cluster going dark still pages.
