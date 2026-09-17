# The other half of `auth0.tf`, for a project that answered neither identity axis with Auth0.
#
# The Auth0 provider is configured the moment anything in the module refers to it, whether or not the
# resource has any instances — a `count = 0` resource is enough — and it refuses to configure without a
# tenant credential. So a project that does not use Auth0 must not carry the provider at all, and the two
# files are chosen between at generation time exactly as `frontend.tf` and `no-frontend.tf` are. Only one
# is ever written, and it is always written as `auth0.tf`.
#
# What is left is the four names `main.tf` and `outputs.tf` refer to unconditionally, each answering
# "nothing". Naming them here rather than guarding every use keeps the merge in `main.tf` one expression
# with one shape, whichever answer this project gave.
locals {
  auth0_staff_wanted          = false
  auth0_staff_environment     = {}
  auth0_staff_secrets         = {}
  auth0_customers_environment = {}
  auth0_web_environment       = {}
}
