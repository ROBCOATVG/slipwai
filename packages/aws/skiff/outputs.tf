output "url" {
  value = local.public_url
}
output "urls" {
  value = local.service_urls
}
output "containers" {
  value = { for name, service in aws_lightsail_container_service.service : name => service.name }
}
output "migration_environment" {
  value     = local.service_environment
  sensitive = true
}
# backing-service:postgres:begin
output "database_name" {
  value = local.database_wanted ? aws_lightsail_database.database[0].relational_database_name : null
}
# backing-service:postgres:end

output "web_environment" {
  value = merge(
    # backing-service:users-keycloak:begin
    local.cognito_web_environment, local.auth0_web_environment,
    # backing-service:users-keycloak:end
    {},
  )
}
