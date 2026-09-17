# The local Keycloak realms

One `keycloak` service in `docker-compose.yml` imports every realm file under `docker/keycloak/realms/` at
start-up, so selecting Keycloak for either identity question gives a working issuer with no manual console
steps. A realm is one answer to one question — the staff realm and the customers realm are kept apart on
purpose, the way a real deployment keeps its workforce directory apart from its customer accounts — and
dropping an answer (`./init --auth none`, `./init --users none`) deletes its realm file and nothing else here.

**There are no comments in the realm files because Keycloak refuses them.** Import parses into
`RealmRepresentation` with unknown fields fatal, so a `_comment` key fails the whole realm — and it fails at
container start-up, which is a slow place to learn it. That is why the explanation lives here instead.

Every value below matches one in `.env.example`, because the point is that the two agree without anyone
editing either. `KEYCLOAK_PORT` is the container's host port; each issuer is `/realms/<realm>` on it.

<!-- backing-service:keycloak:begin -->
## `realms/app.json` — staff

| In the realm | Matching env key | |
|---|---|---|
| realm `app` | `OIDC_ISSUER=http://localhost:8081/realms/app` | the issuer path is `/realms/<realm>` |
| client `app-local` | `OIDC_CLIENT_ID` | confidential, standard flow |
| secret `local-only-not-a-real-secret` | `OIDC_CLIENT_SECRET` | published here on purpose — see below |
| groups `app-admin`, `app-operator`, `app-viewer` | `OIDC_GROUP_ADMIN` and the other two | what the adapter maps to roles |

The `groups` protocol mapper is the part that is easy to omit and hard to diagnose. Without it the group
memberships exist in Keycloak and never appear in the token, so the adapter's group-to-role mapping silently
sees nobody in any group. `full.path` is `false` so the claim reads `app-admin` rather than `/app-admin`,
matching the env values.

Self-registration is off: staff accounts are created by an administrator, which is the shape of a back
office. A user `staff` / `staff` is in `app-admin`, so there is something to log in as.

The adapter itself is a placeholder where nothing owns startup — see the warning at the top of
`apps/service/src/adapters/driving/http/auth/oidc-keycloak.ts` — and the framework's own OIDC client on
either Java backend.

The **client secret is in `realms/app.json`**, which is in version control. It is a local fixture, not a
secret, and nothing like it belongs in a real environment.
<!-- backing-service:keycloak:end -->
<!-- backing-service:users-keycloak:begin -->
## `realms/customers.json` — the product's users

| In the realm | Matching env key | |
|---|---|---|
| realm `customers` | `USERS_OIDC_ISSUER` and `VITE_USERS_ISSUER`, both `http://localhost:8081/realms/customers` | one issuer, read by the service and by the browser app |
| client `web` | `VITE_USERS_CLIENT_ID` | public, authorization code with PKCE (`S256`) required, no secret |
| client `api` | `USERS_OIDC_AUDIENCE` | bearer-only: the service, which never logs anyone in and only validates tokens |
| redirect `http://localhost:5173/*`, origin `http://localhost:5173` | the first browser app's dev server | a second browser app needs its own redirect URI added here |

What differs from the staff realm is what makes it a customer realm: **self-registration is on**, an
account's username is its email address, **password reset is on**, and there are no groups — a customer is
`sub` plus a verified email, and what an account may do is decided per account in a use case, not by a role.
Email verification is off because there is no mail server locally; turn it on (`verifyEmail`) in the same
change that configures SMTP for the realm, and a real deployment does both.

The `api-audience` mapper on the `web` client is the counterpart of the staff realm's `groups` mapper: it puts
`api` into the `aud` of every access token the browser obtains, which is what lets the service insist on an
audience rather than accept any token this realm ever issued.

A user `customer@example.invalid` / `customer` exists with a verified email, so there is something to sign in
as before anyone registers. Sign in through the browser app (`make dev-web`), which owns the login flow — see
`apps/web/src/auth/users.tsx`.

The two realms share one Keycloak, so a staff token is a valid JWT whose issuer differs from a customer's by
one path segment. The customer adapter in each service refuses any issuer but its own for exactly that
reason; do not weaken that check to "any realm on this host".
<!-- backing-service:users-keycloak:end -->

## Do not carry this into a real environment

- The **bootstrap admin is `admin` / `admin`**, set in `docker-compose.yml`.
- The service runs `start-dev`, which disables HTTPS and is explicitly not for production.
- There is **no volume**, deliberately: the realms are re-imported on every start, so the container is
  disposable and reproducible rather than a stateful thing that drifts from these files. Accounts registered
  locally vanish with it.

A real deployment gets its realms from its own provisioning. Load the `secure-oauth-oidc` skill before
implementing or changing any part of the flow.

## Running it

```sh
make services-up                            # starts every service in docker-compose.yml
open http://localhost:8081/realms/app/.well-known/openid-configuration
open http://localhost:8081/realms/customers/.well-known/openid-configuration
```

`make services-up` waits for every container to report healthy, Keycloak's own healthcheck included, so it
returns only once the issuers above actually answer. A cold start takes a few seconds longer than Postgres'.
