# Everything the pipeline is configured with, which `make bootstrap` writes to the repository on the forge.
# Repository *variables* for the identifiers, which are not confidential; a repository *secret* for the one
# client secret, which exists only on a forge without OIDC.
output "location" {
  description = "AZURE_LOCATION: the region every stack creates in."
  value       = azurerm_resource_group.bootstrap.location
}

output "subscription_id" {
  description = "AZURE_SUBSCRIPTION_ID: the subscription everything lives in."
  value       = data.azurerm_client_config.current.subscription_id
}

output "tenant_id" {
  description = "AZURE_TENANT_ID: the directory the deploy identity belongs to."
  value       = data.azurerm_client_config.current.tenant_id
}

output "state_resource_group" {
  description = "TOFU_STATE_RESOURCE_GROUP: the group holding the state account."
  value       = azurerm_resource_group.bootstrap.name
}

output "state_storage_account" {
  description = "TOFU_STATE_ACCOUNT: where the service stack keeps its state and its release records."
  value       = azurerm_storage_account.state.name
}

output "state_container" {
  description = "TOFU_STATE_CONTAINER: the blob container inside that account."
  value       = azurerm_storage_container.state.name
}

output "deploy_client_id" {
  description = "AZURE_CLIENT_ID: what the deploy workflow signs in as."
  value       = local.deploy_client_id
}

output "image_registry" {
  description = "IMAGE_REGISTRY: the prefix `make build` puts before `<project>-<service>:<commit>`."
  value       = "${azurerm_container_registry.images.login_server}/"
}

output "registry_name" {
  description = "AZURE_REGISTRY_NAME: what `az acr login` in the build job is given."
  value       = azurerm_container_registry.images.name
}

output "registry_id" {
  description = "AZURE_REGISTRY_ID: what the service stack scopes the container apps' AcrPull assignment to."
  value       = azurerm_container_registry.images.id
}

output "deploy_client_secret" {
  description = "AZURE_CLIENT_SECRET, a repository secret — only when the pipeline signs in with a secret."
  value       = local.secret ? azuread_service_principal_password.deploy[0].value : null
  sensitive   = true
}
