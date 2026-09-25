MINOR

**`make verify` on the `aws` target fails when the service stack declares IAM the deploy role cannot create.**
The bootstrap stack gives the deploy role PowerUserAccess and IAM on roles named `<project>-*`, and nothing
held `infra/service/` to that: a generated project added an `aws_iam_user`, passed every gate, and met the
limit at the production apply — refused on `iam:CreateUser` part-way through. `check-deploy-role` reads both
stacks and fails on every `aws_iam_*` resource whose create or delete action the policies attached to the
deploy role do not grant on that kind of IAM resource, and on any IAM type it has no row for. Its message,
and `scripts/deploy.py`'s when an apply is refused on an `iam:` action anyway, name where the fix is: a
statement in `infra/bootstrap/main.tf` and a `make bootstrap` by a person with admin credentials — not the
service stack, not the pipeline and not the IAM console.

**Renaming a resource is a `moved` block, and the guidance says so.** The same project renamed a CloudFront
response-headers policy with no `moved` block; OpenTofu created the new one and destroyed the old one before
updating the distribution that still used it, and CloudFront refused with 409. `infra/README.md` on both
targets, and the production rule in `AGENTS.md`, now say that a renamed or moved resource gets a `moved` block
and one dropped from the code a `removed` block, and what `tofu plan` shows when either is right.

**Catch-up.** `slipwai migrate` brings the gate. If it fails on a stack that deploys today, the resource it
names was granted by hand outside `infra/bootstrap/`: put the grant in `bootstrap/main.tf` and run
`make bootstrap`, so the next bootstrap does not take it away.
