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
    auth0 = {
      source  = "auth0/auth0"
      version = "1.31.0"
    }
  }
  # Kept separate from the liner's key. A prepared shape transition must never reinterpret old state.
  backend "s3" {
    key          = "skiff-service.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}
provider "aws" {
  default_tags {
    tags = { Project = var.project, Environment = var.environment, ManagedBy = "opentofu" }
  }
}
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
locals {
  prefix = "${var.project}-${var.environment}"
}
