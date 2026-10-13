---
name: add-target
description: Add somewhere a project can be deployed to — its two shapes, its stack, its pipeline and its preflight. Use when adding a cloud or a platform, not a language or a tool.
---

# Adding a target

A target is **where a project goes to production**. `aws` and `azure` are the two the keel still carries;
phase 10 takes them out into packages, so read `docs/slipwai-2-plan.md`'s phase 10 before starting a third
— the shape of what you write depends on whether the protocol has landed.

## A target is two shapes, not one stack

| Shape | For | What it is |
| --- | --- | --- |
| **Skiff** | A staff or internal tool. An outage is an inconvenience | One environment, the smallest managed compute and database, rolling deploys, no second balancer |
| **Liner** | A product with customers. An outage is an incident | Two environments, per-service balancers, blue/green, a CDN where there is a site |

**Write the liner first and cut it down.** A skiff written first grows into a liner by accident, and what
it grows is the half of a liner somebody remembered.

A new project starts as a skiff unless `--shape liner` says otherwise, and a manifest written before
shapes existed keeps the liner it was generated as — never guessed from anything else, because a shape
guessed from a field nobody maintains is a staging environment somebody loses. `slipwai converge --shape
liner` is the step up: it keeps the database and its data and writes the runbook for the one thing a
person does by hand. Each shape's row carries the warning for *leaving* that shape, which is the one
converge prints.

## The compute is one row

Version 2's skiff was written around AWS App Runner. App Runner is being sunsetted, and the first real
project on the shape had to be moved to Lightsail before version 2 had built any of it. **The answer has a
shelf life.** So the compute a shape runs on is one named row in the target's table and one stack file —
never a choice spread through the infrastructure, the pipeline and the prose. Replacing it should cost a
day.

## What you write

1. **The stacks**, under `assets/targets/<name>/`: a bootstrap module and a service module, one file per
   concern, every provider pinned. Both shapes, and both validating against the real provider before and
   after a prune. **A shape's set is closed.** A file in the skiff's set may not read a declaration that
   lives only in a file the skiff leaves out: that is an `Error: Reference to undeclared resource` on
   every generated project, and it is invisible until something generates that shape and runs `tofu
   validate` on it — so write the test that does, with a browser app, for both shapes.
2. **The pipeline** the trunk runs: build, push, deploy, and the one that undoes it. The workflow that
   undoes it offers the environments the *shape* has, not two. And if a shape's `make deploy` reaches the
   image registry itself — a shape with no one-off task to migrate in does — say so with
   `registry_at_deploy` on its row, so the job that deploys is signed in; a shape that does not must not
   ask for a sign-in it never uses.
3. **The preflight**: what has to be true before the first deploy, checked and said rather than discovered
   by a failing apply. And **the setup hook** — `setup`, a script under `scripts/` that `./init` runs first:
   it installs the target's tools on the machine it finds itself on and settles whatever the target has to
   be told once, a region say, with a default on offer. The keel runs it and reads nothing from it; what a
   region is, or which package manager a tool comes from, is the target's to know and never the keel's.
4. **The axis provisioning**: for each option a backend may answer — a Postgres, an OIDC issuer, a bucket —
   what this target provisions for it, and the prune row that removes it when a project chose otherwise.
5. **The docs page**: what a person has to do in their own account, in order, once.
6. **The reserved words**: names a project may not use because the provider has taken them.

## What you do not write

Anything language-specific. A target takes an image and a port; **languages answer nothing new for a new
target.** If you find yourself needing a backend to do something, the design is wrong — that is what keeps
a shape a target's decision rather than everybody's.

## The gate

```sh
PYTHONPATH=src:tests python3 -m unittest tests.test_aws_stack
```

Every variant — maximal, minimal, and maximal pruned to minimal — validates against the pinned provider.
It skips without a language installed, because it generates a real project; a language package's own
matrix job is where it runs.

## The mistake worth naming

**Making the second environment optional on the liner.** It is the thing that makes blue/green meaningful,
and a liner without it is a skiff with a bigger bill.
