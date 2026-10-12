# slipwai-target-aws

AWS as a slipwai target: where a generated project goes to production, and everything it is given to get
there. `slipwai target install aws`, then `slipwai generate <name> --target aws`.

A project deployed here runs one ECS service per application on Fargate, deployed blue/green behind its own load balancer, with RDS Postgres where it chose Postgres, Cognito where it chose an
identity provider, and a private S3 bucket behind CloudFront where it has a browser app. All of it is applied by OpenTofu and deployed by
the trunk pipeline: `make bootstrap` once, `make deploy` per environment.

## What is in it

| Part | Where |
|---|---|
| The account stack, applied once by `make bootstrap` | `bootstrap/` |
| The service stack, applied per environment by `make deploy` | `service/` |
| What a project gets under `scripts/` | `scripts/` |
| The deployment drawing and the production ADR | `slipwai_target_aws/docs.py` |
| The protocol answers the keel reads | `slipwai_target_aws/__init__.py` |
| The row the catalog's `targets` block gets, and what this target offers | `target.json` |
| How to work on the stacks | `INFRA.md` |

## Checking it

```sh
slipwai target check .
slipwai package check .
```

The first reads the manifest, imports `TARGET` and holds it to every member the protocol asks of a managed
target. The second adds the version rule over `VERSION`, `CHANGELOG.md` and `changelog.d/`.

## What it may import

A target package may import only the keel modules [`import-surface.txt`][surface] lists for its kind, and
that file is held in both directions. Everything else a page here needs is the project's own answers, handed
to it by the keel.

[surface]: https://github.com/ROBCOATVG/slipwai/blob/main/import-surface.txt
