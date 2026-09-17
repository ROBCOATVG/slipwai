# backing-service:keycloak|users-keycloak:begin
# Identity provisioned in Auth0 — the one answer on either identity axis whose objects are **not** created
# by the credential that creates everything else in this stack. The deploy identity owns this resource
# group; it owns nothing in an Auth0 tenant. So this file is applied with a second credential, a machine-to-machine
# application's, read from the environment as AUTH0_DOMAIN, AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET.
# `make bootstrap` asks for the three and stores them on the forge beside the cloud ones; `infra/README.md`
# says what a person has to make by hand before the first apply, and it is exactly two things: the tenant,
# and that one application. Everything below is created on every apply, like any other resource here.
#
# ── One tenant, two environments ──────────────────────────────────────────────────────────────────────
# `staging` and `production` are workspaces over this module and there is one Auth0 credential, so both
# environments' objects live in one tenant, kept apart only by the `<project>-<environment>` prefix every
# name below carries. Auth0's own guidance is a tenant per environment. Doing that needs a second tenant
# and per-environment credentials — a change to how the pipeline passes secrets, not to this file — and
# `docs/adr/0002-production-target.md` records the choice rather than leaving it to be discovered.
#
# ── Why the staff roles arrive through an action ──────────────────────────────────────────────────────
# Auth0 puts no roles in a token by default, and the RBAC setting that puts `permissions` in an access
# token does not touch the ID token, which is what the staff adapter validates. So the roles reach the
# token the way Auth0 documents: a post-login action setting one namespaced custom claim, whose name is
# OIDC_GROUPS_CLAIM. The values inside it are the same three plain strings Keycloak and Cognito use, so
# the adapters cannot tell the three providers apart except by configuration — which is the property this
# axis is built on.
# Every value from the environment. Nothing here names a tenant, exactly as nothing else in this stack
# names an account: the credential decides which tenant is written to, and `scripts/deploy.py` passes it
# through from the forge.
provider "auth0" {}

data "auth0_tenant" "current" {}

locals {
  # The issuer every token from this tenant carries, and the one value both identity answers share — which
  # is the difference from Keycloak and Cognito worth knowing before a validator is written. There, staff
  # and customers differ by issuer and an issuer check alone separates them. Here they are one tenant, and
  # what separates them is the audience: a staff ID token is minted for the staff client, a customer's
  # access token for the customers API. A resource server that checks the signature and the issuer but not
  # `aud` would accept a staff member as a customer. Both adapters already list the `aud` check as
  # required; under this answer it is the check that does the work.
  #
  # A tenant with a custom domain issues on that domain instead. This reads the tenant's own domain, so a
  # project that adds one has to set the issuer it wants here.
  auth0_issuer = "https://${data.auth0_tenant.current.domain}/"
}
# backing-service:keycloak|users-keycloak:end

# backing-service:keycloak:begin
locals {
  auth0_staff_wanted = anytrue([for service in var.services : service.auth == "auth0"])
  auth0_staff_roles  = ["app-admin", "app-operator", "app-viewer"]
  # A custom claim must be namespaced with a URL that is not Auth0's own, and the name is per environment
  # so that two environments sharing one tenant cannot be read as one.
  auth0_roles_claim = "https://${local.prefix}/roles"
  auth0_staff_environment = local.auth0_staff_wanted ? {
    OIDC_ISSUER         = local.auth0_issuer
    OIDC_CLIENT_ID      = auth0_client.staff[0].client_id
    OIDC_GROUPS_CLAIM   = local.auth0_roles_claim
    OIDC_GROUP_ADMIN    = "app-admin"
    OIDC_GROUP_OPERATOR = "app-operator"
    OIDC_GROUP_VIEWER   = "app-viewer"
  } : {}
}

variable "auth0_staff_callback_urls" {
  description = "Where the staff login may redirect back to. A placeholder until the flow exists; then this environment's real URL."
  type        = list(string)
  default     = ["http://localhost:3000/auth/callback"]
}

