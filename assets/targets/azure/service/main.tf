# One Container App per application, on the Consumption profile, deployed by revision. This file is the
# service itself: the environment they share, the identity they run as, the app — which image, which port,
# what it is told about the infrastructure the other files provision for it — and how it scales. How
# traffic reaches it, and what a revision means for a rollback, are in ingress.tf.
#
# A deploy is a new revision rather than a new task definition, and traffic moves to it when it is ready:
# Container Apps will not route to a revision whose readiness probe has not passed, so the release serving
# now goes on serving until the new one answers. Revisions the release before this one left behind are what
# a rollback goes back to — `kept_revisions` decides how many stay running, and `variables.tf` has that
# trade — and `make rollback` is itself an apply of the previous digests, exactly as it is on AWS.
#
# The regions between `backing-service:<feature>:begin` and `:end` belong to one answer to one axis,
# exactly as they do in docker-compose.yml: `scripts/backing-services.py` removes a region with the answer
# that owns it, so `./init --event-store memory` takes the database's wiring out of here as well as the
# database out of postgres.tf.

locals {
  # What every service is told, then what its own backend needs in production (from
  # project.auto.tfvars.json), then what the target provisions for the answers it gave. The trailing `{}`
  # lets every region above it end with a comma and be removed whole.
  #
  # `service.environment` is the per-backend middle layer, and it is not only the framework switches it
  # started as: for a service whose store is a Flexible Server it also carries `PGSSLMODE`, because that
  # server refuses an unencrypted connection and each driver spells its TLS posture differently. The
  # factory's `src/slipwai/images.py` (`POSTGRES_SSLMODE`) has the argument and the measurements behind it,
  # per managed Postgres rather than per cloud, because the answer is a property of the server's
  # certificate chain. Read by the app below and by the migrate job, so the two cannot disagree about how
  # they reach the same database.
  service_environment = {
    for name, service in var.services : name => merge(
      {
        HOST      = "0.0.0.0"
        PORT      = tostring(service.port)
        LOG_LEVEL = "info"
      },
      service.environment,
      # backing-service:keycloak:begin
      service.auth == "entra" ? local.staff_environment : {},
      service.auth == "auth0" ? local.auth0_staff_environment : {},
      # backing-service:keycloak:end
      # backing-service:users-keycloak:begin
      service.users == "auth0" ? local.auth0_customers_environment : {},
      # backing-service:users-keycloak:end
      {},
    )
  }

  # Key Vault secret references, resolved by Container Apps into the replica's environment; the values
  # never appear in an app definition or in this state. Keyed by the container app's own secret name —
  # lowercase, hyphens, which is all that name may be — against the Key Vault secret it points at and the
  # environment variable it lands in.
  service_secrets = {
    for name, service in var.services : name => merge(
      # backing-service:postgres:begin
      service.store == "flexible-server" ? {
        "database-url" = { variable = "DATABASE_URL", id = one(azurerm_key_vault_secret.database[*].id) }
      } : {},
      # backing-service:postgres:end
      # backing-service:keycloak:begin
      service.auth == "entra" ? {
        "oidc-client-secret" = { variable = "OIDC_CLIENT_SECRET", id = one(azurerm_key_vault_secret.staff_client[*].id) }
      } : {},
      service.auth == "auth0" ? local.auth0_staff_secrets : {},
      # backing-service:keycloak:end
      {},
    )
  }
}

resource "azurerm_resource_group" "environment" {
  name     = local.prefix
  location = var.location
}

# Where the logs go. One workspace per environment rather than one for the project: at this volume two cost
# what one costs — the free allowance is per billing account, not per workspace — and staging and
# production not sharing one is most of what two long-lived environments are for.
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "${local.short}-logs"
  resource_group_name = azurerm_resource_group.environment.name
  location            = azurerm_resource_group.environment.location
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "production" ? 90 : 30
}

