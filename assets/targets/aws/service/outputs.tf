output "url" {
  description = "What `make smoke URL=…` is given after a deploy: the site when there is one, else the first service."
  value       = local.public_url
}

output "urls" {
  description = "Every service's own HTTPS address: its CloudFront distribution, in front of its load balancer."
  value       = local.service_urls
}

# What the browser app is built with for this environment: Vite bakes VITE_* values into the bundle, so the
# bundle is built once per environment by scripts/deploy.py, from these. One output, contributed to by
# whichever customer-identity answer this project gave — at most one of them is ever non-empty.
output "web_environment" {
  description = "The VITE_* values the browser app is built with in this environment."
  value = merge(
    # backing-service:users-keycloak:begin
    local.cognito_web_environment,
    local.auth0_web_environment,
    # backing-service:users-keycloak:end
    {},
  )
}
