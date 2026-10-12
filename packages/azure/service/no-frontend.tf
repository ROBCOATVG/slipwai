# No browser app, so the address of this environment is the first service's own. `add-frontend` replaces
# this file with frontend.tf, where the address becomes the static web app in front of both.
locals {
  # Nothing is linked, so every service answers on its own address and every one of them is published.
  service_urls = local.all_service_urls
  public_url   = local.all_service_urls[keys(var.services)[0]]
}