# The Container Apps environment: the boundary the apps share, the certificate their addresses are served
# under, and the ingress in front of them. There is no per-service load balancer to create and none to pay
# for — the environment's own ingress is what answers, on a managed certificate, which is the structural
# reason this target costs less per service than the AWS one.
resource "azurerm_container_app_environment" "main" {
  name                       = local.short
  resource_group_name        = azurerm_resource_group.environment.name
  location                   = azurerm_resource_group.environment.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  logs_destination           = "log-analytics"

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# One identity for every app in this environment, which is the Azure shape of the execution role ECS gives
# a service: it pulls the image, and — where the other files provision one — it reads the database URL and
# the flags out of Key Vault. One rather than one per service for the same reason AWS has one execution
# role per environment: the permissions are the environment's, not the application's.
resource "azurerm_user_assigned_identity" "app" {
  name                = "${local.short}-app"
  resource_group_name = azurerm_resource_group.environment.name
  location            = azurerm_resource_group.environment.location
}

resource "azurerm_role_assignment" "pull" {
  scope                = var.registry_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}

# ── Secrets ────────────────────────────────────────────────────────────────────────────────────────────

# One vault per environment: the database URL, the staff client's secret, and every feature flag. Always
# created, even where none of those exist yet, because a flag is added by whoever writes the code that
# reads one and a vault that appears on the day of the first flag is a resource nobody expected in that
# diff. An empty vault is billed per operation and performs none.
#
# RBAC rather than access policies: the same role assignments as everything else here, so who may read a
# secret is answered in one place and `az role assignment list` is the whole answer.
resource "azurerm_key_vault" "secrets" {
  name                       = substr("kv-${local.slug}-${var.environment}", 0, 24)
  resource_group_name        = azurerm_resource_group.environment.name
  location                   = azurerm_resource_group.environment.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  # Short in staging so a torn-down environment can be rebuilt under the same names the same day; the
  # minimum the product allows. Production keeps the default, and purge protection with it.
  soft_delete_retention_days = var.environment == "production" ? 90 : 7
  purge_protection_enabled   = var.environment == "production"
}

# Whoever is applying — the deploy identity in the pipeline, a person from a laptop — has Contributor on
# the subscription, which creates a vault and cannot read or write what is in one. The data plane is a
# separate grant, and this is it.
resource "azurerm_role_assignment" "secrets_writer" {
  scope                = azurerm_key_vault.secrets.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "secrets_reader" {
  scope                = azurerm_key_vault.secrets.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
  principal_type       = "ServicePrincipal"
}

# A role assignment is not effective the instant it is created — Azure takes some seconds to replicate one
# — and the very next thing this stack does on a first apply is write a secret into the vault it has just
# granted itself access to. Without this the first apply fails with a 403 that a second, identical apply
# would not, which is the worst kind of failure to hand somebody on their first deploy. `create_duration`
# runs once, when this resource is created, so no later apply pays it.
resource "time_sleep" "rbac" {
  create_duration = "40s"

  depends_on = [
    azurerm_role_assignment.secrets_writer,
    azurerm_role_assignment.secrets_reader,
  ]
}

resource "azurerm_container_app" "service" {
  for_each = var.services

  # The service's own name and nothing more: this resource group holds one environment's worth of one
  # project, so that is already unique, and a container app's name is capped at 32 characters where a
  # project's is capped at nothing.
  name                         = each.key
  resource_group_name          = azurerm_resource_group.environment.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Multiple"
  workload_profile_name        = "Consumption"
  max_inactive_revisions       = var.kept_revisions

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = var.registry_server
    identity = azurerm_user_assigned_identity.app.id
  }

  dynamic "secret" {
    for_each = merge(local.service_secrets[each.key], local.service_flags[each.key])

    content {
      name                = secret.key
      identity            = azurerm_user_assigned_identity.app.id
      key_vault_secret_id = secret.value.id
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = each.key
      image  = var.images[each.key]
      cpu    = var.cpu
      memory = var.memory

      # `flag_environment` is empty unless this environment reads its flags from App Configuration, in
      # which case it is the keys naming the store — read by `defaultSource` in the service's flag reader
      # and nowhere else. See `flags.tf`.
      dynamic "env" {
        for_each = merge(local.service_environment[each.key], local.flag_environment)

        content {
          name  = env.key
          value = env.value
        }
      }

      # Secrets and flags reach the container the same way — a Key Vault reference Container Apps resolves
      # when the replica starts — and differ only in what they are for and where they are declared.
      # `flags.tf` has the argument.
      dynamic "env" {
        for_each = merge(local.service_secrets[each.key], local.service_flags[each.key])

        content {
          name        = env.value.variable
          secret_name = env.key
        }
      }

      # What gates the traffic switch: a revision takes no requests until this has passed, which is how a
      # release that cannot start never becomes the one serving.
      readiness_probe {
        transport = "HTTP"
        port      = each.value.port
        path      = each.value.health_path
      }

      # And what gets a replica restarted, which is a different question: the process is up, or it is not.
      # Deliberately not the readiness path — a replica whose event store is unreachable is working and
      # waiting, and restarting it would turn somebody else's outage into a crash loop of this project's.
      liveness_probe {
        transport     = "HTTP"
        port          = each.value.port
        path          = each.value.liveness_path
        initial_delay = 10
      }
    }

    # Concurrency rather than CPU, because that is the scaler Container Apps has of its own: a replica is
    # added when the ones running are each handling this many requests at once. The floor and the ceiling
    # are the environment's tfvars, and this is the one rule a walking skeleton needs until its traffic
    # says otherwise.
    http_scale_rule {
      name                = "concurrency"
      concurrent_requests = "50"
    }
  }

  ingress {
    external_enabled = true
    target_port      = each.value.port
    transport        = "auto"

    # All of it to whatever this apply produced. A revision is created when the template changes — a new
    # image digest is a new template — and the platform names it, deliberately: a suffix must be unique for
    # the lifetime of the app, and `make rollback` re-applies a commit that has already had one. Letting
    # Container Apps hash the template means a rollback is an ordinary apply rather than a name collision
    # nobody hit until the second time they rolled back. Which commit a revision runs is the image tag on
    # it, and `make -s url` plus the release record in the state container are the rest of that answer.
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  lifecycle {
    precondition {
      condition     = contains(keys(var.images), each.key)
      error_message = "No image for ${each.key} in `images`: run `make push` and pass .build/images.json."
    }
  }

  depends_on = [azurerm_role_assignment.pull, time_sleep.rbac]
}
