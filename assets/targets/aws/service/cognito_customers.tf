# backing-service:users-keycloak:begin
# The product's users, provisioned as a second Cognito user pool — never the staff pool with a flag on it,
# for the reason the local Keycloak has two realms: customers and staff share no accounts, no groups and no
# login page. Self-registration is on, the email is verified, and the browser app holds a public client and
# performs the code flow with PKCE, exactly as it does against the local `customers` realm.
#
# One thing differs from Keycloak and is worth knowing before the first token is validated: a Cognito access
# token carries the client id in `client_id`, not in `aud`. USERS_OIDC_AUDIENCE is set to the client id so the
# value is right; the adapters' audience check, written against Keycloak's `aud`, has to read that claim
# here — the users adapter's own note says where.
locals {
  customers_wanted = anytrue([for service in var.services : service.users == "cognito"])
  customers_issuer = local.customers_wanted ? "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.customers[0].id}" : null
  customers_environment = local.customers_wanted ? {
    USERS_OIDC_ISSUER   = local.customers_issuer
    USERS_OIDC_AUDIENCE = aws_cognito_user_pool_client.customers[0].id
  } : {}
}

# Where the customer login may return the browser to. RFC 9700 wants exact URIs and no wildcard, so this is
# a list of literal addresses rather than a pattern.
#
# The default is empty and the real value is derived below, because the address that has to be registered is
# this environment's own site - `local.public_url`, the web distribution's domain - and nothing outside this
# stack knows it until the stack has been applied. A hand-written localhost default is worse than none: it
# is the one address a deployed pool never needs, and it makes the pool look configured while the deployed
# site's own address is missing. Override this only for an address the stack cannot know, such as a custom
# domain in front of the distribution.
variable "customer_callback_urls" {
  description = "Extra exact URLs the customer login may return to, beyond this environment's own site."
  type        = list(string)
  default     = []
}

locals {
  # The browser app uses `${window.location.origin}/` for both redirect_uri and post_logout_redirect_uri, so
  # the trailing slash is part of the address Cognito is asked to match, and Cognito matches it exactly.
  # `local.public_url` carries no trailing slash; this adds the one the browser will send. Getting this wrong
  # fails neither a plan nor a deploy - it fails at the hosted login page with `redirect_mismatch`, after
  # everything else looks healthy.
  customer_login_urls = concat(["${local.public_url}/"], var.customer_callback_urls)
}

resource "aws_cognito_user_pool" "customers" {
  count = local.customers_wanted ? 1 : 0

  name                = "${local.prefix}-customers"
  user_pool_tier      = "ESSENTIALS"
  deletion_protection = var.environment == "production" ? "ACTIVE" : "INACTIVE"

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }
}

resource "aws_cognito_user_pool_domain" "customers" {
  count = local.customers_wanted ? 1 : 0

  domain                = "${local.prefix}-customers"
  user_pool_id          = aws_cognito_user_pool.customers[0].id
  managed_login_version = 2
}

# Public: a browser cannot keep a secret, so there is none, and PKCE is what binds the code to the client.
resource "aws_cognito_user_pool_client" "customers" {
  count = local.customers_wanted ? 1 : 0

  name                                 = "${local.prefix}-web"
  user_pool_id                         = aws_cognito_user_pool.customers[0].id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = local.customer_login_urls
  logout_urls                          = local.customer_login_urls
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
}

# What the browser app is built with for this environment: Vite bakes VITE_* values into the bundle, so the
# bundle is built once per environment by scripts/deploy.py, from these.
# What the browser app is built with when the customers are Cognito's. Merged into the one
# `web_environment` output in outputs.tf, because the Auth0 answer contributes to it too and an output may
# be declared once.
locals {
  cognito_web_environment = local.customers_wanted ? {
    VITE_USERS_ISSUER    = local.customers_issuer
    VITE_USERS_CLIENT_ID = aws_cognito_user_pool_client.customers[0].id
  } : {}
}
# backing-service:users-keycloak:end
