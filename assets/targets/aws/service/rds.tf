# backing-service:postgres:begin
# The Postgres event store, provisioned as RDS: one instance per environment, shared by every service whose
# store is Postgres — the same shape Compose gives them locally, and the right one until a service owns data
# of its own (docs/services.md, "Three limits worth knowing"). `db.t4g.micro`, single-AZ, on purpose: the
# smallest instance that is a real always-on Postgres. Aurora Serverless v2 is the documented swap, not the
# default — its resume from zero takes 15 to 30 seconds, which is the wrong trade for production.
locals {
  rds_wanted = anytrue([for service in var.services : service.store == "rds"])
  # The services whose migrations run as a one-off task against this database, with the service's own
  # image or the migrate image built beside it. A backend whose framework migrates as the service starts
  # (both Java backends, switched on through its `environment`) has neither and is not here.
  migrating = {
    for name, service in var.services : name => service
    if service.store == "rds" && (service.migrate_command != null || service.migrate_image != null)
  }
}

variable "postgres_version" {
  description = "The Postgres major version; minor upgrades apply automatically."
  type        = string
  default     = "17"
}

variable "database_instance_class" {
  description = "The RDS instance class; the smallest Graviton class is a real database for about $12 a month."
  type        = string
  default     = "db.t4g.micro"
}

resource "random_password" "database" {
  count = local.rds_wanted ? 1 : 0

  length  = 32
  special = false
}

resource "aws_db_subnet_group" "database" {
  count = local.rds_wanted ? 1 : 0

  name       = "${local.prefix}-database"
  subnet_ids = data.aws_subnets.default.ids
}

# Reachable from the tasks' security group and from nothing else: not from the internet, and not from a
# laptop. Migrations run inside the VPC as a one-off task for that reason (`make migrate-remote`).
resource "aws_security_group" "database" {
  count = local.rds_wanted ? 1 : 0

  name        = "${local.prefix}-database"
  description = "Postgres, admitted from the ECS tasks only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.tasks.id]
  }
}

# The server half of one decision, whose client half is `PGSSLMODE` in the task environment (see the migrate
# container below, and `local.service_environment` in main.tf). `rds.force_ssl = 1` refuses any unencrypted
# connection: the server answers SQLSTATE `28000`, `no pg_hba.conf entry for host "…", no encryption`,
# before authentication.
#
# It is also the half that carries the guarantee. Three of the five backends ask for encryption explicitly;
# the two Java ones cannot be told through the environment at all — pgjdbc does not read `PGSSLMODE` — and
# rely on their driver's own default, `prefer`, which negotiates TLS but would fall back to plaintext
# against a server that allowed it. This resource is what makes sure none ever does.
#
# Stated here rather than inherited, even though `default.postgres17` has carried this exact value since
# Postgres 15 and so it is already true. Two reasons. It puts the policy and the setting that satisfies it
# in one repository, where a reader who hits `28000` can see both halves at once instead of learning that a
# default group they never chose has an opinion. And it stops a future engine default from moving the
# ground silently — either way round: a default that dropped `force_ssl` would quietly start accepting
# plaintext, and one that added a *stricter* setting would break a deploy with nothing in the diff.
#
# `family` is derived from `postgres_version`, so raising that variable brings the group with it — and that
# is why this is the one resource here named by prefix rather than outright. `family` cannot be changed in
# place, so a major version upgrade replaces the group, and AWS refuses to delete a parameter group an
# instance still references: destroy-then-create deadlocks, and create-then-destroy needs the new group to
# have a name the old one is not already using. `name_prefix` with `create_before_destroy` is that pair —
# the new group is created under a generated name, the instance is updated to point at it, then the old one
# goes. The cost is a name with a suffix in the console, which is the cheaper side of the trade.
resource "aws_db_parameter_group" "database" {
  count = local.rds_wanted ? 1 : 0

  name_prefix = "${local.prefix}-database-"
  family      = "postgres${var.postgres_version}"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_instance" "database" {
  count = local.rds_wanted ? 1 : 0

  identifier                 = "${local.prefix}-database"
  engine                     = "postgres"
  engine_version             = var.postgres_version
  auto_minor_version_upgrade = true
  instance_class             = var.database_instance_class
  allocated_storage          = 20
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = "app"
  username                   = "app"
  password                   = random_password.database[0].result
  db_subnet_group_name       = aws_db_subnet_group.database[0].name
  parameter_group_name       = aws_db_parameter_group.database[0].name
  vpc_security_group_ids     = [aws_security_group.database[0].id]
  publicly_accessible        = false
  multi_az                   = false
  apply_immediately          = true
  # Production keeps a week of backups and refuses to be deleted; staging keeps a day and can be torn down.
  backup_retention_period   = var.environment == "production" ? 7 : 1
  deletion_protection       = var.environment == "production"
  skip_final_snapshot       = var.environment != "production"
  final_snapshot_identifier = "${local.prefix}-database-final"
}

