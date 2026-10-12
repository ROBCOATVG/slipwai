# How traffic reaches each service, and what a deploy does to that path.
#
# There is nothing here to create. A Container App declares its own ingress and the environment answers on
# a name of its own with a certificate of its own — `<app>.<environment>.<region>.azurecontainerapps.io`,
# HTTPS, managed and renewed by the platform — so where the AWS target creates a load balancer, two target
# groups, a listener, a rule and a CloudFront distribution *per service*, this file is a `locals` block
# reading an attribute. That is the whole of why a service costs what it costs here.
#
# A deploy is a revision. The new one starts beside the one serving, and the ingress does not route to it
# until its readiness probe passes; when it does, it takes all the traffic at once and the previous
# revision stops receiving any. Whether that previous revision goes on *running* is `kept_revisions`: one
# makes a rollback a change of traffic weight, none makes it a restart of the previous image. Either way
# `make rollback` is an apply of the previous digests, so the mechanism is the deploy's own.
#
# A domain of this project's own is what changes this file: a custom domain on the environment, a managed
# certificate, and these addresses become names somebody chose.

locals {
  # The service's own address, for anything outside the environment that fronts it, and the same thing as
  # an HTTPS URL. *Every* service, including one linked to a static web app — which is why `service_urls`,
  # the output, is narrowed from this in `frontend.tf`: a linked service has this address and refuses
  # everything that does not arrive through the site, so publishing it would be publishing a 403.
  service_origins  = { for name, app in azurerm_container_app.service : name => app.ingress[0].fqdn }
  all_service_urls = { for name, app in azurerm_container_app.service : name => "https://${app.ingress[0].fqdn}" }
}
