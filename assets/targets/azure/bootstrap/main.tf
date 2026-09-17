# The one stack a person applies, once, with administrator credentials — everything the pipeline needs
# before it can run and cannot create for itself: where state lives, who the pipeline is allowed to be, and
# where images go. `make bootstrap` applies it and then configures the repository on the forge from its
# outputs (scripts/bootstrap.py); infra/README.md is the walk-through, and the variables are what the script
# decides for you.
#
# Its own state is committed to this repository, encrypted with OpenTofu's native state encryption under a
# passphrase the script generates once and prints, so there is no imperative "create the storage account
# first" step and nothing to bootstrap the bootstrap. Without the passphrase the file is noise; with it,
# `tofu output` here is the source of every identifier the pipeline is configured with.

terraform {
  required_version = ">= 1.12.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.5.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "3.9.0"
    }
  }

  encryption {
    key_provider "pbkdf2" "state" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "state" {
      keys = key_provider.pbkdf2.state
    }

    state {
      method   = method.aes_gcm.state
      enforced = true
    }

    plan {
      method   = method.aes_gcm.state
      enforced = true
    }
  }
}

# The subscription comes from ARM_SUBSCRIPTION_ID or the signed-in `az` CLI's default, deliberately: it is
# an identifier the pipeline carries as a repository variable, and one place to say it is one place to move
# it.
#
# Registering resource providers is this stack's job and not the service stack's, because it is a
# subscription-wide act an administrator performs and the deploy identity is deliberately not one. From
# azurerm 5.0 nothing is registered automatically (`resource_provider_registrations` defaults to `none`),
# so a first apply into a fresh subscription would otherwise fail on whichever namespace it reached first
# — and fail from the pipeline, halfway through, rather than here where a person is watching.
provider "azurerm" {
  features {}

  resource_providers_to_register = [
    "Microsoft.App",
    "Microsoft.AppConfiguration",
    "Microsoft.ContainerRegistry",
    "Microsoft.DBforPostgreSQL",
    "Microsoft.KeyVault",
    "Microsoft.ManagedIdentity",
    "Microsoft.OperationalInsights",
    "Microsoft.Storage",
    "Microsoft.Web",
  ]
}

provider "azuread" {}

data "azurerm_client_config" "current" {}

locals {
  # Storage accounts and container registries are named globally, in lowercase letters and digits only, and
  # capped at 24 and 50 characters. A project name may carry `-`, `.` and `_` and be longer than either, so
  # the name is a slug of it plus a digest of the subscription it lives in — which is what keeps two
  # products with one name apart, the way the account id does on AWS, and is stable across applies.
  slug   = substr(replace(lower(var.project), "/[^a-z0-9]/", ""), 0, 14)
  unique = substr(sha1("${data.azurerm_client_config.current.subscription_id}/${var.project}"), 0, 8)
}

resource "azurerm_resource_group" "bootstrap" {
  name     = "${var.project}-bootstrap"
  location = var.location
}

# ── State ──────────────────────────────────────────────────────────────────────────────────────────────

# The service stack's backend. Entra ID authentication only — `shared_access_key_enabled = false` means
# there is no account key to leak and no account key for anything to be configured with, so the deploy
# identity reaches this through its own role assignment below and nothing else can.
#
# The lock is the blob's own lease, taken by the backend for the length of an apply: no second resource, no
# table to create, nothing to clean up after an interrupted run beyond breaking a lease.
resource "azurerm_storage_account" "state" {
  name                            = substr("st${local.slug}${local.unique}", 0, 24)
  resource_group_name             = azurerm_resource_group.bootstrap.name
  location                        = azurerm_resource_group.bootstrap.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  public_network_access           = "Enabled"

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "state" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"
}

# ── Who the pipeline is ────────────────────────────────────────────────────────────────────────────────

