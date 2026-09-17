# One module, two long-lived environments: `staging` and `production` are OpenTofu workspaces over this
# directory, applied in that order by `.github/workflows/deploy.yml` and by `make deploy ENV=<env>`. The
# state lives in the bucket the bootstrap stack created; scripts/deploy.py passes the bucket and the region
# at `init`, so nothing here names an account.
terraform {
  required_version = ">= 1.12.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.61.0"
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
  }

  backend "s3" {
    key          = "service.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "opentofu"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  prefix = "${var.project}-${var.environment}"
}
