"""AWS as a slipwai target: every answer the keel asks a place a project is deployed to.

Amazon Web Services: one ECS service per application on Fargate, RDS Postgres, Cognito, and a
site in S3 behind CloudFront.

This module is the executable half of the package. `target.json` beside it is the declaration half — the
row the prompt shows, the axes a project going here cannot take the no-infrastructure answer to, the words
AWS refuses inside a name, the answers it offers and what each becomes here — and the keel reads that
without importing any of this. What is here is what can only be answered by running code: the two stacks,
the scripts, the two pages, and the tables the keel used to hold a row of per cloud.

Every one of these was a row in a dict inside the keel, keyed by `"aws"`, until phase 10. The keel keeps
the *shape* around them — one apply at a time, apply then smoke, production behind `AUTO_PROMOTE`, a
rollback that re-applies the release before — and this package supplies what that shape cannot know.
"""
from __future__ import annotations

from slipwai.target_protocol import (
    ADD_COMMANDS,
    AGENT_RULES,
    DEPLOYMENT_SHAPES,
    DOCS_PAGES,
    FLAG_TRANSPORTS,
    IMAGE_REGISTRY,
    PIPELINE,
    PREREQUISITES,
    README_WORDS,
    REGION,
    SCRIPTS,
    SHAPES,
    TOOLS,
    Target,
)

from .docs import deployment_diagram, production_adr

#: The account's stack, applied once by `make bootstrap`, and the service's, applied per environment by
#: `make deploy`. The files are this package's own, by the path they have in it.
STACKS = {'bootstrap': ('bootstrap/main.tf', 'bootstrap/outputs.tf', 'bootstrap/variables.tf'),
    'service': ('service/auth0.tf',
               'service/cognito_external.tf',
               'service/cognito_internal.tf',
               'service/flags.auto.tfvars',
               'service/flags.tf',
               'service/frontend.tf',
               'service/ingress.tf',
               'service/main.tf',
               'service/network.tf',
               'service/no-auth0.tf',
               'service/no-frontend.tf',
               'service/outputs.tf',
               'service/production.tfvars',
               'service/rds.tf',
               'service/staging.tfvars',
               'service/variables.tf',
               'service/versions.tf')}

#: What a generated project gets under `scripts/`, by the path it lands at. These run inside a project,
#: which has no slipwai to import: the standard library only.
PROJECT_SCRIPTS = {'scripts/bootstrap.py': 'scripts/bootstrap.py',
    'scripts/check-deploy-role.py': 'scripts/check-deploy-role.py',
    'scripts/check-flags.py': 'scripts/check-flags.py',
    'scripts/deploy.py': 'scripts/deploy.py'}

#: The command-line tools `./init` and `make bootstrap` run. One list, read twice — by `preflight` before a
#: project is written and by the generated `./init` on the machine that runs it — so a project is never
#: refused for a tool its own script does not look for.
CLI_TOOLS = (('tofu', 'OpenTofu 1.12 — what applies the stacks in infra/', 'https://opentofu.org/docs/intro/install/'),
    ('aws', 'the AWS CLI — signs in to the account and configures the pipeline', 'https://aws.amazon.com/cli/'))

#: Where a built image is pushed, what the registry is called, one of its addresses as an example, and what
#: `infra/` runs a service as. `scripts/deploy.py`'s own comment block is written round these four.
REGISTRY_WORDS = {'cloud': 'AWS',
    'registry': 'ECR',
    'example': '123456789012.dkr.ecr.eu-west-2.amazonaws.com/',
    'runtime': 'Fargate'}

#: The parts of the deploy workflow that are AWS's. The job around them is the keel's.
WORKFLOW = {'cli': '      - run: |\n'
           '          curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o awscliv2.zip\n'
           '          unzip -q awscliv2.zip && sudo ./aws/install --update\n',
    'credentials': '      - uses: aws-actions/configure-aws-credentials@v6\n'
                   '        with:\n'
                   '          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}\n'
                   '          aws-region: ${{ vars.AWS_REGION }}\n'
                   '          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}\n'
                   '          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}\n',
    'build_cli': '',
    'registry_login': '      - uses: aws-actions/amazon-ecr-login@v2\n',
    'environment': '  AWS_REGION: ${{ vars.AWS_REGION }}\n'
                   '  TOFU_STATE_BUCKET: ${{ vars.TOFU_STATE_BUCKET }}\n'
                   '  IMAGE_REGISTRY: ${{ vars.IMAGE_REGISTRY }}\n'}