# One deploy principal either way; what differs per forge is how the pipeline gets to be it.
#
# On GitHub, a user-assigned managed identity with federated credentials and no stored credential at all:
# the credentials name this repository's main branch and its two deployment environments and nothing else,
# so a fork, a pull request or another repository in the same organisation cannot become it. A managed
# identity is an ARM resource, so this path asks nothing of the directory — an administrator of the
# subscription can apply it without being able to write to Entra at all.
#
# On a forge without OIDC federation (Gitea), an app registration and its service principal, one client
# secret stored as the repository's secrets — the weaker shape, and the one that does need directory
# permission, which is why it is only ever created for the forge that needs it. `make bootstrap` picks by
# reading the repository's remote.
locals {
  oidc   = var.deploy_with == "oidc"
  secret = var.deploy_with == "access-key"

  # What a federated credential matches on has to be the `sub` the token will actually carry, and that is
  # GitHub's to decide, not ours: an organisation can have the immutable form turned on, in which case
  # every token says `repo:owner@<owner id>/name@<repo id>:ref:refs/heads/main` and a credential naming
  # `repo:owner/name` matches nothing. Entra's subjects are exact strings with no wildcards, so a
  # near-miss is a refusal at sign-in with three credentials that read correctly. `make bootstrap` asks the
  # repository's OIDC customization endpoint what the prefix is and passes it here; `repo:<repository>` is
  # only the fallback for when the forge cannot be asked.
  subject_prefix = var.oidc_subject_prefix != "" ? var.oidc_subject_prefix : "repo:${var.repository}"

  # Three subjects, because GitHub does not issue one shape for every job. A job with no `environment:`
  # gets `<prefix>:ref:refs/heads/main`; a job that declares one gets `<prefix>:environment:<name>`
  # *instead*, with no ref in it at all. A trust naming only the ref form lets `deploy.yml`'s build job
  # sign in while its `staging` and `production` jobs — and `production.yml` and `rollback.yml`, which are
  # environment jobs throughout — are refused before `make deploy` ever runs.
  #
  # The environment set is closed: `infra/service/variables.tf` admits `staging` and `production` and
  # refuses anything else, so the two are listed. Entra has no wildcard to be tempted by here, which is the
  # posture AWS chose on purpose anyway.
  #
  # An environment subject carries no ref, so what keeps these two to main is not in this stack: each
  # environment is created with a deployment branch policy naming `main`, so GitHub refuses to start a job
  # pointed at it from any other branch and never mints such a token. `make bootstrap` does that
  # (`scripts/bootstrap.py`, `ensure_environments`), and it is the half of this that `rollback.yml` needs —
  # a `workflow_dispatch` can be run from a branch.
  subjects = {
    main       = "${local.subject_prefix}:ref:refs/heads/main"
    staging    = "${local.subject_prefix}:environment:staging"
    production = "${local.subject_prefix}:environment:production"
  }
}

resource "azurerm_user_assigned_identity" "deploy" {
  count = local.oidc ? 1 : 0

  name                = "${var.project}-deploy"
  resource_group_name = azurerm_resource_group.bootstrap.name
  location            = azurerm_resource_group.bootstrap.location
}

resource "azurerm_federated_identity_credential" "deploy" {
  for_each = local.oidc ? local.subjects : {}

  name                      = "github-${each.key}"
  user_assigned_identity_id = azurerm_user_assigned_identity.deploy[0].id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = each.value
}

# The two *directory* objects this stack creates, and it creates them only on the access-key path — a forge
# without OIDC federation has nothing else to sign in with. Owner of the subscription grants nothing here:
# an app registration is outside subscription RBAC entirely, which `infra/README.md` now lists as a
# prerequisite of this path and not only of the staff-identity answer.
#
# `owners` is stated rather than left to Graph's default. Where a caller manages applications under the
# narrow owned-applications permission rather than a directory-wide one, creating the service principal for
# an application it does not own is refused — and the refusal names the backing application rather than the
# permission, so it reads as though the application were in another tenant. Naming the caller as owner of
# both is the difference between that and a clean apply, and it costs nothing where the caller is an
# administrator anyway.
data "azuread_client_config" "current" {}

resource "azuread_application" "deploy" {
  count = local.secret ? 1 : 0

  display_name = "${var.project}-deploy"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "deploy" {
  count = local.secret ? 1 : 0

  client_id = azuread_application.deploy[0].client_id
  owners    = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal_password" "deploy" {
  count = local.secret ? 1 : 0

  service_principal_id = azuread_service_principal.deploy[0].id
}

locals {
  # Whichever principal exists, so every role assignment below is written once.
  deploy_principal_id = local.oidc ? one(azurerm_user_assigned_identity.deploy[*].principal_id) : one(azuread_service_principal.deploy[*].object_id)
  deploy_client_id    = local.oidc ? one(azurerm_user_assigned_identity.deploy[*].client_id) : one(azuread_application.deploy[*].client_id)
}

# Contributor everywhere in the subscription, because the service stack creates a resource group per
# environment and a resource group cannot be created from inside one. Narrow this to two named groups once
# the service stack has settled: `tofu plan` lists exactly what it touches.
resource "azurerm_role_assignment" "deploy_contributor" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Contributor"
  principal_id         = local.deploy_principal_id
  principal_type       = "ServicePrincipal"
}

