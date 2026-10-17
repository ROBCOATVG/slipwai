# azure-staff-service

This is a quickstart. It gives Java on Spring, Postgres and Entra ID, with no browser app and no public
sign-up. It is the kit that somebody puts together by hand for a service that nobody outside the company
will ever open. Other services call it. People who are already signed in to their work account use it. It
is deployed to the Azure subscription that the company already pays for.

**It is an example, and it is not a default.** The keel carries it, so the interview lists it. But the
interview never selects it, and no generation uses it unless you ask. This directory is here for you to
read, copy and change.

## Before you start: install the Azure target

```sh
slipwai target install azure
```

**On a machine without the Azure target, the interview greys out this quickstart and names that command.**
It does the same for a language that the machine does not have. The interview treats the target that a
quickstart answers as a package that the quickstart needs, because that is what it is. Install the target
first, and this does not happen.

## Using it

```sh
slipwai quickstart list                                   # this keel carries it; nothing to install
slipwai quickstart show azure-staff-service               # what it would do, before it does any of it
slipwai generate ledger --quickstart azure-staff-service
```

Always run `show` first.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | An internal service is exactly where somebody asks "who changed this, and when?" six months later, in an audit. The workflow is modelled before it is built, and it is delivered one stamped slice at a time |
| `target azure` | The subscription that the company already has: one Container App for each app, deployed by revision behind the environment's own ingress, with PostgreSQL Flexible Server and Entra ID, provisioned by OpenTofu |
| `language java` + `framework spring` | Two questions, because people decide in two steps. The family is `java`. The framework is the second question. `java-spring` is the backend that the two answers together name, so both packages are listed under `languages` |
| `frontend none` | The service has no screens of its own. Its callers are other services, and people who already have a tool open |
| `write-model events` | The log is the truth. See below: this is the one answer here that you cannot change back |
| `persistence postgres` | PostgreSQL Flexible Server, which is what `azure` provisions for this axis. SQLite is not offered under a managed target |
| `auth entra` | The work account that people already sign in with: an app registration with the internal groups and a confidential client, in the subscription's own workforce tenant. There is no second directory to fill, and nobody has a second password |
| `users none` | No public sign-up. On Azure, there is no other answer. See below |

**`write-model` is the one answer that `./init` can never change later.** You can prune the other axes here.
For example, a project can drop Postgres for the in-memory adapter later, and pruning only removes things.
You cannot do that with the rung. On a service that has kept a log, changing to `state` does not only remove
an adapter. It declares that the history on disk is no longer the truth. That needs a migration that
somebody writes. It is not a flag.

This quickstart takes the cheap direction. You can fold a log down into tables whenever you decide to. You
cannot turn state back into history that it never recorded.

## `users none` is a fact about Azure, not a preference

This is the hardest thing on this page to find out for yourself, so the page states it. **The `azure` target
provisions an identity service for staff, and none for customers.**

- On the `auth` axis, the `azure` target uses Entra for the internal directory.
- On the `users` axis, which is for the people that the product is *for*, with sign-up, verification and
  password reset, it provisions `auth0` and nothing of its own.
- Entra ID External Identities is not an answer that this target offers.

So a staff-only service on Azure answers `users none` because there is nothing else to answer. It is not
because somebody decided that external accounts were out of scope. If this product later needs customers,
you have two choices:

- `--users auth0`, with a second vendor;
- `--target aws`, where `users cognito` is provisioned in the same account as everything else.

It is better to meet this decision here than in the middle of generating.

## What it does not decide

- **The project's name and the service's name.** Nobody else can give these two answers.
- **The deployment size: `skiff` or `liner`.** This is deliberate, for every cloud quickstart. The question
  is "who will use this product, and what happens when it is down?". That is a question about the business,
  not the stack. An internal service is not automatically a `skiff`. Payroll is internal, and an outage in
  payroll is an incident. Nobody should inherit that answer from a file.
- **Any extension.** An extension is a third-party package. This quickstart elects none.

## It is a default, never an override

Every answer above is a flag that you could have typed. A flag that you do type wins:

```sh
slipwai generate ledger --quickstart azure-staff-service --framework quarkus
```

The transcript prints every answer that the quickstart gave, and marks the answers that were yours.

## Changing it

Copy the directory and edit `quickstart.json`. Keep it beside your own repository. `--quickstart <a path>`
reads a quickstart where it is. Packages are named by version **range**, never by an exact pin. A
quickstart that named `==1.4.2` would hold everybody who used it to the afternoon that it was written. A
quickstart is a package like any other, and [`typescript-ui/`](../typescript-ui/README.md) lists the
publisher's verbs.
