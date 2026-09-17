# One module, two long-lived environments: `staging` and `production` are OpenTofu workspaces over this
# directory, applied in that order by `.github/workflows/deploy.yml` and by `make deploy ENV=<env>`. The
# state lives in the storage account the bootstrap stack created; scripts/deploy.py passes the account, the
# container and the resource group at `init`, so nothing here names a subscription.
terraform {
  required_version = ">= 1.12.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.9.0"
    }
    # The third party on the identity axes. Declared whether or not this project chose it — a module may
    # have only one `required_providers` block, so the pin cannot travel with the answer the way the
    # resources do. Declaring a provider does not configure one: `auth0.tf` holds the `provider` block and
    # every resource, and a project that answered neither identity axis with Auth0 carries `no-auth0.tf`
    # under that name instead, which refers to the provider nowhere and so never asks it for a credential.
    auth0 = {
      source  = "auth0/auth0"
      version = "1.31.0"
    }
    # For the one thing azurerm has no resource for: linking a container app to a static web app as its API
    # backend (`frontend.tf`). Declared whether or not this project has a browser app, the way `random` is
    # declared whether or not it has a database — a pruned project keeps a provider it no longer calls, and
    # that is cheaper than a `required_providers` block that changes shape with the answers.
    azapi = {
      source  = "Azure/azapi"
      version = "2.12.0"
    }
    # An app registration is a directory object rather than a subscription resource, so the staff identity
    # answer is this provider's rather than azurerm's — and so is the permission the bootstrap stack grants
    # the deploy identity to create one.
    azuread = {
      source  = "hashicorp/azuread"
      version = "3.9.0"
    }
    # One resource, `time_sleep`, and only for the RBAC replication delay main.tf explains. Nothing else
    # here waits on a clock.
    time = {
      source  = "hashicorp/time"
      version = "0.13.1"
    }
  }

  # Entra ID for the state as well as for everything else: the bootstrap account has no shared key to
  # configure this with, and the deploy identity's `Storage Blob Data Contributor` assignment is the whole
  # of how this reaches it. The lock is an exclusive lease on the state blob, taken for the length of an
  # apply — no lock table, no second resource, and nothing to clean up after an interrupted run beyond
  # breaking a lease.
  backend "azurerm" {
    key              = "service.tfstate"
    use_azuread_auth = true
  }
}

# `resource_provider_registrations` defaults to `none` from azurerm 5.0, and that is the right answer here:
# registering a provider is a subscription-wide act, the bootstrap stack does it once with administrator
# credentials, and the deploy identity is deliberately not an administrator.
provider "azurerm" {
  features {}
}

provider "azapi" {}

provider "azuread" {}

data "azurerm_client_config" "current" {}

locals {
  # Azure resource names take letters, digits and hyphens where a project name may also carry `.` and `_`,
  # and a good many of them are capped at 32 characters. Everything here lives in a resource group of its
  # own per environment, so a name only has to be unique among this project's own resources — `short` is
  # for a human reading the portal, and it is trimmed rather than hashed for the same reason.
  slug   = trimsuffix(replace(lower(var.project), "/[^a-z0-9]+/", "-"), "-")
  prefix = "${local.slug}-${var.environment}"
  short  = trimsuffix(substr(local.prefix, 0, 32), "-")
}
