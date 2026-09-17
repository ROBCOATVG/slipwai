output "url" {
  description = "What `make smoke URL=…` is given after a deploy: the site when there is one, else the first service."
  value       = local.public_url
}

# What the browser app is built with for this environment: Vite bakes VITE_* values into the bundle, so the
# bundle is built once per environment by scripts/deploy.py, from these. Empty unless this project answered
# the customer-identity axis, which under this target means Auth0.
output "web_environment" {
  description = "The VITE_* values the browser app is built with in this environment."
  value = merge(
    # backing-service:users-keycloak:begin
    local.auth0_web_environment,
    # backing-service:users-keycloak:end
    {},
  )
}

output "urls" {
  description = "Every *publicly reachable* service's own HTTPS address: the Container Apps environment's ingress, on its managed certificate. A service linked to the site as its API backend is deliberately absent — it answers only through the site, and `web_api_service` names it."
  value       = local.service_urls
}
