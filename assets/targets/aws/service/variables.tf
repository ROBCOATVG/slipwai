variable "project" {
  description = "The project's name; every resource here is prefixed `<project>-<environment>`."
  type        = string
}

variable "environment" {
  description = "Which environment this workspace is: `staging` or `production`."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Two long-lived environments, staging and production; ephemeral ones are a separate design."
  }
}

# The image each service runs, by digest — `<registry>/<project>-<service>@sha256:…` — written by
# `make push` into .build/images.json and passed by scripts/deploy.py. By digest rather than tag so that
# what staging proved is byte for byte what production gets.
variable "images" {
  description = "Service name to the image reference it runs, by digest."
  type        = map(string)
}

# The project's services, written by the factory into project.auto.tfvars.json from project.json's
# `deployables` and rewritten by `add-service`. Each entry says what the service answered its axes with in
# the terms this target provisions them: `store = "rds"` for the Postgres event store, `auth = "cognito"`
# for the staff identity, `users = "cognito"` for the product's users; how its migrations run once it is an
# image; and the environment its backend needs in production over and above the port.
# `health_path` is *readiness* — "send me traffic" — which asks the service's driven ports whether it can
# serve, and it is what the target group's health check gates on, so a task whose event store is
# unreachable never takes traffic. `liveness_path` is the other question, "is this process up", which
# nothing on this target asks: an ALB has one health check, and readiness is the one it should be.
variable "services" {
  description = "The project's services, from project.json."
  type = map(object({
    port            = number
    health_path     = string
    liveness_path   = string
    store           = optional(string)
    auth            = optional(string)
    users           = optional(string)
    migrate_command = optional(list(string))
    migrate_image   = optional(string)
    environment     = optional(map(string), {})
  }))
}

# The feature flags each service reads, from `flags.auto.tfvars`, and the value a new environment seeds them
# with. Not in `project.auto.tfvars.json` with the services: that file is generated from `project.json` and
# rewritten by `add-service`, while a flag is added by whoever writes the code that reads it. `flags.tf` is
# where the shape is explained.
variable "flags" {
  description = "Feature flags per service: the flag's key, and the value a new environment is seeded with."
  type        = map(map(string))
  default     = {}
}

variable "web" {
  description = "The browser app, when the project has one: where it lives and which service its /api goes to."
  type = object({
    path = string
    api  = string
  })
  default = null
}

# Task size and scaling. The smallest Fargate task is enough for a walking skeleton; raise these in the
# environment's tfvars, not here.
variable "cpu" {
  description = "CPU units per task: a power of two between 256 and 4096."
  type        = string
  default     = "256"
}

variable "memory" {
  description = "Memory per task in MiB, 512 to 8192."
  type        = string
  default     = "512"
}

variable "min_tasks" {
  description = "Tasks kept running per service. Two in production is what makes a deploy and a lost zone invisible."
  type        = number
  default     = 1
}

variable "max_tasks" {
  description = "Tasks the service may scale out to."
  type        = number
  default     = 2
}

# How long the old revision's tasks stay up, drained, after the new one has taken the traffic. In that window
# a rollback is the listener rule pointing back — seconds — and a revision that starts failing under real
# traffic is rolled back by ECS itself. Both revisions run for the whole of it, so the deploy job waits and
# the environment briefly costs double; zero tears the old revision down as soon as the traffic has moved.
variable "bake_minutes" {
  description = "Minutes the previous revision is kept running after a blue/green deploy has shifted traffic."
  type        = number
  default     = 0
}

# Where a running task reads its feature flags from, and the one decision that is per environment rather
# than per project. Deliberately not a generation-time answer: "SSM in staging, AppConfig in production" is
# a reasonable thing to want — you take the sidecar on where a flip genuinely has to beat a restart, and not
# before — and a question answered once when the repository was made could not express it.
#
#   ssm        one SSM parameter per flag, resolved into the container's environment by ECS exactly as a
#              secret is. No sidecar, no AWS call from the application, and a flip costs a rolling restart.
#   appconfig  an AWS AppConfig agent beside the container, read over loopback. A flip takes effect without
#              a restart, at the price of a second container in every task and an application that now
#              calls AWS — see `flags.tf` for what that changes about the task role.
#
# The application does not branch on this: the stack tells the reader which source to use through
# `FLAG_TRANSPORT`, and `defaultSource` in the service's own flag reader is the only place that reads it.
variable "flag_transport" {
  description = "How a task reads its feature flags: `ssm` (a restart per flip) or `appconfig` (no restart)."
  type        = string
  default     = "ssm"

  # Written by the factory from the backends this project actually has. `appconfig` is offered only where
  # every service's flag reader can read an agent; a backend whose reader has not been given one yet would
  # otherwise apply cleanly and then read every flag as off, which is the silent failure this whole file is
  # arranged to avoid. Widening it is a reader and this list, together.
  validation {
    condition     = contains(__FLAG_TRANSPORTS__, var.flag_transport)
    error_message = "flag_transport must be one of the values the condition above lists: this project's backends can read those and no others."
  }
}

# The published AppConfig agent, pinned by the project rather than floating. Only pulled under
# `flag_transport = "appconfig"`; it is the one image in a generated project that this repository does not
# build, so it is named here where a project can move it rather than buried in a task definition.
variable "appconfig_agent_image" {
  description = "The AWS AppConfig agent image the sidecar runs, used only under `flag_transport = appconfig`."
  type        = string
  default     = "public.ecr.aws/aws-appconfig/aws-appconfig-agent:2.x"
}
