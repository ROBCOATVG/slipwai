# The Azure target

`--target azure` gives a project the same promise `--target aws` does: an image per service, two long-lived
environments, a pipeline that takes every commit passing `verify` on `main` through both, feature flags that
move without a deploy, and a rollback that is one command. What differs is the products underneath and four
places where the promise is not quite the same — each of which is a row below rather than a silence.

Read this beside [The AWS target](aws-target.md). The two pages are deliberately the same shape, and the
differences between them are the argument.

## What a project is given

| Where | What |
|---|---|
| `infra/bootstrap/` | The state storage account and its blob container, the pipeline's identity, and the container registry. Applied once, by a person; its state is committed here, encrypted. |
| `infra/service/` | One Container App per application, the environment they share, and whatever the answers asked for — the database, the staff identity, the site. `staging` and `production` are workspaces over it, each in a resource group of its own. |
| `scripts/bootstrap.py`, `scripts/deploy.py`, `scripts/check-flags.py` | `make bootstrap`, and the production verbs: push, deploy, rollback, promote, migrate, smoke, url, flag, flags. |
| `.github/workflows/deploy.yml`, `production.yml`, `rollback.yml` | The pipeline, the promotion and the undo. |
| `infra/README.md`, `docs/deployment.md`, `docs/adr/0002-production-target.md` | The walk-through, the drawing, and the decision record with the costs. |

## What it costs, against the other cloud

Matched shapes, list price, on demand. The Azure replica is 0.25 vCPU / 0.5 GiB — the same size as the
smallest Fargate task the AWS target runs.

| Line | `aws` | `azure` |
|---|---|---|
| Compute per service | $9.01, a Fargate task | **$5.91**, a Container Apps replica at the idle rate, ingress and managed TLS included |
| Load balancing per service | **$18.43**, an ALB | **$0** — there is no per-service resource |
| Postgres | $13.98, RDS `db.t4g.micro` + 20 GB | $16.09, Flexible Server `B_Standard_B1ms` + 32 GB, its minimum |
| Registry | ECR, pennies | $5.08, one Basic registry for the whole project |
| Staff identity | Cognito Essentials, free at this scale | Entra ID, included with the subscription |
| Browser app | CloudFront + S3, free tier at this scale | $9/environment, Static Web Apps Standard |

**The per-service load balancer is the whole story.** AWS bills an ALB for every service — $18.43 against a
$9.01 task — so a service costs $27.44 before it serves a request, and each new service adds about $55
across two environments. Container Apps folds the ingress and the certificate into the platform, so a
service is one replica and nothing else. The gap widens with every service `add-service` creates.

One asymmetry worth knowing: Container Apps bills **active** CPU-seconds at several times the idle rate, so
a saturated 0.25 vCPU replica reaches about $20 rather than $6. It still does not lose here, because the
Fargate task needs its balancer beside it whatever it is doing — task-plus-ALB is $27.44 — and the crossover
is at sizes where a project has moved off the Consumption profile anyway. That is the day to re-price the
table in the generated ADR.

Two levers, both real and both already built. `AUTO_PROMOTE=false` leaves production uncreated until the
first `make promote`, which is the whole of one environment's bill. And `min_replicas = 0` in
`staging.tfvars` lets staging sleep between uses, at the price of a cold start on the first request after it
has — `make smoke` runs immediately after the deploy that warmed it, so the gate never sees one, and a
person opening staging after lunch does.

## Four things that are not like-for-like

A "no" here is written down with its reason, not left as a missing row.

### 1. The linked service answers only through the site

A container app linked to a static web app as its API backend is given an identity provider that rejects
anything not proxied by the site, and may be linked to one static web app at a time. So in a project with a
browser app, the api service behind the site has no public address of its own — where on AWS it also has
its own CloudFront distribution in the `urls` output.

This is *stricter* than the AWS shape, not weaker: there, the load balancer is public. But `urls` means
something different under it, so the output says so and the service linked is named in `web_api_service`.
Every other service is unlinked and keeps its own address exactly as it would on AWS, because the site only
ever fronted one of them either way.

The rest of this row is what it buys. Static Web Apps serves its own content, so there is no second,
publicly reachable origin to keep private — no bucket, no origin access control, no policy. And `/api` is
proxied to the *same path* on the container app by the product's own rule, so the single-origin contract
`vite.config.ts`, `flags.ts` and the generated `/api/flags` route rest on is the product's rather than a
routing rule this stack writes. `make smoke` is unchanged from the AWS target's for exactly that reason:
with a site in front it asks `/` for uncached HTML and then `/api/health` expecting the service's own
`404 {"error":"notFound"}`, which is a path the service does not have either way.

Azure Front Door was the first choice here and was dropped. It costs about $35 an environment against $9,
and below its Premium tier — some $330 a month — it cannot reach a *private* storage origin at all, so the
Front Door shape would have left the `$web` blob endpoint publicly reachable beside the CDN, where AWS gets
a private bucket free through origin access control. It stays in the generated ADR as the documented upgrade
for a WAF, custom domains and multi-region.

