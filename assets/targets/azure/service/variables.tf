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

variable "location" {
  description = "The Azure region this environment lives in; the bootstrap stack's, written to the forge as AZURE_LOCATION."
  type        = string
}

# The registry the bootstrap stack created, as two facts rather than one: the resource id is what an
# `AcrPull` assignment is scoped to, and the login server is what a container app is told to pull from.
# Both come from the repository's variables, so neither is guessed from the other.
variable "registry_id" {
  description = "The container registry's resource id, from the bootstrap stack's outputs."
  type        = string
}

variable "registry_server" {
  description = "The container registry's login server, `<registry>.azurecr.io` — IMAGE_REGISTRY without its trailing slash."
  type        = string
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
# the terms this target provisions them: `store = "flexible-server"` for the Postgres event store,
# `auth = "entra"` for the staff identity, `users = "entra-external"` for the product's users; how its
# migrations run once it is an image; and the environment its backend needs in production over and above
# the port.
# The two probes answer two different questions. `health_path` is readiness — "send me traffic" — which
# asks the service's driven ports whether it can serve, and it is what gates the revision's traffic switch.
# `liveness_path` is "is this process up", and a revision that fails it is restarted: pointing that one at
# readiness would restart a replica whose only problem is a database somewhere else.
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

# Replica size and scaling. The Consumption profile takes a fixed set of vCPU/memory pairs, and this is the
# smallest of them — the same shape as the smallest Fargate task the AWS target runs, so the two are
# comparable. Raise these in the environment's tfvars, not here.
variable "cpu" {
  description = "vCPU per replica. Consumption takes 0.25, 0.5, 0.75, 1.0 and up, each with its own memory."
  type        = number
  default     = 0.25
}

variable "memory" {
  description = "Memory per replica, as Container Apps spells it: 0.5Gi goes with 0.25 vCPU."
  type        = string
  default     = "0.5Gi"
}

variable "min_replicas" {
  description = "Replicas kept running per service. Two in production is what makes a deploy and a lost zone invisible; zero lets an environment sleep, at the price of a cold start on the first request."
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Replicas the service may scale out to."
  type        = number
  default     = 2
}

# What Container Apps keeps of the release before this one, and the Azure shape of AWS's bake window.
#
# On ECS both revisions run for `bake_minutes` and then the old one goes, so a rollback inside the window
# is instant and the environment briefly costs double. Here a revision that has stopped taking traffic goes
# on running until the platform deactivates it, so the choice is the other way round: keeping one costs an
# extra replica for as long as it is kept, and keeping none means a rollback starts the previous image
# again — a cold start of seconds rather than a weight change of milliseconds.
#
# Zero in staging, where the deploy itself is what is being proved. One in production, which is the same
# trade `min_replicas = 2` makes there and roughly the same money.
variable "kept_revisions" {
  description = "Revisions kept running after they stop taking traffic: 1 makes a rollback a traffic weight, 0 makes it a restart."
  type        = number
  default     = 0
}

# Where a running replica reads its feature flags from, and the one decision that is per environment rather
# than per project. Deliberately not a generation-time answer: "Key Vault in staging, App Configuration in
# production" is a reasonable thing to want — you take the SDK on where a flip genuinely has to beat a
# restart, and not before — and a question answered once when the repository was made could not express it.
#
#   keyvault   one Key Vault secret per flag, resolved into the replica's environment by Container Apps
#              exactly as a secret is. No SDK in any image, in any of the languages this factory
#              generates, and a flip costs a rolling restart.
#   appconfig  Azure App Configuration, read by the application under its own managed identity. A flip
#              takes effect without a restart, at the price of an SDK in the image — Container Apps has no
#              agent sidecar to read one over loopback, which is the one place this target is weaker than
#              the AWS one. See `flags.tf`.
#
# The application does not branch on this: the stack tells the reader which source to use through
# `FLAG_TRANSPORT`, and `defaultSource` in the service's own flag reader is the only place that reads it.
variable "flag_transport" {
  description = "How a replica reads its feature flags: `keyvault` (a restart per flip) or `appconfig` (no restart)."
  type        = string
  default     = "keyvault"

  # Written by the factory from the backends this project actually has. `appconfig` is offered only where
  # every service's flag reader can read App Configuration; a backend whose reader has not been given one
  # yet would otherwise apply cleanly and then read every flag as off, which is the silent failure this
  # whole file is arranged to avoid. Widening it is a reader and this list, together.
  validation {
    condition     = contains(__FLAG_TRANSPORTS__, var.flag_transport)
    error_message = "flag_transport must be one of the values the condition above lists: this project's backends can read those and no others."
  }
}
