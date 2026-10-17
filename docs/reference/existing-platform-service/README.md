# existing-platform-service

This is a quickstart. It gives Go, Postgres, Keycloak, and a target that provisions nothing. It is the kit
that somebody puts together by hand for the second, fifth or fortieth service on a platform that existed
before this repository. Somebody else owns the cluster. Somebody else owns the database. Somebody else owns
the login. The only job here is to fit in.

**It is an example, and it is not a default.** The keel carries it, so the interview lists it. But the
interview never selects it, and no generation uses it unless you ask. This directory is here for you to
read, copy and change.

## Using it

```sh
slipwai quickstart list                                           # this keel carries it; nothing to install
slipwai quickstart show existing-platform-service                 # what it would do, before it does any of it
slipwai generate payments --quickstart existing-platform-service
```

Always run `show` first. This quickstart is different from the two cloud quickstarts beside it: it needs no
target installed. Nothing has to be fetched before you can use it.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | Other teams will integrate with a service that joins a platform. The log is the contract that they can read without asking this service. That keeps a slice a slice when the people who write the next slice do not sit here |
| `target existing` | **This is the point of the quickstart.** The project deploys to infrastructure that it does not own. `docs/deployment.md` describes what runs the service, and nobody here provisions it. `make verify` is the gate, and the factory deploys nothing. The alternative is to name a cloud and generate OpenTofu for a cluster that already exists and has an owner. That repository would fight the platform team on its first pull request |
| `language go` | One static binary in a container. An existing platform almost always wants this shape |
| `frontend none` | If there are screens, they belong to something that is already on the platform. This service answers HTTP |
| `write-model events` | The log is the truth. See below: this is the one answer here that you cannot change back |
| `persistence postgres` | The database that the platform already runs. Under `existing`, nothing is provisioned. So this is a connection string that the platform team gives you, not a server that anybody starts |
| `auth keycloak` | The login that the platform already has: self-hosted OIDC. The container and the group mapping are scaffolded, so `make verify` has its own issuer to run against. The real issuer is wherever the platform keeps it. `cognito` and `entra` are not offered under `existing`, because a target provisions them, and this target provisions nothing |
| `users none` | If this product has a public, the public signs up somewhere that already exists. A service that joins a platform does not bring its own sign-up |

**`write-model` is the one answer that `./init` can never change later.** You can prune the other axes. For
example, a project can drop Postgres for the in-memory adapter, and pruning only removes things. But you
cannot change the rung back. On a service that has kept a log, changing to `state` does not only remove an
adapter. It declares that the history on disk is no longer the truth. That needs a migration that somebody
writes. It is not a flag. On a platform where other teams will read this service's log, it is important to
make this decision correctly once.

## What it does not decide

- **The project's name and the service's name.** Nobody else can give these two answers.
- **Anything about the platform itself.** There is no deployment size question here, because `existing`
  provisions nothing to size. Write what the service needs from the owner of the runtime in
  `docs/deployment.md`. The keel generates that file for somebody to fill in. This quickstart does not guess
  its contents.
- **Any extension.** An extension is a third-party package. A platform team elects its own tooling, and
  this quickstart elects none.

## It is a default, never an override

Every answer above is a flag that you could have typed. A flag that you do type wins:

```sh
slipwai generate payments --quickstart existing-platform-service --auth none
```

The transcript prints every answer that the quickstart gave, and marks the answers that were yours.

## Changing it

This is the quickstart that is most likely to become a team's own. A platform has one login, one database
and one shape of service. It is worth settling those three answers once, for everybody who joins the
platform.

Copy the directory and edit `quickstart.json`. Keep it beside the platform's own repository.
`--quickstart <a path>` reads a quickstart where it is, so it never needs to be installed anywhere. Packages
are named by version **range**, never by an exact pin. A quickstart that named `==1.4.2` would hold
everybody who used it to the afternoon that it was written. A quickstart is a package like any other, and
[`typescript-ui/`](../typescript-ui/README.md) lists the publisher's verbs.
