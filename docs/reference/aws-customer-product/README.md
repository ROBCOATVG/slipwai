# aws-customer-product

This is a quickstart. It gives Python behind, React in front, Postgres, and two Cognito user pools: one for
the public, and one for the staff who administer the public. It is the kit that somebody puts together by
hand the first time that a product has *customers* and not only users. The product has its own browser app,
a sign-up that anybody on the internet can complete, and an administration side behind a different login.

**It is an example, and it is not a default.** The keel carries it, so the interview lists it. But the
interview never selects it, and no generation uses it unless you ask. This directory is here for you to
read, copy and change.

## Before you start: install the AWS target

```sh
slipwai target install aws
```

**On a machine without the AWS target, the interview greys out this quickstart and names that command.** It
does the same for a language that the machine does not have. The interview treats the target that a
quickstart answers as a package that the quickstart needs, because that is what it is. Install the target
first, and this does not happen.

## Using it

```sh
slipwai quickstart list                                        # this keel carries it; nothing to install
slipwai quickstart show aws-customer-product                   # what it would do, before it does any of it
slipwai generate storefront --quickstart aws-customer-product
```

Always run `show` first.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | People will ask a product that the public signs up for what happened: when an account was created, when a subscription changed, who was an administrator at the time. That is a modelled workflow, not a set of field updates |
| `target aws` | The company's own AWS account, provisioned by OpenTofu and deployed by the trunk pipeline, with Cognito and the browser app in S3 behind CloudFront. The compute depends on the shape: ECS behind a load balancer on a liner, a Lightsail container service on a skiff |
| `language python` | The service. One answer, and most teams that start a product already have somebody for it |
| `frontend react-vite` | The browser app is part of the product, not something added later. The customer's sign-up and login are in it |
| `write-model events` | The log is the truth. See below: this is the one answer here that you cannot change back |
| `persistence postgres` | What `aws` provisions for this axis: RDS PostgreSQL on a liner, Lightsail managed PostgreSQL on a skiff. SQLite is not offered under a managed target, and the in-memory adapter would lose the log at every deploy |
| `auth cognito` | The staff. A user pool with the internal groups, a hosted login and a confidential client, provisioned in the same account as everything else. There is no second vendor to buy, bill and audit |
| `users cognito` | The customers, in a **second** user pool: self-registration, verification, password reset, and a public PKCE client that the browser app owns. It is never the same realm as the staff directory, even with the same vendor. The two axes exist to keep that difference |

**`write-model` is the one answer that `./init` can never change later.** You can prune every other axis
above. For example, a project can drop Postgres for the in-memory adapter later, and pruning only removes
things. You cannot do that with the rung. On a service that has kept a log, changing to `state` does not only
remove an adapter. It declares that the history on disk is no longer the truth. That needs a migration that
somebody writes. It is not a flag. For a product that the public signs up for, `events` is the answer that
you can make on day one and cannot make on day four hundred.

## Why `typescript` is in `languages` when the service is Python

The quickstart must list `typescript`. If you delete it, you will find out at generation, not here.

A browser app is written by the loaded language family that answers the npm workspace. The keel names no
such family itself. If no such family is loaded, `--frontend react-vite` is *unavailable*, not refused: the
frontend menu collapses to `none`, and the quickstart's answer cannot be carried out.

`typescript` is the family that answers the npm workspace. It is not a second service. Nothing is generated
in it except the browser app's own workspace. It is the package that makes `frontend react-vite` possible.

## What it does not decide

- **The project's name and the service's name.** Nobody else can give these two answers.
- **The deployment size: `skiff` or `liner`.** This is deliberate. The question is "who will use this
  product, and what happens when it is down?". The interview asks it for every cloud quickstart, because
  the answer is about the business, not about the stack. A kit that chose `liner` without asking would
  commit a team to the full product stack. A kit that chose `skiff` without asking would put a product that
  the public signs up for in a single environment, where an outage is only an inconvenience. Nobody should
  inherit either answer as a default.
- **Any extension.** An extension is a third-party package. This quickstart elects none.

## It is a default, never an override

Every answer above is a flag that you could have typed. A flag that you do type wins:

```sh
slipwai generate storefront --quickstart aws-customer-product --users auth0
```

The transcript prints every answer that the quickstart gave, and marks the answers that were yours.

## Changing it

Copy the directory and edit `quickstart.json`. Keep it beside your own repository. `--quickstart <a path>`
reads a quickstart where it is. Packages are named by version **range**, never by an exact pin. A
quickstart that named `==1.4.2` would hold everybody who used it to the afternoon that it was written. A
quickstart is a package like any other, and [`typescript-ui/`](../typescript-ui/README.md) lists the
publisher's verbs.
