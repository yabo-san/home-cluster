# home-cluster

k3s cluster managed with Flux CD. Public apps are reached through Cloudflare Tunnels.

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

Alertmanager also sends a heartbeat to an external service, so the cluster going dark still pages.
