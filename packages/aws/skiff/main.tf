# The skiff's compute lives here and in its package row, not in the keel or the deploy workflow.
# One Lightsail service per application keeps independent readiness probes and private ECR pull roles.
# Environment values are visible to authorised Lightsail operators; these are not ECS secret references.
locals {
  service_environment = {
    for name, service in var.services : name => merge(
      { HOST = "0.0.0.0", PORT = tostring(service.port), LOG_LEVEL = "info" },
      service.environment,
      # backing-service:postgres:begin
      service.store == "rds" ? { DATABASE_URL = local.database_url } : {},
      # backing-service:postgres:end
      # backing-service:keycloak:begin
      service.auth == "cognito" ? merge(local.internal_environment, {
        OIDC_CLIENT_SECRET = one(aws_cognito_user_pool_client.internal[*].client_secret)
      }) : {},
      service.auth == "auth0" ? merge(local.auth0_internal_environment, {
        OIDC_CLIENT_SECRET = local.auth0_internal_wanted ? data.aws_secretsmanager_secret_version.identity[local.auth0_internal_secrets.OIDC_CLIENT_SECRET].secret_string : ""
      }) : {},
      # backing-service:keycloak:end
      # backing-service:users-keycloak:begin
      service.users == "cognito" ? local.external_environment : {},
      service.users == "auth0" ? local.auth0_external_environment : {},
      # backing-service:users-keycloak:end
      { for id, flag in local.flag_parameters : "FLAG_${replace(upper(flag.key), "-", "_")}" => aws_ssm_parameter.flag[id].value if flag.service == name },
    )
  }
  service_urls = { for name, service in aws_lightsail_container_service.service : name => trimsuffix(service.url, "/") }
}

resource "aws_lightsail_container_service" "service" {
  for_each = var.services
  name     = "${local.prefix}-${each.key}"
  power    = "nano"
  scale    = 1
  private_registry_access {
    ecr_image_puller_role {
      is_active = true
    }
  }
}

# This is the existing private repository, with only its service's image-puller principal added.
data "aws_ecr_repository" "service" {
  for_each = var.services
  name     = "${var.project}-${each.key}"
}

resource "aws_ecr_repository_policy" "pull" {
  for_each   = var.services
  repository = data.aws_ecr_repository.service[each.key].name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "SkiffImagePull"
      Effect    = "Allow"
      Principal = { AWS = aws_lightsail_container_service.service[each.key].private_registry_access[0].ecr_image_puller_role[0].principal_arn }
      Action    = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    }]
  })
}

resource "aws_lightsail_container_service_deployment_version" "service" {
  for_each     = var.services
  service_name = aws_lightsail_container_service.service[each.key].name
  container {
    container_name = each.key
    image          = var.images[each.key]
    environment    = local.service_environment[each.key]
    ports          = { (tostring(each.value.port)) = "HTTP" }
  }
  public_endpoint {
    container_name = each.key
    container_port = each.value.port
    health_check {
      path          = each.value.health_path
      success_codes = "200-299"
    }
  }
  depends_on = [aws_ecr_repository_policy.pull]
}

# backing-service:keycloak:begin
# Auth0 contributes secret ARNs; Lightsail has no ECS execution role to resolve them into environment values.
data "aws_secretsmanager_secret_version" "identity" {
  for_each  = toset(values(local.auth0_internal_secrets))
  secret_id = each.key
}
# backing-service:keycloak:end
