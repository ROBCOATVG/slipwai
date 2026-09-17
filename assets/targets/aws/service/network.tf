# The account's default VPC, deliberately. A VPC of this product's own — private subnets, NAT gateways, a
# bastion — costs from the first day and buys nothing until there is traffic to isolate; the default VPC has
# a public subnet in every zone, which is what the load balancers and the Fargate tasks need. Moving to
# a dedicated VPC is a change to these two data sources and the subnet group in rds.tf.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# The tasks' own security group, rather than the VPC's default one: it is what the database admits, so it
# has to be a group this stack names. Ingress is each service's port from anywhere inside the VPC, which is
# where the load balancers are; a task has a public address only so it can reach out (network_configuration
# in main.tf), and nothing outside the VPC is admitted to it.
resource "aws_security_group" "tasks" {
  name        = "${local.prefix}-tasks"
  description = "The ECS tasks: reachable on their ports from inside the VPC, free to reach out"
  vpc_id      = data.aws_vpc.default.id

  dynamic "ingress" {
    for_each = toset([for service in var.services : service.port])

    content {
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = [data.aws_vpc.default.cidr_block]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
