"""Azure as a slipwai target: every answer the keel asks a place a project is deployed to.

Microsoft Azure: one Container App per application behind the environment's own ingress,
PostgreSQL Flexible Server, Entra ID, and a static web app.

This module is the executable half of the package. `target.json` beside it is the declaration half — the
row the prompt shows, the axes a project going here cannot take the no-infrastructure answer to, the words
Azure refuses inside a name, the answers it offers and what each becomes here — and the keel reads that
without importing any of this. What is here is what can only be answered by running code: the two stacks,
the scripts, the two pages, and the tables the keel used to hold a row of per cloud.

Every one of these was a row in a dict inside the keel, keyed by `"azure"`, until phase 10. The keel keeps
the *shape* around them — one apply at a time, apply then smoke, production behind `AUTO_PROMOTE`, a
rollback that re-applies the release before — and this package supplies what that shape cannot know.
"""
from __future__ import annotations

from slipwai.target_protocol import (
    ADD_COMMANDS,
    AGENT_RULES,
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
               'service/entra_internal.tf',
               'service/flags.auto.tfvars',
               'service/flags.tf',
               'service/frontend.tf',
               'service/ingress.tf',
               'service/main.tf',
               'service/no-auth0.tf',
               'service/no-frontend.tf',
               'service/outputs.tf',
               'service/postgres.tf',
               'service/production.tfvars',
               'service/staging.tfvars',
               'service/variables.tf',
               'service/versions.tf')}

#: What a generated project gets under `scripts/`, by the path it lands at. These run inside a project,
#: which has no slipwai to import: the standard library only.
PROJECT_SCRIPTS = {'scripts/bootstrap.py': 'scripts/bootstrap.py',
    'scripts/check-flags.py': 'scripts/check-flags.py',
    'scripts/deploy.py': 'scripts/deploy.py'}

#: The command-line tools `./init` and `make bootstrap` run. One list, read twice — by `preflight` before a
#: project is written and by the generated `./init` on the machine that runs it — so a project is never
#: refused for a tool its own script does not look for.
CLI_TOOLS = (('tofu', 'OpenTofu 1.12 — what applies the stacks in infra/', 'https://opentofu.org/docs/intro/install/'),
    ('az',
    'the Azure CLI — signs in to the subscription and configures the pipeline',
    'https://learn.microsoft.com/cli/azure/install-azure-cli'))

#: Where a built image is pushed, what the registry is called, one of its addresses as an example, and what
#: `infra/` runs a service as. `scripts/deploy.py`'s own comment block is written round these four.
REGISTRY_WORDS = {'cloud': 'Azure', 'registry': 'ACR', 'example': 'acrshop1a2b3c4d.azurecr.io/', 'runtime': 'Container Apps'}

#: The parts of the deploy workflow that are Azure's. The job around them is the keel's.
WORKFLOW = {'cli': '      - run: |\n'
           '          command -v az >/dev/null 2>&1 || curl -sSL https://aka.ms/InstallAzureCLIDeb | sudo bash\n',
    'credentials': "      - if: ${{ secrets.AZURE_CLIENT_SECRET == '' }}\n"
                   '        uses: azure/login@v2\n'
                   '        with:\n'
                   '          client-id: ${{ vars.AZURE_CLIENT_ID }}\n'
                   '          tenant-id: ${{ vars.AZURE_TENANT_ID }}\n'
                   '          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}\n'
                   "      - if: ${{ secrets.AZURE_CLIENT_SECRET != '' }}\n"
                   '        env:\n'
                   '          AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}\n'
                   '          AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}\n'
                   '          AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}\n'
                   '          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}\n'
                   '        run: |\n'
                   '          az login --service-principal \\\n'
                   '            --username "$AZURE_CLIENT_ID" \\\n'
                   '            --password "$AZURE_CLIENT_SECRET" \\\n'
                   '            --tenant "$AZURE_TENANT_ID"\n'
                   '          az account set --subscription "$AZURE_SUBSCRIPTION_ID"\n',
    'build_cli': '      - run: |\n'
                 '          command -v az >/dev/null 2>&1 || curl -sSL https://aka.ms/InstallAzureCLIDeb | sudo '
                 'bash\n',
    'registry_login': '      - run: az acr login --name ${{ vars.AZURE_REGISTRY_NAME }}\n',
    'environment': '  AZURE_LOCATION: ${{ vars.AZURE_LOCATION }}\n'
                   '  AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}\n'
                   '  ARM_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}\n'
                   '  AZURE_REGISTRY_ID: ${{ vars.AZURE_REGISTRY_ID }}\n'
                   '  TOFU_STATE_RESOURCE_GROUP: ${{ vars.TOFU_STATE_RESOURCE_GROUP }}\n'
                   '  TOFU_STATE_ACCOUNT: ${{ vars.TOFU_STATE_ACCOUNT }}\n'
                   '  TOFU_STATE_CONTAINER: ${{ vars.TOFU_STATE_CONTAINER }}\n'
                   '  IMAGE_REGISTRY: ${{ vars.IMAGE_REGISTRY }}\n'}

