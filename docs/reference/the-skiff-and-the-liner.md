# The skiff and the liner

A cloud target has **two shapes**:

- A **skiff** is one environment on small managed compute and a managed database. It is for a staff tool
  or an internal tool.
- A **liner** is the full product stack. It is for something whose outage is an incident.

Before there were shapes, a project that answered a cloud got one stack, whatever the project was. That
stack is correct for a product with customers. It is too much for a staff tool with twelve users, and the
bill for the idle stack shows it.

```
slipwai generate <name> --target aws --shape skiff
slipwai converge --check --shape liner        # what moving would cost, before anything is written
slipwai converge --shape liner                # prepare a candidate and a runbook. Nothing is applied
```

---

## The shape is a target package's row

`deployment_shapes` is an optional member of the target protocol. It maps `skiff` or `liner` to these
fields: `compute`, `database`, `stacks`, `scripts`, `environments`, `guidance`, `transition`, and optionally
`registry_at_deploy`. The keel checks the row. It never checks the provider. So a package can change what a
skiff runs on without teaching the keel the name of a provider.

**The compute that a skiff runs on is one named row and one stack file.** It is never a choice spread
through the infrastructure, the pipeline and the docs. Providers retire managed services. Version 2's skiff
was first written around AWS's App Runner, the AWS product with that name. AWS is retiring App Runner. The
first real project generated with the skiff shape had to move to Lightsail before version 2 had built any of
it. The lesson is not that today's answer is correct for ever. The lesson is that every answer has a limited
life, and replacing it should take a day.

The keel refuses these rows, and each refusal says "install an updated target package":

- a row that is missing any of `compute`, `database`, `guidance` or `transition`;
- a row whose stacks are not exactly `bootstrap` and `service`;
- a row whose files go outside their declared tree, or are not in the package.

The keel also checks the number of environments. **A skiff has exactly `production`. A liner has exactly
`staging` and `production`.** The keel refuses a target whose row says something else.

The two shipped target packages have these rows:

| | AWS skiff | AWS liner | Azure skiff | Azure liner |
|---|---|---|---|---|
| Compute | Lightsail container service | ECS Fargate | Container Apps Consumption, HTTP scale to zero | Container Apps Consumption, retained replicas |
| Database | Private Lightsail managed PostgreSQL, same Region | Private RDS PostgreSQL | Flexible Server on its existing firewall and TLS policy | The same Flexible Server |
| Environments | `production` | `staging`, `production` | `production` | `staging`, `production` |

A skiff on AWS also sets `registry_at_deploy`. On that skiff, `make deploy` also runs the migration, because
Lightsail has no one-off task to run it in. So the deploy job must be signed in to the registry. A liner's
deploy job never uses the registry, because the liner migrates with an ECS task that the stack declares.

---

## Which shape a new project gets

```
--shape skiff      one environment, for a staff tool
--shape liner      the full product stack
```

If you do not give `--shape`:

- **A new project starts as a skiff.**
- An existing manifest keeps the shape that it has, in `shape` in `project.json`.
- A manifest without the `shape` field reads as `liner`. That was the contract before shapes existed, and
  it must never shrink a project that already holds data without anybody noticing.

The plan says that the shape defaults from the product state. The code does not do this, and the module
gives the reason. Nothing ever passed a state in, because no manifest records one. So the parameter
depended on a value that nothing set, but it looked like a rule that somebody could rely on. The decision
that a person makes is `--shape`.

---

## Converging between them costs a data transfer, not a DNS change

`slipwai converge --shape <other>` **prepares** the move. It writes a candidate under
`.slipwai/shape-transitions/<from>-to-<to>/`. The candidate holds:

- the regenerated infrastructure, scripts, workflows, deployment docs and ADR;
- a candidate `project.json`;
- a `transition.json` that lists what the move would add and what it would retire;
- a `RUNBOOK.md`.

The command does not touch the active manifest, infrastructure, state or database. It applies, destroys,
pushes and cuts over nothing, and it runs no forge or cloud command.

The command refuses in these cases:

- the project has no managed deployment;
- the request is for the shape that the project already has;
- the target has no transition contract;
- a proposal already exists. The refusal names the `mv` command that moves the old proposal out of the way.

**The runbook starts with the warning for the shape that you leave, not the shape that you join.** A package
writes each row's `transition` as *how to leave this shape*. When the runbook printed the destination's
warning, each direction showed the other direction's warning. The move that leaves a database that the
destination's compute cannot reach never said so. The move that leaves a full stack told the operator to
import into the store that they were leaving.

On AWS, that warning is: **ECS cannot reach a private Lightsail database through VPC peering.** So moving
from skiff to liner is an export, an import over an authorised private connection, and a check of counts
and checksums. It is not a DNS change. Keep the original state and database until the move is complete.
Never turn on public database access to make the step easier.

The runbook has these steps:

1. Back up and record the current images, endpoint, migration version and row counts.
2. Compare the proposal against the live files. Validate the candidate module with `tofu init -backend=false`
   and `tofu validate`.
3. Read the provider's plan. Refuse a plan that replaces the database.
4. Prove the candidate application against that database and the existing immutable images.
5. Move DNS explicitly. Keep the old deployment for rollback.
6. Only then, install the reviewed files and the candidate manifest together.

**The convergence map records the platform change only after a person confirms the cutover.** The prepared
proposal is not that confirmation. A downgrade is an explicit request. It never discards a rung that holds
data, and it never changes that rung's store without saying so.

---

## What the shapes do not change

Both shapes use the same `make verify`, the same [release modes](release-modes.md), the same flag reader and
the same images. Languages answer nothing new. Only the infrastructure module and the pipeline differ. That
is why the shape is a decision for the target, not for the language.

---

Next: [package kinds](package-kinds.md) · [release modes](release-modes.md) ·
[bring an existing codebase](../guide/adopt.md)