#: The nouns the README's *Production* section is written round.
SECTION_WORDS = {'runtime': 'one ECS service per application deployed blue/green\nbehind its own load balancer',
    'site': ' The browser app is a private S3 bucket behind CloudFront, with `/api` routed to the service, so '
            'one bundle serves every environment from the same origin.',
    'credentials': 'administrator credentials the `aws` CLI can find'}

#: The *Before `./init`* table's middle rows: what AWS in particular asks of the machine that runs the
#: first day's work. The rows around them are the same wherever a project deploys.
BEFORE_INIT = (('**OpenTofu 1.12**, on the PATH as `tofu`', '`tofu version`'),
    ('**The AWS CLI, signed in as an administrator** of the account this project will live in — a profile, SSO or '
    'environment variables, whatever the CLI finds; `AWS_PROFILE=<admin profile> ./init` is the usual spelling',
    '`aws sts get-caller-identity` names that account'),
    ('**A region**: `export AWS_REGION=eu-west-2`, or `aws configure set region eu-west-2`',
    '`aws configure get region`'))

#: What a destination puts whoever works here under. Naming the cloud is what makes it land: "no service
#: calls AWS" is a sentence an author checks themselves against.
RULES = ('- This project deploys to AWS from `.github/workflows/deploy.yml`, and a pipeline is the only path to\n'
     '  production: never `tofu apply` production by hand, and never build an image on a laptop for it — a '
     'deploy\n'
     "  is the commit's own image, pushed by digest, promoted unchanged from staging. Whether that pipeline "
     'takes\n'
     '  every green commit all the way is the `AUTO_PROMOTE` variable on the forge; where it reads `false` it '
     'stops\n'
     '  at staging and `.github/workflows/production.yml` is what deploys production, started by `make promote` '
     'or\n'
     '  from the Actions tab. `make promote` asks the forge to run it and applies nothing itself, so it is not '
     'an\n'
     '  exception to the rule above — check `make -s url ENV=production` before assuming production exists at '
     'all,\n'
     '  since without auto-promotion it does not until the first promotion. `make build smoke-image\n'
     '  PLATFORM=linux/arm64` proves an image locally; a bad release is undone by starting\n'
     '  `.github/workflows/rollback.yml` by hand with the environment to roll back; `make deploy` and `make\n'
     '  rollback` are for a person with credentials, from a checkout of `main`. `infra/` is OpenTofu; edit it as '
     'code, `tofu fmt` and `tofu\n'
     '  validate` before committing, and record a changed decision in `docs/adr/0002-production-target.md`. A\n'
     '  renamed or moved resource gets a `moved` block and one dropped from the code a `removed` block, so the\n'
     '  apply updates or forgets it rather than destroying it (`infra/README.md`). IAM the service stack '
     'declares\n'
     "  beyond this project's roles is a grant in `infra/bootstrap/main.tf` and a `make bootstrap` by a person\n"
     '  before it merges — `make check-deploy-role` says which.\n'
     '  Never put a credential in this repository: the pipeline authenticates with OIDC and carries '
     'identifiers.\n')

#: What `add-service` and `add-frontend` say afterwards about the destination. Said in the command because
#: the report says it once and the agent reads the command every time.
AFTERWARDS = {'service': '- This project deploys to AWS, and `infra/` was regenerated with the new service: its image '
               'repository is the\n'
               "  bootstrap stack's, so `make bootstrap` has to run once more — by a person with the "
               'administrator\n'
               '  credentials it needs — before the pipeline can push its image; the ECS service itself arrives '
               'with the\n'
               '  next `make deploy`. Say so when handing over. `docs/deployment.md` was redrawn with the new '
               'service;\n'
               '  `docs/adr/0002-production-target.md` is the design.\n',
    'web': '- This project deploys to AWS: `infra/service/frontend.tf` was regenerated to put the site behind '
           'CloudFront\n'
           '  with `/api` routed to the service it names, and `make deploy` uploads the bundle. Nothing to apply '
           'by hand.\n'}

#: The transport every project here has, and the one it may opt into where every backend can read it.
TRANSPORTS = {'default': 'ssm', 'opt_in': 'appconfig'}

