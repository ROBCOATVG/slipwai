# No browser app, so the address of this environment is the first service's own. `add-frontend` replaces
# this file with frontend.tf, where the address becomes the CloudFront distribution in front of both.
locals {
  public_url = local.service_urls[keys(var.services)[0]]
}