# Contributor cannot grant access, and the service stack has to: the container app is given AcrPull on this
# registry and a reader role on its own Key Vault, which are role assignments like any other. This is the
# Azure shape of the IAM the AWS deploy role is handed back on top of PowerUserAccess — the narrower of the
# two roles that can do it, so the pipeline can manage access and nothing else about identity.
resource "azurerm_role_assignment" "deploy_rbac" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = local.deploy_principal_id
  principal_type       = "ServicePrincipal"
}

# The state. Contributor on the subscription is control-plane only — it does not read a blob — and with no
# account key to fall back on this assignment is the whole of how the backend authenticates.
resource "azurerm_role_assignment" "deploy_state" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.deploy_principal_id
  principal_type       = "ServicePrincipal"
}

# ── Images ─────────────────────────────────────────────────────────────────────────────────────────────

# One registry for the project, rather than one repository per service: a container registry holds every
# repository it is pushed and creates them on first push, so `add-service` needs nothing here — which is
# why `var.services` is read by this stack only to keep one tfvars file serving both.
#
# Two things AWS gets from ECR that the Basic tier does not have, both recorded rather than worked around:
# **immutable tags**, which are a registry-wide policy only on Premium, so a rebuild of a commit would
# replace that commit's image instead of being refused; and **untagged-manifest retention**, also Premium,
# so nothing here expires the layers a rebuild orphans. The pipeline is the only thing that pushes and it
# pushes the commit it checked out, so neither is reachable by accident — but neither is refused either,
# and `docs/adr/0002-production-target.md` says so.
resource "azurerm_container_registry" "images" {
  name                = substr("acr${local.slug}${local.unique}", 0, 50)
  resource_group_name = azurerm_resource_group.bootstrap.name
  location            = azurerm_resource_group.bootstrap.location
  sku                 = "Basic"
  admin_enabled       = false
}

# The build job pushes; the container apps pull with an identity the service stack grants.
resource "azurerm_role_assignment" "deploy_push" {
  scope                = azurerm_container_registry.images.id
  role_definition_name = "AcrPush"
  principal_id         = local.deploy_principal_id
  principal_type       = "ServicePrincipal"
}

# ── The directory ──────────────────────────────────────────────────────────────────────────────────────

# backing-service:keycloak:begin
# The one permission in this stack that is not a subscription's to grant. An Entra ID app registration is a
# *directory* object, outside the subscription's RBAC entirely, so Owner of the subscription does not let
# the pipeline create one — which is the structural difference between provisioning identity here and
# provisioning Cognito on AWS, where a user pool is an ordinary account resource.
#
# `Application.ReadWrite.OwnedBy` is the narrow answer: it lets the deploy identity create app
# registrations and manage the ones it owns, and nothing else in the directory. It does not let it read
# users, write groups, or touch an application somebody else made. Granting it needs a Privileged Role
# Administrator or a Global Administrator, which is why `make bootstrap` says so before it applies and why
# `infra/README.md` lists it as a prerequisite of the staff-identity answer rather than of the target.
#
# This region goes with the `keycloak` feature, so a project that answered `--auth none` has no such grant:
# the permission arrives with the answer that needs it, and with nothing else.
data "azuread_application_published_app_ids" "well_known" {}

# Microsoft's own service principal for the Graph API — **read, never written**. It is already in every
# tenant, so the temptation is a resource with `use_existing = true`; that adopts it and then reconciles it
# on every apply, and updating a first-party Microsoft object is refused to everybody, Global Administrator
# included. It fails with `Authorization_RequestDenied` after the roles and the registry are already made,
# which is the worst place to find out. A data source asks for the two things this needs — the role's id
# and the object to assign it on — and writes nothing.
data "azuread_service_principal" "msgraph" {
  client_id = data.azuread_application_published_app_ids.well_known.result.MicrosoftGraph
}

resource "azuread_app_role_assignment" "deploy_applications" {
  app_role_id         = data.azuread_service_principal.msgraph.app_role_ids["Application.ReadWrite.OwnedBy"]
  principal_object_id = local.deploy_principal_id
  resource_object_id  = data.azuread_service_principal.msgraph.object_id
}
# backing-service:keycloak:end
