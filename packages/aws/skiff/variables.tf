variable "project" {
  type = string
}
variable "environment" {
  type = string
  validation {
    condition     = var.environment == "production"
    error_message = "The skiff has one environment: use make deploy ENV=production, or converge --shape liner."
  }
}
variable "images" {
  description = "Service image references by immutable digest."
  type        = map(string)
}
variable "services" {
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
variable "flags" {
  type    = map(map(string))
  default = {}
}
variable "flag_transport" {
  type    = string
  default = "ssm"
  validation {
    condition     = var.flag_transport == "ssm"
    error_message = "Skiff flags use SSM resolved into environment values; use ssm, or converge --shape liner for a live sidecar."
  }
}
variable "web" {
  type = object({
    path = string
    api  = string
  })
  default = null
}