# Staff sign in against a database connection of their own, never the customers' one — the same separation
# the local Keycloak makes with two realms, and Cognito with two pools. Sign-up is off: staff are accounts
# an administrator creates.
resource "auth0_connection" "staff" {
  count = local.auth0_staff_wanted ? 1 : 0

  name     = "${local.prefix}-staff"
  strategy = "auth0"

  options {
    disable_signup          = true
    password_policy         = "good"
    brute_force_protection  = true
    requires_username       = false
    strategy_version        = 2
  }
}

resource "auth0_client" "staff" {
  count = local.auth0_staff_wanted ? 1 : 0

  name            = "${local.prefix}-staff"
  app_type        = "regular_web"
  oidc_conformant = true
  # Confidential: the services hold the secret, injected from Key Vault as OIDC_CLIENT_SECRET.
  grant_types                = ["authorization_code", "refresh_token"]
  callbacks                  = var.auth0_staff_callback_urls
  allowed_logout_urls        = var.auth0_staff_callback_urls
  is_first_party             = true
  cross_origin_auth          = false
  require_proof_of_possession = false
}

resource "auth0_client_credentials" "staff" {
  count = local.auth0_staff_wanted ? 1 : 0

  client_id             = auth0_client.staff[0].id
  authentication_method = "client_secret_post"
}

resource "auth0_connection_clients" "staff" {
  count = local.auth0_staff_wanted ? 1 : 0

  connection_id   = auth0_connection.staff[0].id
  enabled_clients = [auth0_client.staff[0].id]
}

resource "auth0_role" "staff" {
  for_each = local.auth0_staff_wanted ? toset(local.auth0_staff_roles) : toset([])

  name        = "${local.prefix}-${each.key}"
  description = "The ${each.key} role for ${var.project} in ${var.environment}."
}

# The roles a user holds are not in a token until something puts them there. `event.authorization.roles`
# is what the post-login trigger is given; this copies it into one namespaced claim on both tokens, which
# is the shape every adapter already reads through OIDC_GROUPS_CLAIM. Role names carry the environment
# prefix in Auth0 so two environments in one tenant do not collide; the claim is trimmed back to the plain
# three so what a service sees is identical to Keycloak's and Cognito's.
resource "auth0_action" "staff_roles" {
  count = local.auth0_staff_wanted ? 1 : 0

  name    = "${local.prefix}-staff-roles"
  runtime = "node22"
  deploy  = true
  code    = <<-JS
    exports.onExecutePostLogin = async (event, api) => {
      const claim = '${local.auth0_roles_claim}';
      const prefix = '${local.prefix}-';
      const roles = (event.authorization?.roles ?? [])
        .filter((role) => role.startsWith(prefix))
        .map((role) => role.slice(prefix.length));
      api.idToken.setCustomClaim(claim, roles);
      api.accessToken.setCustomClaim(claim, roles);
    };
  JS

  supported_triggers {
    id      = "post-login"
    version = "v3"
  }
}

resource "auth0_trigger_action" "staff_roles" {
  count = local.auth0_staff_wanted ? 1 : 0

  trigger   = "post-login"
  action_id = auth0_action.staff_roles[0].id
}

resource "azurerm_key_vault_secret" "auth0_staff_client" {
  count = local.auth0_staff_wanted ? 1 : 0

  name         = "AUTH0-OIDC-CLIENT-SECRET"
  key_vault_id = azurerm_key_vault.secrets.id
  value        = auth0_client_credentials.staff[0].client_secret

  # The same wait every other first write to this vault takes: an RBAC assignment made moments ago is not
  # always readable yet. `main.tf` explains it where the sleep is declared.
  depends_on = [time_sleep.rbac]
}

