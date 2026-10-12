# backing-service:postgres:begin
# The Postgres event store, provisioned as a Flexible Server: one server per environment, shared by every
# service whose store is Postgres — the same shape Compose gives them locally, and the right one until a
# service owns data of its own (docs/services.md, "Three limits worth knowing"). `B_Standard_B1ms`, single
# zone, on purpose: the smallest burstable tier that is a real always-on Postgres. Its minimum disk is
# 32 GB, which is why this is the one line in `docs/adr/0002-production-target.md` that costs more than the
# AWS target's equivalent.
locals {
  database_wanted = anytrue([for service in var.services : service.store == "flexible-server"])
  # The services whose migrations run as a one-off job against this database, with the service's own image
  # or the migrate image built beside it. A backend whose framework migrates as the service starts (both
  # Java backends, switched on through its `environment`) has neither and is not here.
  migrating = {
    for name, service in var.services : name => service
    if service.store == "flexible-server" && (service.migrate_command != null || service.migrate_image != null)
  }
}

variable "postgres_version" {
  description = "The Postgres major version; minor upgrades apply in the maintenance window."
  type        = string
  default     = "17"
}

variable "database_sku" {
  description = "The Flexible Server SKU; the smallest burstable tier is a real database for about $16 a month."
  type        = string
  default     = "B_Standard_B1ms"
}

resource "random_password" "database" {
  count = local.database_wanted ? 1 : 0

  length  = 32
  special = false
}

# Public endpoint with a firewall, rather than a virtual network of this project's own. The Container Apps
# environment here is not VNet-integrated — that is a decision with a cost and a subnet plan behind it —
# so the apps reach this over the platform's own network, and the rule below is what says "Azure services
# only". `docs/adr/0002-production-target.md` names the private-endpoint version as the first thing to do
# when this project holds anything that matters.
resource "azurerm_postgresql_flexible_server" "database" {
  count = local.database_wanted ? 1 : 0

  name                          = "${local.short}-db"
  resource_group_name           = azurerm_resource_group.environment.name
  location                      = azurerm_resource_group.environment.location
  version                       = var.postgres_version
  sku_name                      = var.database_sku
  storage_mb                    = 32768
  auto_grow_enabled             = true
  administrator_login           = "app"
  administrator_password        = random_password.database[0].result
  public_network_access_enabled = true
  zone                          = "1"
  # Production keeps a week of backups; staging keeps the minimum the product allows, which is also a week.
  backup_retention_days        = var.environment == "production" ? 7 : 7
  geo_redundant_backup_enabled = false

  authentication {
    password_auth_enabled         = true
    active_directory_auth_enabled = false
  }

  lifecycle {
    # The zone the platform picked on creation comes back in the plan on every apply; letting it re-send
    # would propose replacing the database.
    ignore_changes = [zone]
  }
}

# The server half of one decision, whose client half is `PGSSLMODE` in the app environment (see the migrate
# job below, and `local.service_environment` in main.tf). `require_secure_transport` is on by default here,
# unlike RDS's parameter group — and it is stated anyway, for the reason the AWS stack states `force_ssl`:
# it puts the policy and the setting that satisfies it in one repository, where a reader who hits a refused
# connection can see both halves at once, and it stops a future product default from moving the ground
# silently in either direction.
#
# It is also the half that carries the guarantee. Three of the five backends ask for encryption explicitly;
# the two Java ones cannot be told through the environment at all — pgjdbc does not read `PGSSLMODE` — and
# rely on their driver's own default, `prefer`, which negotiates TLS but would fall back to plaintext
# against a server that allowed it. This resource is what makes sure none ever does.
resource "azurerm_postgresql_flexible_server_configuration" "require_tls" {
  count = local.database_wanted ? 1 : 0

  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.database[0].id
  value     = "ON"
}

resource "azurerm_postgresql_flexible_server_configuration" "minimum_tls" {
  count = local.database_wanted ? 1 : 0

  name      = "ssl_min_protocol_version"
  server_id = azurerm_postgresql_flexible_server.database[0].id
  value     = "TLSv1.2"
}

# `0.0.0.0` at both ends is the product's own spelling of "Azure services and resources inside this
# subscription", not "the internet": it is a documented sentinel, and it is what the Container Apps
# environment's outbound addresses fall under while there is no VNet to name instead. A laptop is not
# admitted, which is why `make migrate-remote` runs the migration as a job in the environment rather than
# from a terminal.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure" {
  count = local.database_wanted ? 1 : 0

  name             = "azure-services"
  server_id        = azurerm_postgresql_flexible_server.database[0].id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  count = local.database_wanted ? 1 : 0

  name      = "app"
  server_id = azurerm_postgresql_flexible_server.database[0].id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# The whole connection string, in the one shape every backend here reads — `DATABASE_URL`, libpq style.
