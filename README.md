# home-cluster

k3s cluster managed with Flux CD. Public apps are reached through Cloudflare Tunnels.

## Apps and how each is monitored

Every app gets container metrics, logs and restart/OOM alerts. Beyond that:

| App | Uptime probe | APM (traces) | Database metrics |
|---|---|---|---|
| Keycloak (SSO) with LLDAP | yes | Keycloak yes, LLDAP no | Postgres |
| RomM | yes | yes | MariaDB |
| Drop | yes | yes | Postgres |
| Paperless | no | no | Redis |
| Grafana, Prometheus, Loki, Tempo | Grafana | no | n/a |