### 2. The opt-in flag transport puts an SDK in the image

AWS's `flag_transport = "appconfig"` is an agent container beside the application, read over loopback, so no
image gains an AWS SDK in any language. Container Apps has no such sidecar, and writing one would mean a
Dockerfile, which this factory does not have for the reason it has no hand-written Compose file. So
`appconfig` here means the TypeScript reader calls `@azure/app-configuration` under the app's managed
identity.

It is confined to the one backend that has a reader — `flag_route.OPT_IN_TRANSPORT` is what confines it, and
`tofu` refuses the answer in a project whose backends cannot read it — and it is chosen per environment, so
it is taken on deliberately or not at all. The `keyvault` default stays SDK-free for every backend, which is
the property that mattered. `check-flags.py` refuses a slice that calls App Configuration directly for the
same reason it refuses one that reads the agent on loopback over there.

The free tier of App Configuration also allows **one store per subscription per region**, so a second
environment opting in needs the standard tier at roughly $36 a month. That is the real price of a flip
without a restart here.

### 3. There is no *first-party* customer-identity answer

`--users` under `azure` offers `none` and `auth0`, where `aws` offers a second Cognito user pool as well.
The missing row is Microsoft's own, and the reason is worth stating precisely, because "Azure cannot do
customer sign-up" would be false: services on Azure do customer sign-up all the time. They mostly do it with
something that is not an Azure resource — Auth0, Okta, Clerk, the framework's own identity tables — and that
is the row this factory now carries.

What Azure has no answer for is a customer directory **the stack can declare**. Cognito is a resource in
your AWS account, made by the same credential and in the same apply as the load balancer. Its Microsoft
counterpart is a separate *tenant*: a directory-plane object, not a subscription one. That is also why the
staff answer worked — `auth/entra` is an app registration inside the tenant your subscription already
trusts, so there is nothing to create.

Checked against the providers rather than asserted, because this is the kind of claim that ages badly
(`tofu providers schema -json`, azurerm 5.5.0 and azuread 3.9.0):

| What the axis needs | What exists |
|---|---|
| An Entra External ID tenant | **No resource.** The only CIAM directory either provider creates is the legacy `azurerm_aadb2c_directory` |
| A sign-up / sign-in user flow | **No resource.** `azuread_user_flow_attribute` makes a custom *attribute* for a flow something else already made |
| A credential to configure it | The `azuread` provider is per tenant, and the pipeline's federated identity lives in the workforce one |

So the sign-up, verification and password reset this axis promises have no declarable form at all: they
would be raw Microsoft Graph calls in a script, in a tenant the pipeline cannot bootstrap itself into.
`azapi` does not rescue it — it speaks ARM, and user flows are Graph. A catalog row with nothing working
behind it is the half-ported shape this factory refuses everywhere else, so Microsoft's product is not a row
and this table is the record of why.

`--users auth0` is the answer instead, and it is offered under `aws` too: a third-party issuer is not a
property of a cloud. What it costs is the first row in this factory whose infrastructure is **not** created
by the cloud credential — `docs/auth0-identity.md` has that in full.

### 4. Image tags are not immutable

ECR refuses a push to a tag that already exists, so rebuilding a commit is a defect the registry catches. A
Basic container registry has no such policy: registry-wide tag immutability and untagged-manifest retention
are both Premium features, at several times the price of everything else in the cost table put together.

The pipeline is the only thing that pushes and it pushes the commit it checked out, so a replaced tag is not
reachable by accident. It is simply not *refused*. A project that needs it refused moves the registry to
Premium and adds the policy; the generated ADR carries the row so that decision has somewhere to be
recorded.

## What else differs, and is not a loss

- **Blue/green is a revision.** A deploy creates a new revision of each container app; it takes no requests
  until its readiness probe passes, and then takes all of them at once. Where AWS runs both revisions for
  `bake_minutes` and then drops one, Container Apps runs a revision that has stopped taking traffic until it
  is deactivated — so the cost is continuous rather than bounded, and the variable is `kept_revisions`: one
  in production, so a rollback is a change of traffic weight and costs an extra replica for as long as it is
  kept; none in staging, so a rollback starts the previous image again.
- **The revision is named by the platform, not by the commit.** A revision suffix must be unique for the
  lifetime of a container app, and `make rollback` re-runs a commit that has already had one — so naming
  revisions after commits would make the *second* rollback a name collision, which nothing here could catch
  and nobody would hit until it mattered. Which commit a revision runs is the image tag on it.
- **Staff identity is app roles, not groups.** Entra can put group membership in a token only as the groups'
  object ids, so `OIDC_GROUP_ADMIN` would have been a GUID, and creating the groups would have needed
  `Group.ReadWrite.All` — permission over the whole directory rather than over this one application. An app
  role is part of the application object, is covered by the narrow permission the bootstrap grants, and
  arrives in the `roles` claim as the same plain string Cognito puts in `cognito:groups`. `OIDC_GROUPS_CLAIM`
  is `roles` here and `groups` in Keycloak, which is one fewer difference than Cognito leaves.