#: Where a project deploys, as the variable, the question AWS's own CLI answers, and what to say when
#: neither does.
WHERE = ('AWS_REGION',
    ('aws', 'configure', 'get', 'region'),
    ('AWS_REGION',
    'the region the project lives in: `export AWS_REGION=eu-west-2`, or `aws configure set region eu-west-2`',
    'https://docs.aws.amazon.com/general/latest/gr/rande.html'))

# Deployment choices are independent of the bootstrap/service phase names in STACKS.
LINER_STACKS = {phase: {path: path for path in files} for phase, files in STACKS.items()}
SKIFF_STACKS = {
    "bootstrap": LINER_STACKS["bootstrap"],
    "service": {
        **{f"service/{name}": f"skiff/{name}" for name in (
            "main.tf", "database.tf", "versions.tf", "variables.tf", "outputs.tf", "flags.tf",
            "frontend.tf", "production.tfvars",
        )},
        **{path: path for path in (
            "service/cognito_internal.tf", "service/cognito_external.tf", "service/auth0.tf",
            "service/no-auth0.tf", "service/no-frontend.tf", "service/flags.auto.tfvars",
        )},
    },
}
SHAPE_ROWS = {
    "skiff": {
        "compute": "Lightsail container service",
        "database": "private Lightsail managed PostgreSQL in the same Region",
        "stacks": SKIFF_STACKS,
        "scripts": {**PROJECT_SCRIPTS, "scripts/deploy.py": "scripts/skiff_deploy.py",
                    "scripts/_deploy_common.py": "scripts/deploy.py",
                    "scripts/skiff_migrations.py": "scripts/skiff_migrations.py"},
        "environments": ("production",),
        # `make deploy` on a skiff is also the migration: `scripts/skiff_migrations.py` builds a bounded
        # wrapper over the immutable migration image and pushes it to ECR, because Lightsail has no
        # one-off task to run it in. So the job that deploys has to be signed in to the registry, where a
        # liner's deploy job never touches it — the liner migrates with an ECS task the stack declares.
        "registry_at_deploy": True,
        "guidance": "One production environment, managed HTTPS readiness checks and rolling deployments. "
                    "The database stays private, backed up and protected from destruction. Database TLS "
                    "enforcement is checked before migrations or applications start. Lightsail operators can "
                    "read container environment secrets: restrict deployment/inspection authority. Remote "
                    "migrations use a bounded, tagged temporary service with an exact result marker; failures "
                    "retain redacted logs under .build/migration-logs. Flags use live SSM values at deployment "
                    "and make flag rolls the current images. See https://docs.aws.amazon.com/lightsail/latest/"
                    "userguide/amazon-lightsail-connecting-container-service-to-database.html. PostgreSQL "
                    "connectivity follows the managed-database contract; the published tutorial uses MySQL.",
        "transition": "Converge prepares a reviewable candidate and cutover runbook; it never applies or "
                      "destroys the current module. Private Lightsail databases cannot be reached from ECS "
                      "through VPC peering. Keep the original skiff state and database until export/import "
                      "into RDS and data verification are complete, then change DNS explicitly. Snapshot "
                      "and compare counts/checksums before cutover; never turn on public database access.",
    },
    "liner": {
        "compute": "ECS Fargate",
        "database": "private RDS PostgreSQL",
        "stacks": LINER_STACKS,
        "scripts": PROJECT_SCRIPTS,
        "environments": ("staging", "production"),
        "guidance": "The full product stack: separate staging and production workspaces, private RDS, "
                    "readiness-gated blue/green services and optional site distribution.",
        "transition": "Preserve every existing database and state until a person verifies the prepared "
                      "shape transition and explicitly completes data transfer and DNS cutover. A downgrade "
                      "is never selected automatically for a data-holding product.",
    },
}

TARGET = Target(
    name="aws",
    answers={
        SHAPES: STACKS,
        DEPLOYMENT_SHAPES: SHAPE_ROWS,
        SCRIPTS: PROJECT_SCRIPTS,
        DOCS_PAGES: {
            "docs/adr/0002-production-target.md": production_adr,
            "docs/deployment.md": deployment_diagram,
        },
        TOOLS: CLI_TOOLS,
        IMAGE_REGISTRY: REGISTRY_WORDS,
        PIPELINE: WORKFLOW,
        README_WORDS: SECTION_WORDS,
        AGENT_RULES: RULES,
        ADD_COMMANDS: AFTERWARDS,
        REGION: WHERE,
        PREREQUISITES: BEFORE_INIT,
        FLAG_TRANSPORTS: TRANSPORTS,
    },
)
