# One ECS service per application, on Fargate, deployed blue/green. This file is the service itself: the
# roles it runs under, its task definition — which image, which port, what it is told about the
# infrastructure the other files provision for it — the service that keeps it running, and how it scales.
# How traffic reaches it, and the two target groups a blue/green deploy swaps between, are in ingress.tf.
#
# Blue/green rather than rolling because of what a deploy can then do: the new revision's tasks start beside
# the old, pass their health checks on a target group with no traffic, take all of it at once when they do,
# and the old tasks stay up, drained, for `bake_minutes` — so in that window a rollback is the listener rule
# pointing back at them, seconds, and a revision that fails its health checks is never routed to at all.
# Native to ECS, so `tofu apply` still describes what is running and `make rollback` — re-apply the previous
# digests — is itself a blue/green deploy.
#
# The regions between `backing-service:<feature>:begin` and `:end` belong to one answer to one axis, exactly
# as they do in docker-compose.yml: `scripts/backing-services.py` removes a region with the answer that owns
# it, so `./init --event-store memory` takes the database's wiring out of here as well as the database out
# of rds.tf.

locals {
  # What every service is told, then what its own backend needs in production (from
  # project.auto.tfvars.json), then what the target provisions for the answers it gave. The trailing `{}`
  # lets every region above it end with a comma and be removed whole.
  #
  # `service.environment` is the per-backend middle layer, and it is not only the framework switches it
  # started as: for a service whose store is RDS it also carries `PGSSLMODE`, because that server refuses an
  # unencrypted connection and each driver spells "encrypt, do not verify" differently — `no-verify` for
  # node-postgres, `require` for psycopg and pgx, and nothing for the Java backends, whose pgjdbc ignores
  # the variable and already prefers TLS on its own. The factory's `src/slipwai/images.py`
  # (`POSTGRES_SSLMODE`) has the whole argument and the measurements behind it. Read by both task
  # definitions — the service below, and the migrate task in rds.tf — so the two cannot disagree about how
  # they reach the same database.
  service_environment = {
    for name, service in var.services : name => merge(
      {
        HOST      = "0.0.0.0"
        PORT      = tostring(service.port)
        LOG_LEVEL = "info"
      },
      service.environment,
      # backing-service:keycloak:begin
      service.auth == "cognito" ? local.staff_environment : {},
      service.auth == "auth0" ? local.auth0_staff_environment : {},
      # backing-service:keycloak:end
      # backing-service:users-keycloak:begin
      service.users == "cognito" ? local.customers_environment : {},
      service.users == "auth0" ? local.auth0_customers_environment : {},
      # backing-service:users-keycloak:end
      {},
    )
  }

  # Secrets Manager ARNs, injected by ECS as environment variables the container reads like any other; the
  # values never appear in a task definition or in this state.
  service_secrets = {
    for name, service in var.services : name => merge(
      # backing-service:postgres:begin
      service.store == "rds" ? { DATABASE_URL = one(aws_secretsmanager_secret.database[*].arn) } : {},
      # backing-service:postgres:end
      # backing-service:keycloak:begin
      service.auth == "cognito" ? { OIDC_CLIENT_SECRET = one(aws_secretsmanager_secret.staff_client[*].arn) } : {},
      service.auth == "auth0" ? local.auth0_staff_secrets : {},
      # backing-service:keycloak:end
      {},
    )
  }

  secret_arns = distinct(flatten([for secrets in values(local.service_secrets) : values(secrets)]))

  # Whether IAM needs a secrets policy at all, decided from the same per-service answers that build
  # `service_secrets` — but from configuration alone. The ARNs in `secret_arns` are created in this same
  # apply, so on a fresh environment their values are unknown at plan time, and `count` must be known then;
  # asking `length(secret_arns) > 0` fails every first apply. The trailing `false` lets every region above
  # it end with a comma and be removed whole.
  has_secrets = anytrue([
    for service in var.services : anytrue([
      # backing-service:postgres:begin
      service.store == "rds",
      # backing-service:postgres:end
      # backing-service:keycloak:begin
      service.auth == "cognito",
      service.auth == "auth0",
      # backing-service:keycloak:end
      false,
    ])
  ])
}

# ── The three roles ECS runs a service under ──────────────────────────────────────────────────────────

data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs.amazonaws.com"]
    }
  }
}

# Pulls the image, writes the logs, reads the secrets: what ECS itself does to start a task.
resource "aws_iam_role" "execution" {
  name               = "${local.prefix}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "execution_secrets" {
  count = local.has_secrets ? 1 : 0

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = local.secret_arns
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  count = local.has_secrets ? 1 : 0

  name   = "read-this-environment-s-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets[0].json
}

