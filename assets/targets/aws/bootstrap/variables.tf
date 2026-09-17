variable "project" {
  description = "The project's name; prefixes every resource this stack and the service stack create."
  type        = string
}

variable "repository" {
  description = "The repository whose main branch may deploy, as `owner/name`; what the OIDC trust names. Read from the remote by `make bootstrap`."
  type        = string
}

variable "oidc_subject_prefix" {
  description = "The prefix GitHub actually puts in the token's `sub` claim for this repository, as its OIDC customization API reports it — `repo:owner/name`, or `repo:owner@<owner id>/name@<repo id>` where the organisation has enabled the immutable, rename-proof form. Read from the forge by `make bootstrap`; empty falls back to `repo:<repository>`."
  type        = string
  default     = ""
}

variable "deploy_with" {
  description = "How the pipeline becomes the deploy role: `oidc` (GitHub, no stored credential) or `access-key` (a forge without OIDC federation, such as Gitea). Decided by `make bootstrap` from the remote."
  type        = string
  default     = "oidc"

  validation {
    condition     = contains(["oidc", "access-key"], var.deploy_with)
    error_message = "deploy_with is oidc or access-key."
  }
}

variable "state_passphrase" {
  description = "Encrypts this stack's committed state. Keep it in a password manager; without it the state file is unreadable."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "OpenTofu's pbkdf2 key provider needs at least 16 characters."
  }
}

# Written by the factory into project.auto.tfvars.json from project.json's `deployables`, and rewritten by
# `add-service`; the same file the service stack reads. Only `migrate_image` matters here — it is what asks
# for a second repository.
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

variable "web" {
  description = "The browser app, when the project has one; unused here, declared so one tfvars file serves both stacks."
  type = object({
    path = string
    api  = string
  })
  default = null
}
