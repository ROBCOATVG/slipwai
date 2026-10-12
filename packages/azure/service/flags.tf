# Feature flags: the one thing about a running service this environment can change without a deploy.
#
# A flag's value lives in a Key Vault secret, and Container Apps resolves it into the replica's environment
# exactly the way it resolves any other secret — so a service reads `FLAG_<KEY>` at start-up like any other
# variable and needs no Azure SDK, no client, and no code that knows this file exists. That is what makes
# flags cost a generated project nothing in whichever language it was generated in.
#
# What it buys, and what it does not: `make flag` writes the secret and restarts the revision, so a flip is
# a rolling restart — around two minutes, no build, no apply, and no merge to `main`. It is not a live
# re-read, and that is the one thing this shape cannot do. Left alone the platform would find a new version
# of a versionless reference within half an hour; `make flag` does not wait, and restarts.
#
# When a flag has to move without a restart, `flag_transport = "appconfig"` in an environment's own tfvars
# is the other shape below: Azure App Configuration, read by the application under its own managed
# identity, and a flip that takes effect in seconds. It is per environment rather than per project, so an
# environment takes it on when it needs it and not before. `variable "flag_transport"` has the trade — and
# the honest part of it, which is that unlike the AWS target's agent sidecar this one puts an SDK in the
# image, because Container Apps has no sidecar to read one over loopback.
#
# A browser app reads the same flag by asking the service for it, over `GET /api/flags`, which the service
# answers from the very environment these secrets land in. So one product flag has one name and one value
# on both sides of `/api`, and the restart above is the whole of a flip: a browser already open picks the
# new value up on its next load, and no deploy is owed.
#
# It was not always so, and the reason is worth keeping. Vite inlines a `VITE_`-prefixed value while the
# bundle is *built*, so a flag compiled into a bundle is a property of that build and not of the
# environment it runs in — which gave one flag two clocks, the service's moving in a restart and the
# browser's only on the next deploy. Every screen gated on a flag then carried an ordering rule (on in the
# service first, off in the bundle first) that existed only because of how the value arrived. Asking the
# service removes the second clock, and with it the rule.
#
# `make rollback` no longer diverges here either. It restores the previous release's `index.html`, and that
# bundle carries no flag values at all, so the browser and the service both read whatever this environment
# is set to now — which is what a rollback should leave alone, the secret being the one place a flip is
# recorded.
#
# One secret per flag per environment, and every revision resolves the same one. Where `kept_revisions` is
# one, the release before this one is still running, so a flip reaches both. A key the older revision has
# never heard of is harmless, because nothing there reads it; a key whose *meaning* changed between the two
# revisions is not. That is the compatibility rule the migrations are held to, landing on flags instead of
# on schemas: a key is never repurposed, it is retired and another is introduced, exactly as a column is
# expanded before it is contracted.
#
# `ignore_changes = [value]` is what makes a flip stick. This stack seeds a new environment's secret with
# the value declared in `flags.auto.tfvars` and never touches it again, so neither the next deploy — which
# applies the whole stack, unattended, on every merge — nor `make rollback` quietly puts a flag back the way
# the file says it started. The seed is therefore a one-time event: changing it in the file moves nothing in
# an environment that already exists, where the secret is the truth and `make flags` prints it.

locals {
  # One entry per flag, keyed `<service>/<key>`, so a flag's name only has to be unique within the service
  # that reads it. `merge(...)` over a list of one-map-per-service flattens that into a single map for
  # `for_each`; the `...` is the argument expansion, not a range.
  flag_declarations = merge([
    for name, flags in var.flags : {
      for key, seed in flags : "${name}/${key}" => { service = name, key = key, seed = seed }
    }
  ]...)

  # A Key Vault secret's name takes letters, digits and hyphens and nothing else, and a container app's own
  # secret name takes the same. So one flag has three spellings, all derived from the one in
  # `flags.auto.tfvars`: `flag-<service>-<key>` in the vault, where every environment's flags share a
  # namespace; `flag-<key>` on the app, where the service is already the app; and `FLAG_<KEY>` in the
  # environment, which is the only one anybody writing code ever types.
  flag_secret_names = {
    for id, flag in local.flag_declarations : id => "flag-${flag.service}-${replace(flag.key, "_", "-")}"
  }

  # Only under `keyvault`: `appconfig` puts nothing in the replica's environment but the two keys in
  # `flag_environment`, and the values are read from the store instead.
  service_flags = {
    for name, service in var.services : name => local.use_keyvault ? {
      for id, flag in local.flag_declarations :
      "flag-${replace(flag.key, "_", "-")}" => {
        variable = "FLAG_${upper(replace(flag.key, "-", "_"))}"
        # Versionless, so a secret `make flag` has written a new version of is what the next replica reads.
        id = azurerm_key_vault_secret.flag[id].versionless_id
      }
      if flag.service == name
    } : {}
  }

  # Known from configuration alone at plan time, for the reason the `count`s in postgres.tf are: the ids
  # below are created in this same apply, so on a fresh environment their values are unknown then.
  has_flags = length(local.flag_declarations) > 0

  # Which of the two shapes below this environment is running. Per environment and not per project: see
  # `variable "flag_transport"`.
  use_keyvault  = var.flag_transport == "keyvault"
  use_appconfig = var.flag_transport == "appconfig"

  # What a replica is told about where its flags come from. `FLAG_TRANSPORT` is read by exactly one function
  # in the service — `defaultSource` in its own flag reader — so no slice, and no other file, branches on
  # it. Under `keyvault` the variables themselves are the answer and nothing here is needed.
  flag_environment = local.use_appconfig && local.has_flags ? {
    FLAG_TRANSPORT     = "appconfig"
    APPCONFIG_ENDPOINT = one(azurerm_app_configuration.flags[*].endpoint)
    APPCONFIG_LABEL    = var.environment
    AZURE_CLIENT_ID    = azurerm_user_assigned_identity.app.client_id
  } : {}
}

