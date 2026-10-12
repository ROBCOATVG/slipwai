# backing-service:postgres:begin
# Private to Lightsail resources in this Region. Never expose RDS to the internet to make compute fit.
locals {
  database_wanted = anytrue([for service in var.services : service.store == "rds"])
  database_url = local.database_wanted ? format(
    "postgres://app:%s@%s:%d/app", random_password.database[0].result,
    aws_lightsail_database.database[0].master_endpoint_address,
    aws_lightsail_database.database[0].master_endpoint_port,
  ) : null
}
variable "postgres_blueprint" {
  description = "Lightsail PostgreSQL blueprint; list available choices with aws lightsail get-relational-database-blueprints."
  type        = string
  default     = "postgres_16"
}
resource "random_password" "database" {
  count   = local.database_wanted ? 1 : 0
  length  = 32
  special = false
}
resource "aws_lightsail_database" "database" {
  count                    = local.database_wanted ? 1 : 0
  relational_database_name = "${local.prefix}-database"
  master_database_name     = "app"
  master_username          = "app"
  master_password          = random_password.database[0].result
  blueprint_id             = var.postgres_blueprint
  bundle_id                = "micro_1_0"
  publicly_accessible      = false
  backup_retention_enabled = true
  skip_final_snapshot      = false
  final_snapshot_name      = "${local.prefix}-database-final"
  lifecycle {
    prevent_destroy = true
  }
}
# backing-service:postgres:end

# backing-service:postgres:begin
output "database_url" {
  value     = local.database_url
  sensitive = true
}
# backing-service:postgres:end
