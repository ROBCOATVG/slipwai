# azure-staff-service

A quickstart: Java on Spring, Postgres, Entra ID, no browser app and no public sign-up. It is the kit
somebody assembles by hand for the service nobody outside the company will ever open — it is called by other
services and by people who are already signed in to their work account, and it is deployed to the
subscription the company already pays for.

**It is an example and it is not a default.** Nothing installs it, nothing offers it until you do, and no
generation anywhere reaches for it. What this directory is for is to be read, copied and changed.

## Before you start: install the Azure target

```sh
slipwai target install azure
```

**On a machine without it, the interview greys this quickstart out and names that command**, the way it
does for a language it has not got: the target a quickstart answers is read as a package it needs, because
that is what it is. Install it first and the question does not arise.

## Using it

```sh
slipwai quickstart install docs/reference/azure-staff-service      # from this checkout
slipwai quickstart show azure-staff-service                        # before it does any of it
slipwai generate ledger --quickstart azure-staff-service
```

`show` first, always.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | An internal service is exactly where somebody asks "who changed this, and when?" six months later, in an audit. The workflow is modelled before it is built and delivered one stamped slice at a time |
| `target azure` | The subscription the company already has: one Container App per app deployed by revision behind the environment's own ingress, PostgreSQL Flexible Server and Entra ID, provisioned by OpenTofu |
| `language java` + `framework spring` | Two questions, because that is how people decide. The family is `java`; the framework answers startup, and `java-spring` is the backend the two together name — which is why both packages are listed under `languages` |
| `frontend none` | No screens of its own. The callers are other services and the people who already have a tool open |
| `write-model events` | The log is the truth. See below — it is the one answer here that cannot be walked back |
| `persistence postgres` | PostgreSQL Flexible Server, which is what `azure` provisions for this axis. SQLite is not offered under a managed target |
| `auth entra` | The work account people already sign in with: an app registration with the internal groups and a confidential client, in the subscription's own workforce tenant. There is no second directory to populate and nobody has a second password |
| `users none` | No public sign-up — and, on Azure, no other answer. See below |

**`write-model` is the one `./init` can never change afterwards.** The other axes here are prunable: a
project can drop Postgres for the in-memory adapter later, and pruning only ever subtracts. The rung cannot —
`state` on a service that has been keeping a log does not remove an adapter, it declares the history on disk
is no longer the truth, which is a migration somebody writes rather than a flag. The cheap direction is the
one this quickstart takes: a log folds down into tables whenever you decide it should, and state cannot be
turned back into history it never recorded.

## `users none` is a fact about Azure, not a preference

It is the least discoverable thing on this page, so it is stated rather than implied. **Azure provisions an
identity service for staff and none for customers.** The `azure` target maps the `auth` axis to Entra for the
internal directory, and on the `users` axis — the people the product is *for*, with sign-up, verification and
password reset — it provisions `auth0` and nothing of its own. Entra ID External Identities is not an answer
this target offers.

So a staff-only service on Azure answers `users none` because there is nothing else to answer, not because
somebody decided external accounts were out of scope. If this product later needs customers, the choice is
`--users auth0` and a second vendor, or `--target aws`, where `users cognito` is provisioned in the same
account as everything else. That is a decision worth meeting here rather than in the middle of generating.

## What it does not decide

- **The project's name and the service's name.** The two answers nobody else can give.
- **The deployment size — `skiff` or `liner`.** Deliberately, and for every cloud quickstart. It is the
  question "who will use this product, and what happens when it is down?" — a question about the business,
  not the stack. An internal service is not automatically a `skiff`: payroll is internal, and an outage in it
  is an incident. Nobody should inherit that answer from a file.
- **Any extension.** An extension is a third-party package; this quickstart elects none.

## It is a default, never an override

Every answer above is a flag you could have typed, and a flag you do type wins:

```sh
slipwai generate ledger --quickstart azure-staff-service --framework quarkus
```

The transcript prints every answer the quickstart gave and marks the ones that were yours.

## Changing it

Copy the directory, edit `quickstart.json`, and keep it beside your own repository — `--quickstart <a path>`
reads one where it lies. Packages are named by **range**, never by pin: one that named `==1.4.2` would hold
everyone who used it to the afternoon it was written. It is a package like any other, and
[`typescript-ui/`](../typescript-ui/README.md) states the publisher's verbs once.
