# Feature flags: the one thing about a running service this environment can change without a deploy.
#
# A flag's value lives in an SSM parameter, and ECS resolves it into the container's environment exactly the
# way it resolves a secret — so a service reads `FLAG_<KEY>` at start-up like any other variable and needs
# no AWS SDK, no client, and no code that knows this file exists. That is what makes flags cost a generated
# project nothing in whichever language it was generated in.
#
# What it buys, and what it does not: `make flag` writes the parameter and restarts the service, so a flip
# is a rolling restart — around two minutes, no build, no apply, and no merge to `main`. It is not a live
# re-read, and that is the one thing this shape cannot do.
#
# When a flag has to move without a restart, `flag_transport = "appconfig"` in an environment's own tfvars
# is the other shape below: an AppConfig agent beside the container, read over loopback, and a flip that
# takes effect in seconds. It is per environment rather than per project, so an environment takes the
# sidecar on when it needs it and not before. `variable "flag_transport"` has the trade.
#
# A browser app reads the same flag by asking the service for it, over `GET /api/flags`, which the service
# answers from the very environment these parameters land in. So one product flag has one name and one
# value on both sides of `/api`, and the restart above is the whole of a flip: a browser already open picks
# the new value up on its next load, and no deploy is owed.
#
# It was not always so, and the reason is worth keeping. Vite inlines a `VITE_`-prefixed value while the
# bundle is *built*, so a flag compiled into a bundle is a property of that build and not of the
# environment it runs in — which gave one flag two clocks, the service's moving in a restart and the
# browser's only on the next deploy. Every screen gated on a flag then carried an ordering rule (on in the
# service first, off in the bundle first) that existed only because of how the value arrived. Asking the
# service removes the second clock, and with it the rule.
#
# `make rollback` no longer diverges here either. It restores the previous release's `index.html`, and that
# bundle carries no flag values at all, so the browser and the service both read whatever this environment
# is set to now — which is what a rollback should leave alone, the parameter being the one place a flip is
# recorded.
#
# One parameter per flag per environment, and both revisions of a blue/green deploy resolve the same one.
# During the bake — five minutes in production — the release before and the release after are both running,
# so a flip in that window reaches both. A key the older revision has never heard of is harmless, because
# nothing there reads it; a key whose *meaning* changed between the two revisions is not. That is the
# compatibility rule the migrations are held to, landing on flags instead of on schemas: a key is never
# repurposed, it is retired and another is introduced, exactly as a column is expanded before it is
# contracted.
#
# `ignore_changes = [value]` is what makes a flip stick. This stack seeds a new environment's parameter with
# the value declared in `flags.auto.tfvars` and never touches it again, so neither the next deploy — which
# applies the whole stack, unattended, on every merge — nor `make rollback` quietly puts a flag back the way
# the file says it started. The seed is therefore a one-time event: changing it in the file moves nothing in
# an environment that already exists, where the parameter is the truth and `make flags` prints it.

locals {
  # One entry per flag, keyed `<service>/<key>`, so a flag's name only has to be unique within the service
  # that reads it. `merge(...)` over a list of one-map-per-service flattens that into a single map for
  # `for_each`; the `...` is the argument expansion, not a range.
  flag_parameters = merge([
    for name, flags in var.flags : {
      for key, seed in flags : "${name}/${key}" => { service = name, key = key, seed = seed }
    }
  ]...)

  # `checkout-v2` becomes `FLAG_CHECKOUT_V2`: one spelling in `flags.auto.tfvars` and the environment
  # variable derived from it, so an operator flipping a flag and the code reading it cannot drift apart.
  # Only under `ssm`: `appconfig` puts nothing in the container's environment but the three keys in
  # `flag_environment`, and the values arrive over loopback instead.
  service_flags = {
    for name, service in var.services : name => local.use_ssm ? {
      for id, flag in local.flag_parameters :
      "FLAG_${upper(replace(flag.key, "-", "_"))}" => aws_ssm_parameter.flag[id].arn
      if flag.service == name
    } : {}
  }

  # Known from configuration alone at plan time, for the reason `has_secrets` is: the ARNs below are created
  # in this same apply, so on a fresh environment their values are unknown then, and `count` must not be.
  has_flags = length(local.flag_parameters) > 0

  # Which of the two shapes below this environment is running. Per environment and not per project: see
  # `variable "flag_transport"`.
  use_ssm       = var.flag_transport == "ssm"
  use_appconfig = var.flag_transport == "appconfig"

  # What a task is told about where its flags come from. `FLAG_TRANSPORT` is read by exactly one function in
  # the service — `defaultSource` in its own flag reader — so no slice, and no other file, branches on it.
  # Under `ssm` the variables themselves are the answer and nothing here is needed.
  flag_environment = local.use_appconfig && local.has_flags ? {
    FLAG_TRANSPORT        = "appconfig"
    APPCONFIG_APPLICATION = one(aws_appconfig_application.flags[*].name)
    APPCONFIG_ENVIRONMENT = one(aws_appconfig_environment.flags[*].name)
    APPCONFIG_PROFILE     = one(aws_appconfig_configuration_profile.flags[*].name)
  } : {}
}