# The whole connection string, in the one shape every backend here reads — `DATABASE_URL`, libpq style —
# rather than RDS's own managed secret, whose JSON the application would have to assemble a URL from.
#
# The address and the credentials, and nothing about TLS. No `?sslmode=…` here on purpose: one string is
# shared by five backends with three different driver semantics, and `sslmode` inside it means something
# different to each — for node-postgres it means *verify* against a CA store RDS's certificate is not in,
# and what it parses from the string also overrides `PGSSLMODE`, closing off the route that does work. So
# encryption is asked for per backend in the task environment instead; `src/slipwai/images.py`
# (`POSTGRES_SSLMODE`) in the factory carries the full reasoning with the package lines that prove it.
resource "aws_secretsmanager_secret" "database" {
  count = local.rds_wanted ? 1 : 0

  name                    = "${local.prefix}/DATABASE_URL"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database" {
  count = local.rds_wanted ? 1 : 0

  secret_id = aws_secretsmanager_secret.database[0].id
  secret_string = format(
    "postgres://%s:%s@%s:%d/%s",
    aws_db_instance.database[0].username,
    random_password.database[0].result,
    aws_db_instance.database[0].address,
    aws_db_instance.database[0].port,
    aws_db_instance.database[0].db_name,
  )
}

# The migration runner: the service's own image (or the migrate image built beside it) run once as a task
# inside the VPC, by `scripts/deploy.py` — which `make deploy` does *before* the service revision rolls, by
# applying this resource alone first, so an expand migration is in place when the new release arrives and
# the old one is still serving; `make migrate-remote ENV=…` does it on its own. Writing to a database stays
# an explicit act, exactly as it is locally; what changes in production is only where the command runs.
resource "aws_ecs_task_definition" "migrate" {
  for_each = local.migrating

  family                   = "${local.prefix}-${each.key}-migrate"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  # No flag transport and no AppConfig agent here, deliberately. A migration is a schema change and the one
  # thing it must not do is behave differently depending on a flag: the expand-then-contract rule that
  # `make check-migrations` enforces is what makes a rollback safe, and a flag-gated migration would make
  # "which shape is this database in" depend on something flippable. So a migrate task reads the plain
  # environment, and a flag read inside one would answer off — which is the safe direction, and the reason
  # this is stated rather than left to be discovered.

  container_definitions = jsonencode([
    merge(
      {
        name      = "migrate"
        image     = each.value.migrate_image != null ? var.images[each.value.migrate_image] : var.images[each.key]
        essential = true
        secrets   = [{ name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database[0].arn }]
        # The same environment the long-running service gets (main.tf), not a subset of it, and that is the
        # point: a migration and the service it migrates for connect to the same database, so anything that
        # decides *how* they connect has to reach both. `PGSSLMODE` is the case that proves it — this
        # container had `secrets` and no `environment` at all, so the client half of the TLS policy could
        # not reach the one task that runs first, and every first deploy failed here with `28000` while the
        # service that would have failed the same way had not started yet. Sharing the map means the two can
        # never disagree again, rather than the next such setting having to be added in two places.
        #
        # `HOST`, `PORT` and `LOG_LEVEL` ride along and are inert: nothing in a migration binds a socket.
        # `QUARKUS_FLYWAY_MIGRATE_AT_START` / `SPRING_FLYWAY_ENABLED` never appear here either way — a
        # backend whose framework migrates as it starts has no migrate task, so it is not in
        # `local.migrating`, which is also why every task reached by this map has a `PGSSLMODE` to read.
        environment = [for name, value in local.service_environment[each.key] : { name = name, value = value }]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = aws_cloudwatch_log_group.service[each.key].name
            "awslogs-region"        = data.aws_region.current.region
            "awslogs-stream-prefix" = "migrate"
          }
        }
      },
      # `command` on its own is ignored. The image a buildpack builds — pack's, for both backends that migrate
      # this way — has a fixed entrypoint, `/cnb/process/web`, which starts the web process whatever command
      # it is handed: the task would serve instead of migrating, never exit, and `scripts/deploy.py` would
      # wait on it until the waiter gave up, with nothing in the log but a normal start. The buildpack's
      # launcher runs any command with the image's PATH and environment in place, so the entrypoint is
      # pointed at it wherever a command is given (`tests/test_images.py` proves both halves). A migrate
      # image — Go's `cmd/migrate`, built by ko — is run as built, with the entrypoint it was given.
      each.value.migrate_command != null ? {
        entryPoint = ["/cnb/lifecycle/launcher"]
        command    = each.value.migrate_command
      } : {},
    )
  ])
}

output "migrate_tasks" {
  description = "What scripts/deploy.py runs to apply each service's migrations inside the VPC."
  value = {
    for name, task in aws_ecs_task_definition.migrate : name => {
      cluster         = aws_ecs_cluster.main.name
      family          = task.family
      subnets         = data.aws_subnets.default.ids
      security_groups = [aws_security_group.tasks.id]
      # So a failed migration can print its own log instead of telling the reader where to go looking. The
      # stream is `<prefix>/<container>/<task id>` — both halves are the `awslogs` configuration above, and
      # the deploy script has the task id from the ARN it started.
      log_group  = aws_cloudwatch_log_group.service[name].name
      log_stream = "migrate/migrate"
    }
  }
}
# backing-service:postgres:end