# What ECS itself does to a deploy's traffic: register tasks with the two target groups and repoint the
# listener rule between them. The managed policy is exactly that.
resource "aws_iam_role" "infrastructure" {
  name               = "${local.prefix}-infrastructure"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "infrastructure" {
  role       = aws_iam_role.infrastructure.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonECSInfrastructureRolePolicyForLoadBalancers"
}

# What the application itself may call. Nothing yet: a walking skeleton talks to its database through a
# connection string and to nothing else. Grant here, per service, when a slice needs an AWS API.
resource "aws_iam_role" "task" {
  name               = "${local.prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

# ── The services ───────────────────────────────────────────────────────────────────────────────────────

# One cluster per environment, so staging and production have a load balancer each rather than sharing the
# account's `default` cluster and its one.
resource "aws_ecs_cluster" "main" {
  name = local.prefix
}

resource "aws_cloudwatch_log_group" "service" {
  for_each = var.services

  name              = "/${local.prefix}/${each.key}"
  retention_in_days = var.environment == "production" ? 90 : 14
}

# The task definition is the image and everything it is started with. `X86_64` because that is what
# `make build` targets (`PLATFORM=linux/amd64`); a change of platform is a change in both places.
resource "aws_ecs_task_definition" "service" {
  for_each = var.services

  family                   = "${local.prefix}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode(concat([
    {
      name      = each.key
      image     = var.images[each.key]
      essential = true
      portMappings = [
        { containerPort = each.value.port, protocol = "tcp" }
      ]
      # `flag_environment` is empty unless this environment reads its flags from AppConfig, in which case it
      # is the three keys naming the configuration — read by `defaultSource` in the service's flag reader
      # and nowhere else. See `flags.tf`.
      environment = [
        for name, value in merge(local.service_environment[each.key], local.flag_environment) :
        { name = name, value = value }
      ]
      # Secrets and flags reach the container the same way — an ARN ECS resolves at task start — and differ
      # only in what they are for and where they are declared. `flags.tf` has the argument.
      secrets = [
        for name, arn in merge(local.service_secrets[each.key], local.service_flags[each.key]) :
        { name = name, valueFrom = arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.service[each.key].name
          "awslogs-region"        = data.aws_region.current.region
          "awslogs-stream-prefix" = each.key
        }
      }
    }
    ],
    # The AppConfig agent, only where this environment reads its flags from it. It polls AppConfig with the
    # task role's permissions and answers the application over loopback, which is what keeps the AWS SDK out
    # of every image this factory builds — the sidecar holds it and the service makes a plain HTTP call.
    #
    # `essential = false` deliberately: if the agent stops, the task keeps serving and every flag reads as
    # absent, which is off. The alternative — taking the task down because a *flag* source is unreachable —
    # turns a degraded flag lookup into an outage, and off is already the safe answer this whole mechanism
    # is built around.
    local.use_appconfig && local.has_flags ? [
      {
        name      = "aws-appconfig-agent"
        image     = var.appconfig_agent_image
        essential = false
        portMappings = [
          { containerPort = 2772, protocol = "tcp" }
        ]
        environment = [
          { name = "SERVICE_REGION", value = data.aws_region.current.region }
        ]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = aws_cloudwatch_log_group.service[each.key].name
            "awslogs-region"        = data.aws_region.current.region
            "awslogs-stream-prefix" = "appconfig-agent"
          }
        }
      }
  ] : []))

  lifecycle {
    precondition {
      condition     = contains(keys(var.images), each.key)
      error_message = "No image for ${each.key} in `images`: run `make push` and pass .build/images.json."
    }
  }
}

resource "aws_ecs_service" "service" {
  for_each = var.services

  name            = "${local.prefix}-${each.key}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.service[each.key].arn
  desired_count   = var.min_tasks
  launch_type     = "FARGATE"
  # The target group has to see a task answer its probe before the listener rule is moved to it; the grace
  # period is how long a task has to come up before a failed probe counts.
  health_check_grace_period_seconds = 60

  network_configuration {
    subnets         = data.aws_subnets.default.ids
    security_groups = [aws_security_group.tasks.id]
    # The default VPC has no NAT gateway, so a task needs an address of its own to pull its image and read
    # its secrets. The security group is what keeps that address from being an entrance.
    assign_public_ip = true
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_configuration {
    strategy             = "BLUE_GREEN"
    bake_time_in_minutes = var.bake_minutes
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue[each.key].arn
    container_name   = each.key
    container_port   = each.value.port

    advanced_configuration {
      alternate_target_group_arn = aws_lb_target_group.green[each.key].arn
      production_listener_rule   = aws_lb_listener_rule.production[each.key].arn
      role_arn                   = aws_iam_role.infrastructure.arn
    }
  }

  # So an apply returns when the new revision has taken the traffic and baked, rather than when it was
  # accepted: what `make smoke` runs against afterwards is the revision that was just deployed. And so that
  # interrupting an apply rolls the deploy back rather than leaving it half made.
  wait_for_steady_state = true
  sigint_rollback       = true

  lifecycle {
    ignore_changes = [
      # Autoscaling owns the count once the service exists.
      desired_count,
      # ECS swaps the two target groups at every deploy, and the provider (hashicorp/terraform-provider-aws
      # #45678) would otherwise send the original pair back with every update, so that every deploy lands
      # on the same group and the rule is never repointed. Nothing in this block changes after creation.
      load_balancer,
    ]
  }

  # The resource's own documentation asks for this: without it the policies can be destroyed before the
  # service has finished draining, and the service is then stuck.
  depends_on = [
    aws_iam_role_policy_attachment.execution,
    aws_iam_role_policy_attachment.infrastructure,
    aws_iam_role_policy.execution_secrets,
    aws_iam_role_policy.execution_flags,
    aws_lb_listener_rule.production,
  ]
}

# Between `min_tasks` and `max_tasks` on average CPU: the same floor and ceiling the environment's tfvars
# set, and the one policy a walking skeleton needs until its traffic says otherwise.
resource "aws_appautoscaling_target" "service" {
  for_each = var.services

  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.service[each.key].name}"
  min_capacity       = var.min_tasks
  max_capacity       = var.max_tasks
}

resource "aws_appautoscaling_policy" "cpu" {
  for_each = var.services

  name               = "${local.prefix}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.service[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.service[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.service[each.key].resource_id

  target_tracking_scaling_policy_configuration {
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