# The Key Vault reference main.tf injects, in the shape Container Apps reads — a secret name the app
# declares, the vault secret it points at, and the variable it lands in. Behind a local so that a project
# without this answer can name the same thing and get nothing; `no-auth0.tf` is the other half.
locals {
  auth0_staff_secrets = local.auth0_staff_wanted ? {
    "oidc-client-secret" = { variable = "OIDC_CLIENT_SECRET", id = azurerm_key_vault_secret.auth0_staff_client[0].id }
  } : {}
}

output "auth0_staff_login" {
  description = "The tenant that authenticates staff, once the flow exists to send them there."
  value       = local.auth0_staff_wanted ? local.auth0_issuer : null
}
# backing-service:keycloak:end

# backing-service:users-keycloak:begin
# The product's users, provisioned as a second database connection and a public client — never the staff
# connection with a flag on it, for the reason the local Keycloak has two realms. Self-registration and
# password reset are on, and the browser app performs the code flow with PKCE exactly as it does against
# the local `customers` realm.
locals {
  auth0_customers_wanted = anytrue([for service in var.services : service.users == "auth0"])
  # The API the browser app asks for a token for. Its identifier is the `aud` of every customer access
  # token, and it is what tells a customer's token apart from a staff member's in this one tenant.
  auth0_customers_audience = "https://${local.prefix}/customers"
  auth0_customers_environment = local.auth0_customers_wanted ? {
    USERS_OIDC_ISSUER   = local.auth0_issuer
    USERS_OIDC_AUDIENCE = local.auth0_customers_audience
  } : {}
  auth0_web_environment = local.auth0_customers_wanted ? {
    VITE_USERS_ISSUER    = local.auth0_issuer
    VITE_USERS_CLIENT_ID = auth0_client.customers[0].client_id
    VITE_USERS_AUDIENCE  = local.auth0_customers_audience
  } : {}
}

# Where the customer login may return the browser to. RFC 9700 wants exact URIs and no wildcard, so this is
# a list of literal addresses. The default is empty and the real value is this environment's own site,
# which nothing outside this stack knows until it has been applied.
variable "auth0_customer_callback_urls" {
  description = "Extra exact URLs the customer login may return to, beyond this environment's own site."
  type        = list(string)
  default     = []
}

locals {
  # The browser app uses `${window.location.origin}/` for both redirect_uri and post_logout_redirect_uri,
  # so the trailing slash is part of the address Auth0 is asked to match.
  auth0_customer_login_urls = concat(["${local.public_url}/"], var.auth0_customer_callback_urls)
}

resource "auth0_resource_server" "customers" {
  count = local.auth0_customers_wanted ? 1 : 0

  name       = "${local.prefix}-customers"
  identifier = local.auth0_customers_audience
  signing_alg = "RS256"
  # Customers have no roles: whether a customer may see an order is a question of ownership, decided in the
  # use case that loads it. So no RBAC here, and nothing authorisation-shaped in the token.
  enforce_policies   = false
  token_dialect      = "access_token"
  allow_offline_access = true
}

resource "auth0_connection" "customers" {
  count = local.auth0_customers_wanted ? 1 : 0

  name     = "${local.prefix}-customers"
  strategy = "auth0"

  options {
    disable_signup         = false
    password_policy        = "good"
    brute_force_protection = true
    requires_username      = false
    strategy_version       = 2
  }
}

resource "auth0_client" "customers" {
  count = local.auth0_customers_wanted ? 1 : 0

  name            = "${local.prefix}-customers"
  app_type        = "spa"
  oidc_conformant = true
  # Public: the browser holds no secret and the code flow is protected by PKCE.
  grant_types         = ["authorization_code", "refresh_token"]
  callbacks           = local.auth0_customer_login_urls
  allowed_logout_urls = local.auth0_customer_login_urls
  web_origins         = [local.public_url]
  allowed_origins     = [local.public_url]
  is_first_party      = true
}

resource "auth0_connection_clients" "customers" {
  count = local.auth0_customers_wanted ? 1 : 0

  connection_id   = auth0_connection.customers[0].id
  enabled_clients = [auth0_client.customers[0].id]
}
# backing-service:users-keycloak:end
