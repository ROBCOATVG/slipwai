# The one stack a person applies, once, with administrator credentials — everything the pipeline needs
# before it can run and cannot create for itself: where state lives, who the pipeline is allowed to be, and
# where images go. `make bootstrap` applies it and then configures the repository on the forge from its
# outputs (scripts/bootstrap.py); infra/README.md is the walk-through, and the variables below are what the
# script decides for you.
#
# Its own state is committed to this repository, encrypted with OpenTofu's native state encryption under a
# passphrase the script generates once and prints, so there is no imperative "create the bucket first" step
# and nothing to bootstrap the bootstrap. Without the passphrase the file is noise; with it, `tofu output`
# here is the source of every identifier the pipeline is configured with.

terraform {
  required_version = ">= 1.12.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.61.0"
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

# The region comes from AWS_REGION in the environment, deliberately: it is an identifier the pipeline carries
# as a repository variable, and one place to say it is one place to move it.
provider "aws" {}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
  region  = data.aws_region.current.region
  # A second ECR repository for a service whose migrations run from an image of their own (Go's
  # `cmd/migrate`, built by ko beside `cmd/serve`).
  repositories = merge(
    var.services,
    { for name, service in var.services : "${name}-migrate" => service if service.migrate_image != null },
  )
}

# ── State ──────────────────────────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "state" {
  # Bucket names are global, so the account id is what keeps two products with one name apart.
  bucket = "${var.project}-${local.account}-tofu-state"
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3-native locking writes a lock object beside each state on every plan and apply, and versioning keeps a
# copy of each one; this is what stops those copies accumulating forever.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# ── Who the pipeline is ────────────────────────────────────────────────────────────────────────────────

# One deploy role either way; what differs per forge is how the pipeline gets to be it.
#
# On GitHub, with a short-lived OIDC token and no stored credential at all: the trust names this
# repository's main branch and its two deployment environments and nothing else, so a fork, a pull request
# or another repository in the same organisation cannot assume the role. On a forge without OIDC federation
# (Gitea), an IAM user whose only permission is to assume this role, its access key stored as the
# repository's secrets — the weaker shape, and still one role as the permission boundary. `make bootstrap`
# picks by reading the repository's remote.
locals {
  oidc = var.deploy_with == "oidc"
  key  = var.deploy_with == "access-key"

  # What the trust matches on has to be the `sub` the token will actually carry, and that is GitHub's to
  # decide, not ours: an organisation can have the immutable form turned on, in which case every token says
  # `repo:owner@<owner id>/name@<repo id>:ref:refs/heads/main` and a trust naming `repo:owner/name` matches
  # nothing — `Not authorized to perform sts:AssumeRoleWithWebIdentity`, with a trust policy that reads
  # correctly. So `make bootstrap` asks the repository's OIDC customization endpoint what the prefix is and
  # passes it here; `repo:<repository>` is only the fallback for when the forge cannot be asked.
  subject_prefix = var.oidc_subject_prefix != "" ? var.oidc_subject_prefix : "repo:${var.repository}"
}

resource "aws_iam_openid_connect_provider" "github" {
  count = local.oidc ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_user" "deploy" {
  count = local.key ? 1 : 0

  name = "${var.project}-deploy"
}

resource "aws_iam_access_key" "deploy" {
  count = local.key ? 1 : 0

  user = aws_iam_user.deploy[0].name
}

# `configure-aws-credentials` tags the session it opens (repository, workflow, commit...), which is what lets
# CloudTrail say which run assumed the role. Tagging is a second action, and it has to be allowed on both sides:
# here and in the trust policy below. AssumeRoleWithWebIdentity takes no tags from the caller, so the OIDC
# branch needs nothing extra.
data "aws_iam_policy_document" "deploy_user" {
  count = local.key ? 1 : 0

  statement {
    actions   = ["sts:AssumeRole", "sts:TagSession"]
    resources = [aws_iam_role.deploy.arn]
  }
}

