# users.y4bo.com: LLDAP admin behind Keycloak (CHG0030487)

## MANUAL STEPS (before merge, in this order)

1. **Cloudflare tunnel + DNS (owner).** `cloudflared tunnel create lldap`, then
   `cloudflared tunnel route dns lldap users.y4bo.com`. The CNAME lives in Cloudflare,
   not in this repo (same as rom.y4bo.com).
2. **Tunnel secret.** Fill `apps/staging/lldap/tunnel-secret.yaml` from
   `~/.cloudflared/<TUNNEL_ID>.json` (command in the file), `sops --encrypt --in-place` it.
3. **Keycloak client `lldap-admin`** in realm `y4bo`: confidential (client authentication
   on), standard flow only, redirect URI `https://users.y4bo.com/oauth2/callback`, web
   origin `https://users.y4bo.com`, and a groups mapper (Group Membership, claim `groups`,
   "Full group path" off, added to ID token, access token and userinfo), same as romm/drop.
4. **Proxy secret.** Fill `apps/staging/lldap/proxy-secret.yaml` with the client secret
   from step 3 and `openssl rand -base64 32` as the cookie secret, `sops --encrypt --in-place` it.
5. **Wire the secrets.** Add `proxy-secret.yaml` and `tunnel-secret.yaml` to
   `apps/staging/lldap/kustomization.yaml` (the comment there marks the spot). Check both
   files show `ENC[` before committing.
6. **LLDAP admins.** In LLDAP (tailnet, `http://100.99.35.21:17170`): create Goose's own
   account if absent, add Goose and the owner's own account to `lldap_admin`. That one group opens
   both gates. The built-in `admin` password is never shared.

## After merge: verify as three users

| who | expect at https://users.y4bo.com |
| --- | --- |
| no session | redirect to the Keycloak login at id.y4bo.com |
| `roms`-only user | 403 from oauth2-proxy, LLDAP never reached |
| `lldap_admin` | LLDAP's own login page; their own LLDAP account works |

The blackbox probe `https://users.y4bo.com` (job blackbox-http) and the cloudflared
PodMonitor (app `cloudflared-lldap`) should both go green within a few minutes.

## Backout

Remove `oauth2-proxy.yaml` and `cloudflare.yaml` from `kustomization.yaml` (or delete the
hostname from the tunnel). The page is tailnet-only again through `service-admin.yaml`,
which this change never touches. The Keycloak client and LLDAP group memberships can stay.
