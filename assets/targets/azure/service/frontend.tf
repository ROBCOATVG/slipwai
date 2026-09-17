# The browser app: a static web app serving the bundle, with the service its `/api` goes to linked as the
# API backend. Same origin from the browser's point of view, which is what lets the bundle call `/api/...`
# relatively in every environment and never pay a CORS preflight, exactly as the Vite dev server arranges
# locally.
#
# What is *not* here is the point of the design. The AWS target writes a cache behaviour to route `/api/*`
# at the service and a function to serve `index.html` for the app's own routes; Static Web Apps does both
# by its own rule — it matches `/api` and proxies the entire path to the linked resource, and it serves the
# app's fallback document for a route that is not a file — so this file creates two resources and
# configures neither behaviour. The contract `vite.config.ts`, `flags.ts` and the generated `/api/flags`
# route rest on is the product's, not this stack's.
#
# Two consequences, both real and both stated rather than discovered:
#
#   - A linked container app **accepts only requests proxied through the site**, and may be linked to one
#     static web app at a time. So the api service has no public address of its own, where on AWS it also
#     has its own CloudFront distribution. That is stricter than the AWS shape, not weaker — but it means
#     `urls` does not carry that service, and the output below says so. Every other service is unlinked and
#     keeps its own address exactly as it would on AWS, because the site only ever fronted one of them.
#   - The Standard tier is what the linking needs; Free cannot do it. That is $9 an environment, and it is
#     also what buys the absence of a second, publicly reachable origin: there is no bucket here to keep
#     private, because the product serves its own content.
#
# scripts/deploy.py uploads the bundle with the `swa` CLI against a deployment token: hashed assets first,
# as immutable; `index.html` last, with `Cache-Control: no-store`, so it is the release pointer — and a
# copy under `releases/<commit>/` in the state container is what a rollback puts back.

# Static Web Apps is offered in a handful of regions rather than everywhere, so a project whose `location`
# is not one of them says where the site goes. Null means "the same region as everything else", which is
# right wherever it is offered and wrong loudly rather than quietly wherever it is not: the apply fails
# naming the region, at which point this variable is the fix.
variable "site_location" {
  description = "Where the static web app is created; null uses var.location. Static Web Apps is offered in a limited set of regions — westeurope, eastus2, westus2, centralus, eastasia — so set this where `location` is not one."
  type        = string
  default     = null
}

resource "azurerm_static_web_app" "web" {
  name                = "${local.short}-web"
  resource_group_name = azurerm_resource_group.environment.name
  location            = coalesce(var.site_location, var.location)
  # Standard, not Free: linking a container app as the API backend is a Standard feature, and the link is
  # the whole reason the site and the service share an origin.
  sku_tier = "Standard"
  sku_size = "Standard"

  # This repository is not connected to the site, deliberately: the bundle is uploaded by `make deploy`
  # from the commit the pipeline built, so the site never builds anything itself and never needs a token
  # with access to the repository. Preview environments are off for the same reason — nothing opens a pull
  # request against a site that has no repository.
  preview_environments_enabled = false
  # `staticwebapp.config.json` is the app's file and part of its bundle, so an upload may change it.
  configuration_file_changes_enabled = true
}

# The link itself, which azurerm has no resource for. `backendResourceId` is the container app; `region` is
# the container app's region, not the site's, and they differ wherever `site_location` is set.
resource "azapi_resource" "api_backend" {
  type      = "Microsoft.Web/staticSites/linkedBackends@2024-04-01"
  name      = "api"
  parent_id = azurerm_static_web_app.web.id

  body = {
    properties = {
      backendResourceId = azurerm_container_app.service[var.web.api].id
      region            = azurerm_resource_group.environment.location
    }
  }
}

locals {
  public_url = "https://${azurerm_static_web_app.web.default_host_name}"
  # Every service but the linked one. The linked one has an address and refuses everything that does not
  # arrive through the site, so `make smoke` and anything else reading `urls` would be given a 403 to ask.
  service_urls = { for name, url in local.all_service_urls : name => url if name != var.web.api }
}

output "web_site" {
  description = "The static web app scripts/deploy.py uploads the bundle to."
  value       = azurerm_static_web_app.web.name
}

output "web_deployment_token" {
  description = "What the `swa` CLI authenticates an upload with; scripts/deploy.py reads it from here rather than storing it on the forge."
  value       = azurerm_static_web_app.web.api_key
  sensitive   = true
}

output "web_api_service" {
  description = "The service linked as the site's API backend, which is therefore reachable only through the site and absent from `urls`."
  value       = var.web.api
}
