# aws-customer-product

A quickstart: Python behind, React in front, Postgres, and two Cognito user pools — one for the public and
one for the staff who administer them. It is the kit somebody assembles by hand the first time a product has
*customers* rather than users: a browser app of its own, a sign-up anyone on the internet can complete, and
an administration side behind a login that is not the same login.

**It is an example and it is not a default.** Nothing installs it, nothing offers it until you do, and no
generation anywhere reaches for it. What this directory is for is to be read, copied and changed.

## Before you start: install the AWS target

```sh
slipwai target install aws
```

**On a machine without it, the interview greys this quickstart out and names that command**, the way it
does for a language it has not got: the target a quickstart answers is read as a package it needs, because
that is what it is. Install it first and the question does not arise.

## Using it

```sh
slipwai quickstart list                                        # this keel carries it; nothing to install
slipwai quickstart show aws-customer-product                   # what it would do, before it does any of it
slipwai generate storefront --quickstart aws-customer-product
```

`show` first, always.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | A product the public signs up for will be asked what happened — when an account was created, when a subscription changed, who an administrator was at the time. That is a modelled workflow, not a set of field updates |
| `target aws` | The company's own AWS account: ECS behind a load balancer, RDS, Cognito, and the browser app in S3 behind CloudFront, provisioned by OpenTofu and deployed by the trunk pipeline |
| `language python` | The service. One answer, and the one most teams starting a product already have somebody for |
| `frontend react-vite` | The browser app is part of the product rather than something bolted on later: the customer's sign-up and login live in it |
| `write-model events` | The log is the truth. See below — it is the one answer here that cannot be walked back |
| `persistence postgres` | RDS, which is what `aws` provisions for this axis. SQLite is not offered under a managed target, and in-memory would lose the log on every deploy |
| `auth cognito` | The staff. A user pool with the internal groups, a hosted login and a confidential client, provisioned in the same account as everything else — no second vendor to buy, bill and audit |
| `users cognito` | The customers, in a **second** user pool: self-registration, verification, password reset, and a public PKCE client the browser app owns. Never the same realm as the staff directory, even on the same vendor — that is the distinction the two axes exist to keep |

**`write-model` is the one `./init` can never change afterwards.** Every other axis above is prunable: a
project can drop Postgres for the in-memory adapter later, and pruning only ever subtracts. The rung cannot.
`state` on a service that has been keeping a log does not take an adapter away, it declares that the history
on disk is no longer the truth, and that is a migration somebody writes rather than a flag. For a product the
public signs up for, `events` is the answer you want to have made on day one and cannot make on day four
hundred.

## Why `typescript` is in `languages` when the service is Python

Because it has to be, and the reader who deletes it will find out at generation rather than here. A browser
app is written by whichever loaded language family answers the npm workspace, and the keel names none itself
— with no such family loaded, `--frontend react-vite` is not refused so much as *unavailable*: the frontend
menu collapses to `none` and the answer this quickstart gives cannot be carried out. `typescript` is the
family that answers it. It is not a second service and nothing is generated in it beyond the browser app's
own workspace; it is the package that makes `frontend react-vite` mean anything.

## What it does not decide

- **The project's name and the service's name.** The two answers nobody else can give.
- **The deployment size — `skiff` or `liner`.** Deliberately. It is the question "who will use this product,
  and what happens when it is down?", and it is asked of every cloud quickstart because the answer is about
  the business and not about the stack. A kit that quietly chose `liner` would commit a team to the full
  product stack, and one that quietly chose `skiff` would put a product the public can sign up for in a
  single environment where an outage is an inconvenience. Neither is a default anybody should inherit.
- **Any extension.** An extension is a third-party package; this quickstart elects none.

## It is a default, never an override

Every answer above is a flag you could have typed, and a flag you do type wins:

```sh
slipwai generate storefront --quickstart aws-customer-product --users auth0
```

The transcript prints every answer the quickstart gave and marks the ones that were yours.

## Changing it

Copy the directory, edit `quickstart.json`, and keep it beside your own repository — `--quickstart <a path>`
reads one where it lies. Packages are named by **range**, never by pin: one that named `==1.4.2` would hold
everyone who used it to the afternoon it was written. It is a package like any other, and
[`typescript-ui/`](../typescript-ui/README.md) states the publisher's verbs once.
