---
name: add-target
description: Factory-maintenance skill for adding a production target to slipwai — a second cloud beside `aws` (Azure, GCP), or a different kind of destination on the same cloud. Covers the catalog's targets block, per-option `targets` and provisioning declarations, the pruner's mirror of both, `assets/targets/<target>/`, what `project/infra.py`, `project/production.py`, `project/deploy_workflow.py` and `scripts/deploy.py` need to know about a second cloud, tests and docs. Use when asked to add, restore or scaffold a deploy target, a cloud, or a path to production in this factory.
---

# Add a production target

A **target** is where a generated project goes to production. It is a top-level dimension, asked second,
because it decides the menus that follow; `none` and `aws` ship. A target arrives with its infrastructure
and never before it — a catalog row with nothing behind it generates projects claiming a destination they
cannot reach — so this skill is the infrastructure first and the row last. `docs/aws-target.md` is the
worked example; `docs/axes.md` ("Production target") is the mechanism.

## 0. Search for the facts — this document has none that are current

Every product fact here — which managed container service, which database tier, which identity service,
which IaC provider version, what each costs idle — was searched for once and pinned. Do not carry one over
to another cloud from memory: run a WebSearch for the current answer to each row of the design table in
`docs/aws-target.md`, and read the provider's own resource documentation for every resource you write (the
`hashicorp/terraform-provider-*` repositories carry it under `website/docs/r/`, reachable where the registry is
not). Then confirm the tool choices with the user with AskUserQuestion before pinning them — the runtime, the
database shape, the IaC — the way the existing `aws` row was agreed before anything was written.

## 1. Decide the shape

- **What the target deploys.** `aws` deploys an HTTP service and proves a deploy by asking it `/health`, so it
  `requires` the `http` axis. A target for workers or jobs would not, and would need a different proof.
- **Which options it carries, and how.** For every axis option: offered under the new target or not, and if
  offered, provisioned there or merely carried (`memory` is carried; `postgres` is provisioned as RDS). An
  option whose local stand-in differs from its cloud provisioning is a *new option* owning the *same feature*
  (`auth/cognito` owns `keycloak`), so that the local files and the cloud resources go together.
- **Two long-lived environments** and no approval step, unless the user decides otherwise; ephemeral
  environments are a separate feature and out of scope here.

## 2. catalog.json

- `targets.<name>` — `label` (shown by the prompt), `requires` (axes it refuses the absent answer to),
  `reserved` (words a project's name may not contain, because this cloud names resources after the project
  and its services refuse their own brand inside those names — read every resource the stack creates from
  the project's name for the rule, the way `aws` reserves `amazon`, `aws` and `cognito` for the Cognito
  hosted-login domain).
- Each option offered under it adds `<name>` to `targets`; each option it provisions adds
  `"<name>": {"provisions": "<what>"}`; a new cloud-flavoured option follows `auth/cognito`'s shape.
- Each backend that can be built into an image for it adds `<name>` to its `targets`.

`validate_targets` and `validate_axis_targets` in `src/slipwai/targets.py` refuse the rest and hold
the pruner to the same declarations. `tests/test_targets.py` has the mechanism's tests and a `cloud`
fixture to copy.

## 3. assets/backing-services/prune.py — the other half

`AXES[<axis>]["options"][<option>]["targets"]` mirrors the catalog's, and `TARGET_REQUIRES` mirrors
`requires`; the factory refuses a catalog the pruner disagrees with. New cloud-flavoured options need an
entry with `features`, `targets`, `label` and `note`. Any new marked file the stacks carry goes into
`MARKED_FILES`.

## 4. assets/targets/<name>/ — the stacks

Read as a tree by `project/infra.py`: everything but `scripts/` lands under `infra/`, and `scripts/deploy.py`
lands at the root. The `aws` tree is the shape to follow:

- `bootstrap/` — state, the pipeline's identity, image repositories; its own state committed, encrypted.
- `service/` — one module, workspaces per environment, `for_each` over `var.services` read from the generated
  `project.auto.tfvars.json` (see `infra.service_record` for its fields). Feature-owned resources sit inside
  `# backing-service:<feature>:begin/end` comments, with their wiring into the services inside the same
  markers in `main.tf`, so a prune leaves a valid stack — `tests/test_aws_target.py` proves that for `aws`.
