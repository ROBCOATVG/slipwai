# The skiff and the liner

A cloud target has **two shapes**. A **skiff** is one environment on small managed compute and a managed
database, for a staff or internal tool. A **liner** is the full product stack, for something whose outage is
an incident.

Today a project that answers a cloud gets one stack whatever it is — which is right for a product with
customers and too much for a staff tool with twelve users, and the idle bill says so.

```
slipwai generate <name> --target aws --shape skiff
slipwai converge --check --shape liner        # what moving would cost, before anything is written
slipwai converge --shape liner                # prepare a candidate and a runbook. Nothing is applied
```

---

## The shape is a target package's row

`deployment_shapes` is an optional member of the target protocol: `skiff` or `liner` → `compute`,
`database`, `stacks`, `scripts`, `environments`, `guidance`, `transition`, and optionally
`registry_at_deploy`. The keel checks the row and never the provider — so a package can change what a skiff
runs on without teaching the keel a provider's name.

**The compute a skiff runs on is one named row and one stack file, never a choice spread through the
infrastructure, the pipeline and the docs.** Managed services get retired: version 2's skiff was written
around AWS's App Runner — the AWS product of that name — which is being sunsetted, and the first real
project generated on the shape had to be moved to Lightsail before version 2 had built any of it. The lesson is not that today's answer is right
for ever; it is that the answer has a shelf life, and replacing it should cost a day.

The keel refuses a row that is short of any of `compute`, `database`, `guidance` or `transition`, a row
whose stacks are not exactly `bootstrap` and `service`, and a row whose files escape their declared tree or
are not in the package — each naming "install an updated target package". And it holds the environment
count: **a skiff has exactly `production`; a liner has exactly `staging` and `production`.** A target whose
row says otherwise is refused.

As the two shipped target packages have it:

| | AWS skiff | AWS liner | Azure skiff | Azure liner |
|---|---|---|---|---|
| Compute | Lightsail container service | ECS Fargate | Container Apps Consumption, HTTP scale to zero | Container Apps Consumption, retained replicas |
| Database | Private Lightsail managed PostgreSQL, same Region | Private RDS PostgreSQL | Flexible Server on its existing firewall and TLS policy | The same Flexible Server |
| Environments | `production` | `staging`, `production` | `production` | `staging`, `production` |

A skiff on AWS also sets `registry_at_deploy`: `make deploy` there is also the migration, because Lightsail
has no one-off task to run one in, so the deploying job has to be signed in to the registry. A liner's
deploy job never touches it — the liner migrates with an ECS task the stack declares.

---

## Which shape a new project gets

```
--shape skiff      one environment, for a staff tool
--shape liner      the full product stack
```

With no `--shape` given, **a new project starts as a skiff** and an existing manifest keeps the shape it has
(`shape` in `project.json`; a manifest without the field reads as `liner`, which is the pre-shape contract
and must never silently shrink a project that already holds data).

The plan says the shape defaults from the product state. It does not, and the reason is written in the
module: nothing ever passed a state in — no manifest records one — so the parameter steered by a mark
nothing sets, which reads as a rule somebody could rely on. The decision a person makes is `--shape`.

---

## Converging between them costs a data transfer, not a DNS change

`slipwai converge --shape <other>` **prepares**. It writes a candidate under
`.slipwai/shape-transitions/<from>-to-<to>/` — the regenerated infrastructure, scripts, workflows,
deployment docs and ADR, a candidate `project.json`, a `transition.json` listing what the move would add and
what it would retire, and a `RUNBOOK.md`. The active manifest, infrastructure, state and database are
untouched. Nothing is applied, destroyed, pushed or cut over, and no forge or cloud command runs.

It refuses a project with no managed deployment, a request for the shape the project already has, and a
target with no transition contract. It refuses to write over an existing proposal, naming the `mv` that
moves the old one aside.

**The runbook is headed by the warning that belongs to the shape being left, not the one being joined.** A
package writes each row's `transition` as *how to leave this shape*. Printing the destination's meant each
direction showed the other one's warning: the move that leaves a database the destination's compute cannot
reach never said so, and the move that leaves a full stack told the operator to import into the store being
left behind.

What that warning is, concretely, on AWS: **a private Lightsail database cannot be reached from ECS through
VPC peering**, so skiff → liner is an export, an import over an authorised private connection, and verified
counts and checksums — not a DNS change. Keep the original state and database until that is done. Never turn
on public database access to make the step convenient.

The runbook's steps are: back up and record the current images, endpoint, migration version and row counts;
compare the proposal against the live files and validate the candidate module with
`tofu init -backend=false` and `tofu validate`; read the provider's plan and refuse one that replaces the
database; prove the candidate application against that database and the existing immutable images, then move
DNS explicitly, keeping the old deployment for rollback; and only then install the reviewed files and the
candidate manifest together.

**The convergence map records the platform change only after a person confirms the cutover.** The prepared
proposal is not that receipt. And a downgrade is an explicit request that never discards a data-holding rung
or silently changes its store.

---

## What the shapes do not change

The same `make verify`, the same [release modes](release-modes.md), the same flag reader and the same images.
Languages answer nothing new. Only the infrastructure module and the pipeline differ — which is what keeps
the shape a target's decision and not a language's.

---

Next: [package kinds](package-kinds.md) · [release modes](release-modes.md) ·
[bring an existing codebase](../guide/adopt.md)