#
# The address and the credentials, and nothing about TLS. No `?sslmode=…` here on purpose: one string is
# shared by five backends with three different driver semantics, and `sslmode` inside it means something
# different to each — for node-postgres it means *verify*, and what it parses from the string also
# overrides `PGSSLMODE`, closing off the route that does work. So encryption is asked for per backend in
# the app environment instead; `src/slipwai/images.py` (`POSTGRES_SSLMODE`) in the factory carries the full
# reasoning, the measurements behind the AWS row, and what is still owed for this one.
resource "azurerm_key_vault_secret" "database" {
  count = local.database_wanted ? 1 : 0

  name         = "DATABASE-URL"
  key_vault_id = azurerm_key_vault.secrets.id
  value = format(
    "postgres://%s:%s@%s:5432/%s",
    azurerm_postgresql_flexible_server.database[0].administrator_login,
    random_password.database[0].result,
    azurerm_postgresql_flexible_server.database[0].fqdn,
    azurerm_postgresql_flexible_server_database.app[0].name,
  )

  depends_on = [time_sleep.rbac]
}

# The migration runner: the service's own image (or the migrate image built beside it) run once as a job in
# the same environment as the app, started by `scripts/deploy.py` — which `make deploy` does *before* the
# service revision rolls, by applying these resources alone first, so an expand migration is in place when
# the new release arrives and the old one is still serving; `make migrate-remote ENV=…` does it on its own.
# Writing to a database stays an explicit act, exactly as it is locally; what changes in production is only
# where the command runs.
#
# `manual_trigger_config` and nothing else: a job with a schedule would migrate on a clock, which is the one
# thing a migration must not do.
resource "azurerm_container_app_job" "migrate" {
  for_each = local.migrating

  name                         = "${each.key}-migrate"
  resource_group_name          = azurerm_resource_group.environment.name
  location                     = azurerm_resource_group.environment.location
  container_app_environment_id = azurerm_container_app_environment.main.id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 900
  replica_retry_limit          = 0

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = var.registry_server
    identity = azurerm_user_assigned_identity.app.id
  }

  secret {
    name                = "database-url"
    identity            = azurerm_user_assigned_identity.app.id
    key_vault_secret_id = azurerm_key_vault_secret.database[0].id
  }

  # No flag transport here, deliberately. A migration is a schema change and the one thing it must not do
  # is behave differently depending on a flag: the expand-then-contract rule that `make check-migrations`
  # enforces is what makes a rollback safe, and a flag-gated migration would make "which shape is this
  # database in" depend on something flippable. So a migrate job reads the plain environment, and a flag
  # read inside one would answer off — which is the safe direction, and the reason this is stated rather
  # than left to be discovered.
  template {
    container {
      name   = "migrate"
      image  = each.value.migrate_image != null ? var.images[each.value.migrate_image] : var.images[each.key]
      cpu    = var.cpu
      memory = var.memory

      # `command` on its own is ignored. The image a buildpack builds — pack's, for both backends that
      # migrate this way — has a fixed entrypoint, `/cnb/process/web`, which starts the web process
      # whatever command it is handed: the job would serve instead of migrating, never exit, and
      # `scripts/deploy.py` would wait on it until the timeout above. The buildpack's launcher runs any
      # command with the image's PATH and environment in place, so the command is prefixed with it wherever
      # one is given (`tests/test_images.py` proves both halves). A migrate image — Go's `cmd/migrate`,
      # built by ko — is run as built, with the entrypoint it was given.
      command = each.value.migrate_command != null ? ["/cnb/lifecycle/launcher"] : []
      args    = each.value.migrate_command != null ? each.value.migrate_command : []

      # The same environment the long-running service gets (main.tf), not a subset of it, and that is the
      # point: a migration and the service it migrates for connect to the same database, so anything that
      # decides *how* they connect has to reach both. `PGSSLMODE` is the case that proves it — on the AWS
      # target this container once had secrets and no environment at all, so the client half of the TLS
      # policy could not reach the one task that runs first, and every first deploy failed here while the
      # service that would have failed the same way had not started yet. Sharing the map means the two can
      # never disagree again.
      #
      # `HOST`, `PORT` and `LOG_LEVEL` ride along and are inert: nothing in a migration binds a socket.
      dynamic "env" {
        for_each = local.service_environment[each.key]

        content {
          name  = env.key
          value = env.value
        }
      }

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
  }
}

output "migrate_jobs" {
  description = "What scripts/deploy.py starts to apply each service's migrations in this environment."
  value = {
    for name, job in azurerm_container_app_job.migrate : name => {
      name           = job.name
      resource_group = azurerm_resource_group.environment.name
    }
  }
}
# backing-service:postgres:end
