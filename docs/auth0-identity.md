# Auth0 on both identity axes

`--auth auth0` and `--users auth0`, under `--target aws` and `--target azure`. A third-party issuer is not a
property of a cloud, so it is one row offered under both rather than two rows that happen to agree.

It exists because the two clouds are not symmetrical here. AWS put its customer-identity product in the
subscription plane — a Cognito user pool is a resource in your account, made by the same credential and in
the same apply as the load balancer. Microsoft put its in the directory plane: the counterpart is a separate
*tenant*, which azurerm has no resource for and whose sign-up flows azuread has no resource for either
([`azure-target.md`](azure-target.md) has the table). So `--target azure` had no customer-identity answer at
all, and the honest way to give it one was not to half-port Microsoft's product but to carry the answer most
teams actually reach for.

## What a project is given

| Axis | What the stack creates |
|---|---|
| `auth` | A database connection staff sign in against, with sign-up **off** — staff are accounts an administrator creates. A confidential `regular_web` client, whose secret is written to Secrets Manager or Key Vault and injected as `OIDC_CLIENT_SECRET`. Three roles. A post-login action putting them in one namespaced claim. |
| `users` | A second database connection with self-registration and password reset **on**. An API resource server whose identifier is the audience. A public `spa` client for the browser app, PKCE, callbacks derived from this environment's own site. |

Keycloak stays the local stand-in for both, exactly as it does for Cognito and Entra: same realms, same
`OIDC_*` and `USERS_OIDC_*` names, so `make demo` needs no tenant and the adapters cannot tell the three
providers apart except by configuration. That is the property these axes are built on, and this row keeps it.

## What it costs that no other row costs

**A credential the cloud did not issue.** The deploy role owns your account; it owns nothing in an Auth0
tenant. `infra/service/auth0.tf` is applied with a machine-to-machine application's own credentials, read
from the environment as `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID` and `AUTH0_CLIENT_SECRET`. One apply, two
credentials. `make bootstrap` asks for the three and stores two as forge variables and one as a secret.

**A human step before the first apply**, which no other row has:

1. Create the Auth0 tenant. There is no API for it.
2. Create one machine-to-machine application authorised for the Auth0 Management API, allowed to read and
   write clients, connections, resource servers and roles.

Everything else is made on every apply, like any other resource in the stack. Staff accounts and their role
assignments are made by nobody: the stack creates the roles, and putting a person in one is an operator act
— the same line the Cognito row draws between groups and memberships.

## Three things that are not like-for-like, and are not accidents

### Staff and customers share one issuer

Under Keycloak they are two realms and under Cognito two user pools, each with an issuer of its own, and
an issuer check alone separates them — the users adapter says so in its own header, and its test uses the
staff realm's issuer on purpose. Here they are two connections in one tenant, and the issuer is the same
string for both.

What separates them instead is the audience: a staff ID token is minted for the staff client, and a
customer's access token for the customers API. Auth0 enforces the separation upstream of that as well — each
connection is bound to its own client, and the staff client is not granted the customers API — so a staff
account cannot obtain a customer's token by asking. But in the resource server, the `aud` check is the one
doing the work, where for every other answer on this axis the `iss` check would have caught it too.

Both adapters already list `aud` as required and both are scaffolds with the validation deliberately
unwritten. This is the one answer where getting that check wrong is not defence in depth.

### The staff roles arrive through an action

Auth0 puts no roles in a token by default. The RBAC setting that puts `permissions` in an *access* token
does not touch the ID token, which is what the staff adapter validates — so the roles reach the token the
way Auth0 documents it: a post-login action setting one namespaced custom claim, named by
`OIDC_GROUPS_CLAIM`. The values inside are the same three plain strings Keycloak and Cognito use.

The alternative was an `auth0_resource_server` with `enforce_policies` and the `access_token_authz` dialect,
which needs no code — and would have moved staff validation from the ID token to an access token, which is a
change to every adapter rather than to this stack.

### One tenant serves both environments

`staging` and `production` are workspaces over one module, and there is one credential on the forge, so both
environments' clients and connections live in one tenant, kept apart by the `<project>-<environment>` prefix
every name carries. Auth0's own guidance is a tenant per environment.

Doing that properly needs a second tenant and per-environment credentials — a change to how the pipeline
passes secrets, not to this stack — so it is written here and in the generated ADR rather than left to be
discovered. One visible consequence: both environments' post-login actions run on every login in the tenant.
Each filters the roles to its own prefix, so they do not contradict each other, but they do both run.

## Why the file is chosen at generation time and not pruned later

Every other answer's infrastructure lives in a `backing-service:<feature>` region that `./init` can strip.
This one cannot, and the reason is a property of the provider: **OpenTofu configures a provider the moment
anything in the module refers to it, and a `count = 0` resource is enough.** The Auth0 provider refuses to
configure itself without a tenant credential, so a project that did not choose Auth0 must not carry the
`provider` block at all — and no marker could decide that, because `keycloak` is the feature behind Cognito,
Entra *and* Auth0.

So `auth0.tf` and `no-auth0.tf` are chosen between when the project is written, exactly as `frontend.tf` and
`no-frontend.tf` are, and only one is ever emitted — always under the name `auth0.tf`. The empty half names
the four locals `main.tf` and `outputs.tf` refer to and answers "nothing" to each.

The version pin is the exception: a module may have only one `required_providers` block, so it lives in
`versions.tf` in every project. Declaring a provider is not configuring one — nothing asks it for a
credential until a resource refers to it, which is what makes that safe, and
`tests/test_auth0_identity.py` holds both halves of it.

## What the factory proves, and what it cannot

Proved here, on every push: the catalog offers the row where it says it does; a project that chose it gets
the provider and one that did not gets none; the stacks validate against the real provider before and after
a prune; the workflows carry the credential only for a project that needs it; dropping both identity answers
leaves nothing that asks for a tenant credential.

Not proved here, and not provable: the apply. It ends in somebody's Auth0
tenant, as the rest of the stack ends in somebody's account. That limitation
is as true of this row as of every other, and this one widens it — it is the
first row whose apply needs a credential the factory has never held.
