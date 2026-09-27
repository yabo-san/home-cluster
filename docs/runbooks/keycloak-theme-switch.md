# Keycloak theme switch (CHG0030486)

Run after the new image is live (`start --optimized` pod Ready, logins still work on the
stock theme). The theme is switched through the admin API because the realm JSON is only
imported on first start; editing `realm-secret.yaml` changes nothing on a running realm.

Placeholders: `<ADMIN_USER>` / `<ADMIN_PASSWORD>` are a master-realm admin, `<THEME>` is
the `themeName` from the theme repo's `vite.config.ts` (Keycloakify plugin options; it is
also the theme folder name inside `keycloak-theme-y4bo.jar`).

## 0. Token

```sh
KC=https://id.y4bo.com
# If id.y4bo.com is down: kubectl -n keycloak port-forward svc/keycloak 8080 and use
# KC=http://localhost:8080 (the issuer stays id.y4bo.com because KC_HOSTNAME is set).
TOKEN=$(curl -s "$KC/realms/master/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d username='<ADMIN_USER>' -d password='<ADMIN_PASSWORD>' | jq -r .access_token)
H=(-H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json')
```

The token lives 60 seconds by default; get a fresh one per step.

## 1. Check the theme is loaded

```sh
curl -s "${H[@]}" "$KC/admin/serverinfo" | jq '.themes.login[].name, .themes.account[].name'
```

`<THEME>` must appear in both lists. If it does not, stop: the jar is not in the image.

## 2. Clients: Base URL and "Always display in UI"

The account console lists an app only when its client has both. Partial PUTs are merged
by Keycloak, so only the two fields are sent.

```sh
set_client() {  # $1 clientId, $2 base URL
  ID=$(curl -s "${H[@]}" "$KC/admin/realms/y4bo/clients?clientId=$1" | jq -r '.[0].id')
  curl -s -o /dev/null -w "$1 %{http_code}\n" -X PUT "${H[@]}" \
    "$KC/admin/realms/y4bo/clients/$ID" \
    -d "{\"baseUrl\":\"$2\",\"alwaysDisplayInConsole\":true}"
}
set_client grafana https://monitoring.y4bo.com
set_client romm    https://rom.y4bo.com
set_client drop    https://gaben.y4bo.com
```

Expect `204` for each. Harmless on the stock theme, so this step can run first on its own.

## 3. Switch the realm theme

```sh
curl -s -o /dev/null -w '%{http_code}\n' -X PUT "${H[@]}" "$KC/admin/realms/y4bo" \
  -d '{"loginTheme":"<THEME>","accountTheme":"<THEME>"}'
```

Expect `204`. Then, in a private window: `https://id.y4bo.com/realms/y4bo/account` shows
the new login page, and after login the tiles for that user's groups (verify list in the
ticket). The master realm (admin console) is not touched.

## Backout (one call)

```sh
curl -s -o /dev/null -w '%{http_code}\n' -X PUT "${H[@]}" "$KC/admin/realms/y4bo" \
  -d '{"loginTheme":"keycloak","accountTheme":"keycloak.v3"}'
```

Instant, no restart. If the image itself is the problem, revert the digest commit in
`keycloak.yaml` (and `--optimized` with it if going back to the stock image).
