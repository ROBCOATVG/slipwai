# existing-platform-service

A quickstart: Go, Postgres, Keycloak, and a target that provisions nothing. It is the kit somebody assembles
by hand for the second, fifth or fortieth service on a platform that was there before this repository was —
somebody else owns the cluster, somebody else owns the database, somebody else owns the login, and the only
job here is to fit in.

**It is an example and it is not a default.** Nothing installs it, nothing offers it until you do, and no
generation anywhere reaches for it. What this directory is for is to be read, copied and changed.

## Using it

```sh
slipwai quickstart list                                           # this keel carries it; nothing to install
slipwai quickstart show existing-platform-service                 # what it would do, before it does any of it
slipwai generate payments --quickstart existing-platform-service
```

`show` first, always. Unlike the two cloud quickstarts beside it, this one needs no target installed: nothing
has to be fetched before it can be carried out.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | A service joining a platform is a service other teams will integrate with, and the log is the contract they can read without asking this one. That is what keeps a slice a slice when the people writing the next one do not sit here |
| `target existing` | **The point of this quickstart.** This project deploys to infrastructure it does not own: whatever runs it is described in `docs/deployment.md` and provisioned by nobody here. `make verify` is the gate and the factory deploys nothing. The alternative — naming a cloud and generating OpenTofu for a cluster that already exists and is already owned — would produce a repository that fights the platform team on its first pull request |
| `language go` | One static binary in a container, which is the shape a platform that already exists almost always wants put into it |
| `frontend none` | The screens, if there are any, belong to something already on the platform. This service answers HTTP |
| `write-model events` | The log is the truth. See below — it is the one answer here that cannot be walked back |
| `persistence postgres` | The database the platform already runs. Under `existing` nothing is provisioned, so this is a connection string the platform team hands over, not a server anybody stands up |
| `auth keycloak` | The login the platform already has. Self-hosted OIDC, with the container and the group mapping scaffolded so `make verify` has an issuer of its own to run against — the real one is wherever the platform keeps it. `cognito` and `entra` are not offered under `existing`, because they are provisioned by a target that is provisioning nothing here |
| `users none` | The public, if this product has one, signs up somewhere that already exists. A service joining a platform does not bring its own sign-up |

**`write-model` is the one `./init` can never change afterwards.** The other axes are prunable — a project
can drop Postgres for the in-memory adapter, and pruning only ever subtracts — but the rung cannot be walked
back. `state` on a service that has been keeping a log does not take an adapter away, it declares the history
on disk is no longer the truth, which is a migration somebody writes rather than a flag. On a platform where
other teams will come to read this service's log, that is a decision worth having made correctly once.

## What it does not decide

- **The project's name and the service's name.** The two answers nobody else can give.
- **Anything about the platform itself.** There is no deployment size question here, because `existing`
  provisions nothing to size. What the service needs from whoever owns the runtime goes in
  `docs/deployment.md`, which is generated for somebody to fill in rather than for this quickstart to guess.
- **Any extension.** An extension is a third-party package; a platform team's own tooling is theirs to
  elect, and this quickstart elects none.

## It is a default, never an override

Every answer above is a flag you could have typed, and a flag you do type wins:

```sh
slipwai generate payments --quickstart existing-platform-service --auth none
```

The transcript prints every answer the quickstart gave and marks the ones that were yours.

## Changing it

This is the one most likely to become a team's own: a platform has one login, one database and one shape of
service, and those are three answers worth settling once for everybody who joins it. Copy the directory, edit
`quickstart.json`, and keep it beside the platform's own repository — `--quickstart <a path>` reads one where
it lies, so it never has to be installed anywhere. Packages are named by **range**, never by pin: one that
named `==1.4.2` would hold everyone who used it to the afternoon it was written. It is a package like any
other, and [`typescript-ui/`](../typescript-ui/README.md) states the publisher's verbs once.