resource "aws_ssm_parameter" "flag" {
  for_each = local.use_ssm ? local.flag_parameters : {}

  # A path rather than a flat name, so `aws ssm get-parameters-by-path` can read an environment's flags
  # without being told what they are called.
  name  = "/${var.project}/${var.environment}/${each.value.service}/flags/${each.value.key}"
  type  = "String"
  value = each.value.seed

  lifecycle {
    ignore_changes = [value]
  }
}

# The execution role reads the parameter when it starts a task — the same role, and the same moment, as the
# secrets policy beside this. The task role is untouched: the application never calls AWS for a flag.
data "aws_iam_policy_document" "execution_flags" {
  count = local.has_flags && local.use_ssm ? 1 : 0

  statement {
    actions   = ["ssm:GetParameters"]
    resources = [for parameter in aws_ssm_parameter.flag : parameter.arn]
  }
}

resource "aws_iam_role_policy" "execution_flags" {
  count = local.has_flags && local.use_ssm ? 1 : 0

  name   = "read-this-environment-s-flags"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_flags[0].json
}

# ── The AppConfig shape ────────────────────────────────────────────────────────────────────────────────
#
# What `flag_transport = "appconfig"` provisions, and what it deliberately does not.
#
# It owns the *containers* for a configuration and nothing about its content: the application, the
# environment, the profile and the strategy a deployment runs under. The document itself — which flags exist
# and what each is set to — is written by `scripts/deploy.py`, and that split is the whole design. AppConfig
# holds one document per profile rather than a parameter per flag, so a stack that owned the content would
# rewrite every flag on every apply, and this stack is applied unattended on every merge to `main`. There is
# no `ignore_changes` that helps: ignoring the content would mean a flag declared in `flags.auto.tfvars`
# could never reach an environment that already exists, which is the file's entire job.
#
# So a new environment starts with a profile and no version deployed, and the agent answers with nothing —
# every flag off, which is the safe direction and exactly what a new environment should do. `make deploy`
# reconciles the declared flags at their seeds, and `make flag` writes a version and starts a deployment.
#
# One deployment may be in flight per environment: a second is refused with a `ConflictException` rather than
# queued. With one document that is a feature — flips serialise and a collision is loud — and it is the
# reason this is one profile rather than one per flag, which would make two people flipping two unrelated
# flags collide.
resource "aws_appconfig_application" "flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  name        = local.prefix
  description = "Feature flags for ${var.project}, read by the agent beside each task."
}

resource "aws_appconfig_environment" "flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  name           = var.environment
  application_id = aws_appconfig_application.flags[0].id
}

# Freeform rather than `AWS.AppConfig.FeatureFlags`, on purpose. The typed shape wraps every flag in its own
# object with a schema of AppConfig's choosing; freeform lets the document be exactly the map the service's
# reader already returns from `snapshot()` — one key, one string, `on` or anything else. That is what keeps
# a slice's `flagEnabled('checkout-v2')` identical whichever transport an environment runs.
resource "aws_appconfig_configuration_profile" "flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  application_id = aws_appconfig_application.flags[0].id
  name           = "flags"
  location_uri   = "hosted"
}

# All at once, and no bake. A flag flip is already the reversible change — `make flag ... VALUE=off` puts it
# back in seconds — so a gradual rollout here would only make "is it on yet?" unanswerable while adding the
# window in which two revisions of the same environment disagree. A project that wants a percentage rollout
# wants it in the code the flag gates, where it can be reasoned about, not in the delivery of the value.
resource "aws_appconfig_deployment_strategy" "flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  name                           = "${local.prefix}-flags-immediate"
  deployment_duration_in_minutes = 0
  final_bake_time_in_minutes     = 0
  growth_factor                  = 100
  replicate_to                   = "NONE"
}

# The first thing this skeleton's application is allowed to call. Under `ssm` the *execution* role reads the
# parameters when it starts a task and the task role is untouched — the application never talks to AWS at
# all. The agent runs inside the task and uses the task role, so choosing `appconfig` is also choosing to
# give the application an AWS permission, which is worth knowing before taking it on.
data "aws_iam_policy_document" "task_flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  statement {
    actions   = ["appconfig:StartConfigurationSession"]
    resources = ["${aws_appconfig_configuration_profile.flags[0].arn}/*"]
  }

  # Takes the session token the call above returned rather than naming a resource, so there is nothing
  # narrower to scope it to.
  statement {
    actions   = ["appconfig:GetLatestConfiguration"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "task_flags" {
  count = local.has_flags && local.use_appconfig ? 1 : 0

  name   = "read-this-environment-s-flags"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_flags[0].json
}

output "flags" {
  description = "What `make flag` and `make flags` need: the transport, the cluster, each service, and where the values live."
  value = {
    transport  = var.flag_transport
    cluster    = aws_ecs_cluster.main.name
    services   = { for name, service in aws_ecs_service.service : name => service.name }
    parameters = { for id, parameter in aws_ssm_parameter.flag : id => parameter.name }
    declared   = { for id, flag in local.flag_parameters : id => flag.seed }
    appconfig = local.use_appconfig && local.has_flags ? {
      application = one(aws_appconfig_application.flags[*].id)
      environment = one(aws_appconfig_environment.flags[*].environment_id)
      profile     = one(aws_appconfig_configuration_profile.flags[*].configuration_profile_id)
      strategy    = one(aws_appconfig_deployment_strategy.flags[*].id)
    } : null
  }
}
