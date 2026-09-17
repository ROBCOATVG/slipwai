# backing-service:keycloak:begin
# Staff identity, provisioned as an Entra ID app registration in the subscription's own workforce tenant:
# the same three groups the local Keycloak realm has, and one confidential client for the services.
# Keycloak stays the local stand-in — same groups, same `OIDC_*` keys — so `make demo` needs no Azure
# subscription and the adapters cannot tell the two apart except by the issuer, which is configuration.
#
# The protocol flow is as unwritten here as it is locally: the redirect URI is a variable with a
# placeholder default because there is no route to redirect to yet. Set it in the environment's tfvars in
# the same change that writes the route.
#
# **App roles rather than security groups**, and that is a deliberate improvement on what a literal
# translation of the Cognito shape would have been. Entra can put group membership in a token, but only as
# the groups' *object ids* — so `OIDC_GROUP_ADMIN` would have had to be a GUID, and creating the groups
# would have needed `Group.ReadWrite.All` on the deploy identity, which is permission over the whole
# directory rather than over this one application. An app role is part of the application object, so it is
# covered by the `Application.ReadWrite.OwnedBy` grant the bootstrap stack makes, it appears in the `roles`
# claim as the plain string below, and the adapter compares the same three names it compares locally.
# `OIDC_GROUPS_CLAIM` is `roles` here and `groups` in Keycloak, which is the one line of configuration
# between them — one fewer than Cognito needs.
locals {
  staff_wanted = anytrue([for service in var.services : service.auth == "entra"])
  staff_groups = ["app-admin", "app-operator", "app-viewer"]
  # A stable id per role, derived from the role's own name so it never moves between applies and never
  # collides with another project's. An app role's id is a UUID the caller chooses, not one Entra assigns.
  staff_role_ids = {
    for name in local.staff_groups : name => uuidv5("dns", "${var.project}.${var.environment}.${name}")
  }
  staff_environment = local.staff_wanted ? {
    OIDC_ISSUER         = "https://login.microsoftonline.com/${data.azurerm_client_config.current.tenant_id}/v2.0"
    OIDC_CLIENT_ID      = azuread_application.staff[0].client_id
    OIDC_GROUPS_CLAIM   = "roles"
    OIDC_GROUP_ADMIN    = "app-admin"
    OIDC_GROUP_OPERATOR = "app-operator"
    OIDC_GROUP_VIEWER   = "app-viewer"
  } : {}
}

variable "staff_callback_urls" {
  description = "Where the staff login may redirect back to. A placeholder until the flow exists; then this environment's real URL."
  type        = list(string)
  default     = ["http://localhost:3000/auth/callback"]
}

resource "azuread_application" "staff" {
  count = local.staff_wanted ? 1 : 0

  display_name = "${local.prefix}-staff"
  # This directory's own accounts and nobody else's: staff are people the organisation already has, which
  # is the whole difference between this axis and the one that answers for the product's users.
  sign_in_audience = "AzureADMyOrg"

  dynamic "app_role" {
    for_each = local.staff_role_ids

    content {
      id                   = app_role.value
      value                = app_role.key
      display_name         = app_role.key
      description          = "The ${app_role.key} role, as the local Keycloak realm has it"
      allowed_member_types = ["User"]
      enabled              = true
    }
  }

  web {
    redirect_uris = var.staff_callback_urls

    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = false
    }
  }
}

resource "azuread_service_principal" "staff" {
  count = local.staff_wanted ? 1 : 0

  client_id = azuread_application.staff[0].client_id
  # Staff are assigned a role or they do not get in: without this anyone in the directory could sign in
  # with no role at all, and an adapter that reads `roles` would see an empty claim rather than a refusal.
  app_role_assignment_required = true
}

# Confidential: the services hold the secret, referenced from Key Vault as OIDC_CLIENT_SECRET.
resource "azuread_application_password" "staff" {
  count = local.staff_wanted ? 1 : 0

  application_id = azuread_application.staff[0].id
  display_name   = "${local.prefix}-service"
}

resource "azurerm_key_vault_secret" "staff_client" {
  count = local.staff_wanted ? 1 : 0

  name         = "OIDC-CLIENT-SECRET"
  key_vault_id = azurerm_key_vault.secrets.id
  value        = azuread_application_password.staff[0].value

  depends_on = [time_sleep.rbac]
}

output "staff_application" {
  description = "The app registration staff sign in through, once the flow exists to send them there."
  value       = local.staff_wanted ? azuread_application.staff[0].client_id : null
}
# backing-service:keycloak:end
