# backing-service:keycloak:begin
# Internal identity, provisioned as a Cognito user pool: the same three groups the local Keycloak realm has,
# a hosted login, and one confidential client for the services. Keycloak stays the local stand-in — same
# groups, same OIDC_* keys — so `make demo` needs no AWS account and the adapters cannot tell the two apart
# except by the issuer and the name of the groups claim, which are configuration. The Essentials tier is
# free to 10,000 monthly active users.
#
# The protocol flow is as unwritten here as it is locally: the redirect URI is a variable with a placeholder
# default because there is no route to redirect to yet. Set it in the environment's tfvars in the same change
# that writes the route.
locals {
  internal_wanted = anytrue([for service in var.services : service.auth == "cognito"])
  internal_groups = ["app-admin", "app-operator", "app-viewer"]
  internal_environment = local.internal_wanted ? {
    OIDC_ISSUER         = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.internal[0].id}"
    OIDC_CLIENT_ID      = aws_cognito_user_pool_client.internal[0].id
    OIDC_GROUPS_CLAIM   = "cognito:groups"
    OIDC_GROUP_ADMIN    = "app-admin"
    OIDC_GROUP_OPERATOR = "app-operator"
    OIDC_GROUP_VIEWER   = "app-viewer"
  } : {}
}

variable "internal_callback_urls" {
  description = "Where the internal login may redirect back to. A placeholder until the flow exists; then this environment's real URL."
  type        = list(string)
  default     = ["http://localhost:3000/auth/callback"]
}

resource "aws_cognito_user_pool" "internal" {
  count = local.internal_wanted ? 1 : 0

  name                = "${local.prefix}-internal"
  user_pool_tier      = "ESSENTIALS"
  deletion_protection = var.environment == "production" ? "ACTIVE" : "INACTIVE"

  # Internal are accounts an administrator creates; nobody signs up.
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }
}

resource "aws_cognito_user_pool_domain" "internal" {
  count = local.internal_wanted ? 1 : 0

  # A Cognito-hosted prefix domain; a custom domain needs a certificate and a DNS zone this stack does not own.
  domain                = "${local.prefix}-internal"
  user_pool_id          = aws_cognito_user_pool.internal[0].id
  managed_login_version = 2
}

resource "aws_cognito_user_group" "internal" {
  for_each = local.internal_wanted ? toset(local.internal_groups) : toset([])

  name         = each.key
  user_pool_id = aws_cognito_user_pool.internal[0].id
}

resource "aws_cognito_user_pool_client" "internal" {
  count = local.internal_wanted ? 1 : 0

  name         = "${local.prefix}-service"
  user_pool_id = aws_cognito_user_pool.internal[0].id
  # Confidential: the services hold the secret, injected from Secrets Manager as OIDC_CLIENT_SECRET.
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.internal_callback_urls
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
}

resource "aws_secretsmanager_secret" "internal_client" {
  count = local.internal_wanted ? 1 : 0

  name                    = "${local.prefix}/OIDC_CLIENT_SECRET"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "internal_client" {
  count = local.internal_wanted ? 1 : 0

  secret_id     = aws_secretsmanager_secret.internal_client[0].id
  secret_string = aws_cognito_user_pool_client.internal[0].client_secret
}

output "internal_login" {
  description = "The hosted login for internal, once the flow exists to send them there."
  value       = local.internal_wanted ? "https://${aws_cognito_user_pool_domain.internal[0].domain}.auth.${data.aws_region.current.region}.amazoncognito.com" : null
}
# ─────────────────────────────────────────────────────────────────────────────────────────────────────
# Renamed 2026-10-08: `staff` is `internal` and `customers` is `external`, because the two identity axes
# are now asked that way. A resource address is state, not a name — without these blocks the first apply
# after the rename destroys every resource below and creates it again, which for a user pool is every
# account in it. `tofu plan` reads these and moves the state instead; read the plan before you apply, and
# it must say no destroy.
# ─────────────────────────────────────────────────────────────────────────────────────────────────────
moved {
  from = aws_cognito_user_pool.staff
  to   = aws_cognito_user_pool.internal
}

moved {
  from = aws_cognito_user_pool_domain.staff
  to   = aws_cognito_user_pool_domain.internal
}

moved {
  from = aws_cognito_user_group.staff
  to   = aws_cognito_user_group.internal
}

moved {
  from = aws_cognito_user_pool_client.staff
  to   = aws_cognito_user_pool_client.internal
}

moved {
  from = aws_secretsmanager_secret.staff_client
  to   = aws_secretsmanager_secret.internal_client
}

moved {
  from = aws_secretsmanager_secret_version.staff_client
  to   = aws_secretsmanager_secret_version.internal_client
}
# backing-service:keycloak:end