resource "aws_iam_user_policy" "deploy" {
  count = local.key ? 1 : 0

  name   = "assume-the-deploy-role"
  user   = aws_iam_user.deploy[0].name
  policy = data.aws_iam_policy_document.deploy_user[0].json
}

data "aws_iam_policy_document" "deploy_trust" {
  dynamic "statement" {
    for_each = local.oidc ? [1] : []

    content {
      actions = ["sts:AssumeRoleWithWebIdentity"]

      principals {
        type        = "Federated"
        identifiers = [aws_iam_openid_connect_provider.github[0].arn]
      }

      condition {
        test     = "StringEquals"
        variable = "token.actions.githubusercontent.com:aud"
        values   = ["sts.amazonaws.com"]
      }

      # Three subjects, because GitHub does not issue one shape for every job. A job with no `environment:`
      # gets `<prefix>:ref:refs/heads/main`; a job that declares one gets `<prefix>:environment:<name>`
      # *instead*, with no ref in it at all. That is why a trust naming only the ref form let `deploy.yml`'s
      # build job assume this role while its `staging` and `production` jobs — and `production.yml` and
      # `rollback.yml`, which are environment jobs throughout — were refused before `make deploy` ever ran.
      #
      # The environment set is closed: `infra/service/variables.tf` admits `staging` and `production` and
      # refuses anything else, so the two are listed rather than matched with `environment:*`. A wildcard
      # here would trust whatever environment anybody adds to the repository later, which is a permission
      # granted by creating one.
      #
      # An environment subject carries no ref, so what keeps these two to main is not in this document: each
      # environment is created with a deployment branch policy naming `main`, so GitHub refuses to start a
      # job pointed at it from any other branch and never mints such a token. `make bootstrap` does that
      # (`scripts/bootstrap.py`, `ensure_environments`), and it is the half of this that `rollback.yml`
      # needs — a `workflow_dispatch` can be run from a branch.
      condition {
        test     = "StringLike"
        variable = "token.actions.githubusercontent.com:sub"
        values = [
          "${local.subject_prefix}:ref:refs/heads/main",
          "${local.subject_prefix}:environment:staging",
          "${local.subject_prefix}:environment:production",
        ]
      }
    }
  }

  dynamic "statement" {
    for_each = local.key ? [1] : []

    content {
      actions = ["sts:AssumeRole", "sts:TagSession"]

      principals {
        type        = "AWS"
        identifiers = [aws_iam_user.deploy[0].arn]
      }
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${var.project}-deploy"
  assume_role_policy = data.aws_iam_policy_document.deploy_trust.json
}

# PowerUserAccess is everything but IAM, and the service stack has to create the three roles ECS runs under
# — so the deploy role gets IAM back, scoped to roles carrying this project's name. Narrow this further once
# the service stack has settled: `tofu plan` lists exactly what it touches.
resource "aws_iam_role_policy_attachment" "deploy_power_user" {
  role       = aws_iam_role.deploy.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

data "aws_iam_policy_document" "deploy_iam" {
  statement {
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:UpdateRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:PassRole",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
    ]
    resources = ["arn:aws:iam::${local.account}:role/${var.project}-*"]
  }

  # ECS, RDS and CloudFront create their own service-linked roles the first time they are used in an account.
  statement {
    actions   = ["iam:CreateServiceLinkedRole"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy_iam" {
  name   = "iam-for-this-project"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_iam.json
}

# ── Images ─────────────────────────────────────────────────────────────────────────────────────────────

# One repository per service, named `<project>-<service>` — the name `make build` gives an image. Tags are
# immutable: a tag is the commit that built the image, and rebuilding a commit is a defect worth refusing.
resource "aws_ecr_repository" "service" {
  for_each = local.repositories

  name                 = "${var.project}-${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "service" {
  for_each = aws_ecr_repository.service

  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 30 images; a rollback reaches back one release, not thirty"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 30
      }
      action = { type = "expire" }
    }]
  })
}
