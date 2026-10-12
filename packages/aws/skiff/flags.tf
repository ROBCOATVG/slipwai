# Parameter values belong to the operator after their first seed. Every deploy resolves the live value;
# neither rollback nor a source change resets it. The application still reads FLAG_<KEY> from its environment.
locals {
  flag_parameters = merge([
    for name, flags in var.flags : {
      for key, seed in flags : "${name}/${key}" => { service = name, key = key, seed = seed }
    }
  ]...)
}
resource "aws_ssm_parameter" "flag" {
  for_each = local.flag_parameters
  name     = "/${var.project}/${var.environment}/${each.value.service}/flags/${each.value.key}"
  type     = "String"
  value    = each.value.seed
  lifecycle {
    ignore_changes = [value]
  }
}
output "flags" {
  value = {
    transport  = "ssm"
    parameters = { for id, parameter in aws_ssm_parameter.flag : id => parameter.name }
  }
}