- **A directory permission is a prerequisite of one answer, not of the target.** An app registration is a
  directory object, outside the subscription's RBAC, so Owner of the subscription does not let the pipeline
  create one. The bootstrap stack grants the deploy identity `Application.ReadWrite.OwnedBy` — the narrow
  Graph role that covers applications it owns and nothing else — and that grant lives inside the `keycloak`
  marker, so a project that answered `--auth none` asks for no directory permission at all. Making the grant
  needs a Privileged Role Administrator, which `infra/README.md` lists beside the answer rather than beside
  the target.
- **`make flags` cannot say who.** SSM keeps the identity that wrote each version of a parameter beside it;
  Key Vault keeps a version's timestamps and not its author. So the command prints the value and when it
  last moved, and says plainly that the author is in the vault's diagnostic log if one is enabled.
- **A rollback restores the whole bundle.** On S3 the hashed assets stay in the bucket for ever and
  `index.html` is the pointer at them, so restoring the pointer restores the release. Static Web Apps
  replaces its content wholesale on every deployment, so `make deploy` keeps an archive of each release's
  bundle in the state container and `make rollback` re-uploads it.

## What the factory proves, and what it cannot

- **Every stack validates against the real providers.** `tests/test_azure_stack.py` runs `tofu validate`
  over the bootstrap and service stacks of a maximal and a minimal project, and again after `./init` has
  pruned the maximal one down to the in-memory store and no identity — so a pruned stack is still one stack.
  The pinned azurerm, azapi and azuread providers are downloaded once per run for it.
- **The apply-time decisions `tofu validate` cannot see are asserted as text.** The RBAC replication wait
  before the first secret is written; the buildpack launcher in front of a migrate command; the traffic
  weight naming the latest revision rather than a suffix; the server half of the TLS policy stated in both
  directions. Each of those is a first-apply failure that reads correctly in the file.
- **`make bootstrap` is proved to its decisions, not to a subscription.** `scripts/bootstrap.py --plan`
  prints what it would do — which forge it read off the remote, which credential shape follows, what it
  would apply and configure — and the test drives it with a GitHub-shaped and a Gitea-shaped remote, and
  without a location (a refusal, because Azure has no ambient region to fall back on).
- **What the container is told is asserted, because nothing runnable can catch it.** The emitted
  `docker-compose.yml` runs `postgres:17-alpine` with no TLS, so it accepts a connection a Flexible Server
  refuses — every local gate passes on a project whose first deploy would fail. `tests/test_postgres.py`
  asserts the environment per backend; `images.POSTGRES_SSLMODE` is keyed by the managed Postgres rather
  than by the cloud, because the answer is a property of the server's certificate chain.
- **The TypeScript `PGSSLMODE` value here is inherited, not measured.** RDS forced `no-verify` because its
  certificate chains to a private Amazon root Node does not bundle; a Flexible Server's chains to DigiCert
  Global Root G2 and Microsoft RSA Root CA 2017, which Node does — so `require`, and real verification, may
  work. Every value in the table is safe as it stands (both encrypt, and neither fails where the other
  succeeds), but one is weaker than it may need to be. What is owed is a single run of node-postgres against
  a real Flexible Server. Until somebody has done it the table says what is known to work.
- **The apply is unprovable by construction.** It ends in somebody's subscription. What proves it is `make
  smoke` against the environment the pipeline just deployed, which is why the pipeline runs it after each
  apply and why the first thing to do with a generated project is to push it. The initial implementation showed that no gate ever
  applies a stack — is as true here as it is of `aws`, and a second cloud doubles what that gap covers.

## What a third cloud would need

The same list [The AWS target](aws-target.md#the-next-cloud-is-a-row) gives, now with two examples of each:

1. `catalog.json`: a `targets.<name>` row with a label, `requires`, `managed` and its reserved words by
   class; `"<name>"` in the `targets` of every option offered under it; an `"<name>"` key on each option it
   provisions differently. `assets/backing-services/prune.py` mirrors all of it.
2. `assets/targets/<name>/`: the two stacks and the three scripts, read as a tree by `project/infra.py`,
   with feature-owned parts inside `backing-service:<feature>` markers and a `frontend.tf`/`no-frontend.tf`
   pair.
3. A row in each per-target table: `targets.TOOLS`, `preflight.REGION`, `rules.CLOUD` and
   `PRODUCTION_GUIDANCE`, `target_docs.PAGES`/`PREREQUISITES`/`WORDS`, `deploy_workflow.CLOUD_STEPS`,
   `flag_route.DEFAULT_TRANSPORT`/`OPT_IN_TRANSPORT`, `production.REGISTRY`, `add_commands`'s two
   afterwards tables — and a `<name>_docs.py` module beside `aws_docs.py` and `azure_docs.py`, because a
   deployment drawing and a production ADR have no general version to parameterise.
4. `images.POSTGRES_SSLMODE` gains a block keyed by whatever that cloud provisions the store as, *measured*
   against it.
5. `tests/test_<name>_target.py` and `tests/test_<name>_stack.py` in the shape of these two.

`.claude/skills/add-target/SKILL.md` is the procedure.
