# home-cluster

A self-hosted, open-source take on the SSO and observability I used in production (OneLogin, New Relic):
Keycloak on an LLDAP directory for single sign-on, and Prometheus, Loki, Tempo and Grafana for metrics,
logs, traces and APM.

k3s cluster managed with Flux CD. Public apps are reached through Cloudflare Tunnels. Secrets are
encrypted in the repo with SOPS + age and decrypted by Flux.

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