- `service/frontend.tf` and `service/no-frontend.tf` — one lands, as `frontend.tf`, chosen by whether the
  project has a browser app; both define the environment's public address.
- `<env>.tfvars` per environment; `outputs.tf` with `url` and `urls`, and per-feature outputs
  (`migrate_tasks`, `web_bucket`, `web_environment`) inside their regions.
- `service/flags.auto.tfvars` and `service/flags.tf` — where a project declares a feature flag and how the
  value reaches a running container without a deploy. **Not optional for a target.** A flag is the only
  thing between a merge and a customer once every commit that passes `verify` is applied, so a target that
  offers no flag mechanism offers no way to ship dark, and the constitution's
  `build-once-deploy-is-not-release` becomes unenforceable. `project/flags.py` emits each service's reader
  under any target, and `scripts/check-flags.py` (below) parses this declaration file — so a target that
  declares flags some other way brings its own gate, or the two files' shape.
- `scripts/check-flags.py` — a static gate, part of the generated `make verify`, which reads the
  declaration file against the sources: declared-and-never-read, read-and-never-declared, a new key seeded
  anything but `off`, and a key tested on one path only. Cloud-neutral except for the file it parses.

Validate offline while writing: `tofu init -backend=false` needs the provider, which a
`provider_installation { filesystem_mirror }` CLI config can serve from a downloaded zip where the registry is
unreachable.

## 5. src/slipwai/ — what a second cloud changes

- `images.py` is cloud-neutral. `IMAGE_BUILDERS` and `MIGRATIONS_IN_PRODUCTION` stay as they are unless the
  target needs a different image shape.
- `project/infra.py` — `target_files` dispatches on the target name today; a second tree means either a
  per-target module or a table keyed by target for the data file and the ADR. `production_adr` is `aws`'s
  prose and becomes per target.
- `project/production.py` — the Makefile section is cloud-neutral except for the words in its help text.
- `project/deploy_workflow.py` — the credential step (`CREDENTIALS`) and the registry login are the cloud's.
- `project/infra.py`'s `deployment_diagram` — `docs/deployment.md`, two Mermaid diagrams drawn from the project's
  answers (what runs; how a commit gets there) and regenerated by `add-service`/`add-frontend`. A second cloud
  draws its own: the nodes are the resources its stack creates, in the words its README uses.
- `assets/targets/<name>/scripts/deploy.py` — the `aws` CLI calls (`ecs run-task`, `s3 cp`, `ecr
  describe-images`) are the cloud's; the verbs are not.
- `assets/targets/<name>/scripts/bootstrap.py` — `make bootstrap`: the cloud's sign-in check and the stack's
  variables are the cloud's; reading the forge off the remote and writing variables and secrets to it are
  not, and belong in whatever shared shape a second cloud makes worth extracting.
- Anything keyed by target name: `add_commands.PRODUCTION_AFTERWARDS`, `WEB_PRODUCTION_AFTERWARDS`, and
  `preflight.TOOLS` — the tools the target's `./init` will use, checked by `generate` the moment the target
  is chosen and named in the factory README's step 1; a requirement discovered at the end of `./init` is
  the wrong moment.

## 6. Tests and docs

- `tests/test_targets.py` — the menus the target changes.
- A `tests/test_<name>_target.py` in the shape of `tests/test_aws_target.py`: files present, per-backend
  builders and migrations, `add-service`/`add-frontend` regenerating the stacks, `tofu validate` before and
  after a prune (skipping with the reason where `tofu` is absent), one image built and smoked.
- `docs/axes.md` (the target table and menus), `docs/generating.md` (the transcript), a
  `docs/<name>-target.md`, `README.md`, `docs/requirements.md`, `.github/workflows/verify.yml` for any tool the
  tests need. Prove the `none` output unchanged with the whole-matrix snapshot, and account for every file
  that differs.

## 7. Verify

`make verify` from the factory root, with `tofu` on the PATH so the validate suite runs rather than skips.
Then generate a project with the new target, apply its bootstrap stack to a real account, push, and watch
the pipeline reach production — the one proof the factory cannot run for you.
