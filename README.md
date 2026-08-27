# home-cluster

GitOps-driven single-node k3s homelab — Flux CD, SOPS/age, Longhorn, kube-prometheus-stack, Cloudflare Tunnel.

> Docs intentionally stripped — the cluster changed a lot (Keycloak SSO, a friends portal, monitoring-as-code) and the old README was stale. Reference links kept below; full docs are a rewrite-in-progress.

## Planned / In Progress

- [ ] Overseerr
- [ ] Kavita
- [ ] Romm
- [ ] LinuxGSM
- [ ] [Protonmail bridge using traefik](https://rossjr.dev/blog/proton-bridge-tailscale/)
- [ ] Second cluster node (RAM expansion)
- [ ] YAMS to [Preparr migration](https://robbeverhelst.github.io/Preparr/deployment/helm/)
- [ ] [Stirling-pdf](https://docs.stirlingpdf.com/Installation/Kubernetes%20Install)

## Sources

- [k3s on ubuntu](https://www.digitalocean.com/community/tutorials/how-to-setup-k3s-kubernetes-cluster-on-ubuntu)
- [SOPS with age encryption in fluxCD](https://fluxcd.io/flux/guides/mozilla-sops/#encrypting-secrets-using-age)
- [longhorn on fluxCD](https://oneuptime.com/blog/post/2026-03-06-deploy-longhorn-storage-flux-cd/view)
- [fluxCD monorepo](https://fluxcd.io/flux/guides/repository-structure/#monorepo)
