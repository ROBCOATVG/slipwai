# Everything the pipeline is configured with, which `make bootstrap` writes to the repository on the forge.
# Repository *variables* for the identifiers, which are not confidential; repository *secrets* for the two
# access-key outputs, which exist only on a forge without OIDC.
output "region" {
  value = local.region
}

output "state_bucket" {
  description = "TOFU_STATE_BUCKET: where the service stack keeps its state and its release records."
  value       = aws_s3_bucket.state.bucket
}

output "deploy_role_arn" {
  description = "AWS_DEPLOY_ROLE_ARN: what the deploy workflow assumes."
  value       = aws_iam_role.deploy.arn
}

output "image_registry" {
  description = "IMAGE_REGISTRY: the prefix `make build` puts before `<project>-<service>:<commit>`."
  value       = "${local.account}.dkr.ecr.${local.region}.amazonaws.com/"
}

output "deploy_access_key_id" {
  description = "AWS_ACCESS_KEY_ID, a repository secret — only when the pipeline signs in with a key."
  value       = local.key ? aws_iam_access_key.deploy[0].id : null
}

output "deploy_secret_access_key" {
  description = "AWS_SECRET_ACCESS_KEY, a repository secret — only when the pipeline signs in with a key."
  value       = local.key ? aws_iam_access_key.deploy[0].secret : null
  sensitive   = true
}