#: The nouns the README's *Production* section is written round.
SECTION_WORDS = {'runtime': "one Container App per application deployed by revision behind\nthe environment's own ingress",
    'site': ' The browser app is a static web app with the service it names linked as its API backend, so `/api` '
            "reaches that service by the product's own rule and one bundle serves every environment from the "
            'same origin.',
    'credentials': 'an Owner sign-in the `az` CLI can find'}

#: The *Before `./init`* table's middle rows: what Azure in particular asks of the machine that runs the
#: first day's work. The rows around them are the same wherever a project deploys.
BEFORE_INIT = (('**OpenTofu 1.12**, on the PATH as `tofu`', '`tofu version`'),
    ('**The Azure CLI, signed in as an Owner** of the subscription this project will live in — `az login`, then '
    '`az account set --subscription <id>` if you have more than one. Owner rather than Contributor because the '
    'bootstrap grants the pipeline its roles, and granting access is not something Contributor may do',
    '`az account show` names that subscription'),
    ('**A region**: `export AZURE_LOCATION=uksouth`, or `az config set defaults.location=uksouth`',
    '`az config get defaults.location`'))

#: What a destination puts whoever works here under. Naming the cloud is what makes it land: "no service
#: calls Azure" is a sentence an author checks themselves against.
RULES = ('- This project deploys to Azure from `.github/workflows/deploy.yml`, and a pipeline is the only path to\n'
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
     '  apply updates or forgets it rather than destroying it (`infra/README.md`).\n'
     '  Never put a credential in this repository: the pipeline authenticates with a federated identity and '
     'carries identifiers.\n')

#: What `add-service` and `add-frontend` say afterwards about the destination. Said in the command because
#: the report says it once and the agent reads the command every time.
AFTERWARDS = {'service': '- This project deploys to Azure, and `infra/` was regenerated with the new service: its '
               'Container App\n'
               '  arrives with the next `make deploy`, and there is nothing to bootstrap — one registry holds '
               'every\n'
               "  service's images and creates a repository the first time one is pushed. `docs/deployment.md` "
               'was redrawn\n'
               '  with the new service; `docs/adr/0002-production-target.md` is the design.\n',
    'web': '- This project deploys to Azure: `infra/service/frontend.tf` was regenerated to serve the site from '
           'a\n'
           '  static web app with the service it names linked as its API backend, so `/api` reaches that service '
           'by the\n'
           "  product's own rule, and `make deploy` uploads the bundle. Nothing to apply by hand. One "
           'consequence worth\n'
           '  saying when handing over: a linked service answers only through the site, so that service no '
           'longer has a\n'
           '  public address of its own in `urls`.\n'}

#: The transport every project here has, and the one it may opt into where every backend can read it.
TRANSPORTS = {'default': 'keyvault', 'opt_in': 'appconfig'}

#: Where a project deploys, as the variable, the question Azure's own CLI answers, and what to say when
#: neither does.
WHERE = ('AZURE_LOCATION',
    ('az', 'config', 'get', 'defaults.location', '--only-show-errors'),
    ('AZURE_LOCATION',
    'the region the project lives in: `export AZURE_LOCATION=uksouth`, or `az config set '
    'defaults.location=uksouth`',
    'https://learn.microsoft.com/azure/reliability/regions-list'))

TARGET = Target(
    name="azure",
    answers={
        SHAPES: STACKS,
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