resource "azurerm_key_vault_secret" "flag" {
  for_each = local.use_keyvault ? local.flag_declarations : {}

  name         = local.flag_secret_names[each.key]
  key_vault_id = azurerm_key_vault.secrets.id
  value        = each.value.seed

  lifecycle {
    ignore_changes = [value]
  }

  depends_on = [time_sleep.rbac]
}

# ── The App Configuration shape ────────────────────────────────────────────────────────────────────────
#
# What `flag_transport = "appconfig"` provisions, and what it costs.
#
# It is a key-value store rather than a document, which makes it a closer match to the Key Vault shape than
# AWS's AppConfig is to its SSM one: one key per flag, seeded once and then left alone by the same
# `ignore_changes = [value]`, so the stack can own the values here without rewriting a flip on every merge.
# What `scripts/deploy.py` does is therefore only what `make flag` does — write one key — and there is no
# reconcile step of the kind the AWS target needs.
#
# The label is the environment's name, so one store *could* serve both; this stack gives each environment
# its own anyway, because sharing one would put staging and production behind a single resource whose
# deletion takes both, which is most of what two long-lived environments are for.
#
# The `free` SKU allows **one store per subscription per region**, which is the constraint to know before
# turning this on in a second environment: the second one needs `standard`, at roughly $36 a month. That is
# the real price of a flip without a restart here, and it is why this is opt-in per environment.
variable "appconfig_sku" {
  description = "The App Configuration tier: `free` allows one store per subscription per region, `standard` is about $36 a month."
  type        = string
  default     = "free"
}

resource "azurerm_app_configuration" "flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  name                = "${local.short}-flags"
  resource_group_name = azurerm_resource_group.environment.name
  location            = azurerm_resource_group.environment.location
  sku                 = var.appconfig_sku
  # The application reads this as itself, with the role assignment below; a connection string would be a
  # second credential to keep somewhere.
  local_auth_enabled = false
}

resource "azurerm_app_configuration_key" "flag" {
  for_each = local.has_flags && local.use_appconfig ? local.flag_declarations : {}

  configuration_store_id = azurerm_app_configuration.flags[0].id
  key                    = "FLAG_${upper(replace(each.value.key, "-", "_"))}"
  label                  = var.environment
  value                  = each.value.seed

  lifecycle {
    ignore_changes = [value]
  }

  depends_on = [azurerm_role_assignment.flags_writer]
}

# Whoever is applying has Contributor, which creates a store and cannot write a key in one.
resource "azurerm_role_assignment" "flags_writer" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  scope                = azurerm_app_configuration.flags[0].id
  role_definition_name = "App Configuration Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

# The first thing this skeleton's application is allowed to call. Under `keyvault` the *platform* resolves
# the secrets when it starts a replica and the app's identity is used for nothing else — the application
# never talks to Azure at all. Under this transport the application reads the store as itself, so choosing
# `appconfig` is also choosing to give the application an Azure permission and an SDK, which is worth
# knowing before taking it on.
resource "azurerm_role_assignment" "flags_reader" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  scope                = azurerm_app_configuration.flags[0].id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}

output "flags" {
  description = "What `make flag` and `make flags` need: the transport, the resource group, each app, and where the values live."
  value = {
    transport      = var.flag_transport
    resource_group = azurerm_resource_group.environment.name
    vault          = azurerm_key_vault.secrets.name
    apps           = { for name, app in azurerm_container_app.service : name => app.name }
    secrets        = { for id, name in local.flag_secret_names : id => name if local.use_keyvault }
    declared       = { for id, flag in local.flag_declarations : id => flag.seed }
    appconfig = local.use_appconfig && local.has_flags ? {
      store    = one(azurerm_app_configuration.flags[*].name)
      endpoint = one(azurerm_app_configuration.flags[*].endpoint)
      label    = var.environment
    } : null
  }
}
