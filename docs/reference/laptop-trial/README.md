# laptop-trial

This is a quickstart. It gives Python, Event Modeling and SQLite in a file, with nothing else switched on.
It is the kit that somebody puts together by hand on the afternoon that they *evaluate* this factory: one
service, on their own machine, with a store that they can open in a viewer, and a repository that they
expect to delete on Friday.

**It is an example, and it is not a default.** The keel carries it, so the interview lists it. But the
interview never selects it, and no generation uses it unless you ask. This directory is here for you to
read, copy and change.

## Using it

```sh
slipwai quickstart list                           # this keel carries it; nothing to install
slipwai quickstart show laptop-trial              # what it would do, before it does any of it
slipwai generate trial --quickstart laptop-trial
```

Always run `show` first. It prints every answer that this quickstart would give, before it gives any of
them.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | Event Modeling is the thing that the trial evaluates. A trial under `standard` would show you the walking skeleton and the CD gate, and nothing about the model. The model is the part that somebody is here to see |
| `target none` | Nothing is deployed anywhere, and `make verify` is the last step. If a trial asked for a cloud account on its first afternoon, the trial would not happen |
| `language python` | One language, loaded by one `slipwai install python`, with no toolchain to install on the machine first |
| `frontend none` | A browser app is a second thing to run and a second thing to read. The trial reads the service |
| `write-model events` | The log is the truth. The profile exists for this answer, and it is the answer worth looking at in a store that you can open |
| `persistence sqlite` | A real store, in a single file, with no container and nothing to start. The in-memory adapter would lose the log on restart, and a reader wants to come back to the log. Postgres would put a Docker daemon between somebody and their first five minutes |
| `auth none` | There is nobody to authenticate. An OIDC issuer here would be a container, a realm and a redirect URI to get right before anything runs |
| `users none` | The same reason, for the people that the product would be for. There is no product yet |

**`write-model` is the one answer that `./init` can never change later.** You can prune every other axis
here. For example, a project that chose SQLite can drop to the in-memory adapter later, and pruning only
removes things. You cannot change the rung back. On a service that has kept a log, changing to `state` does
not only remove an adapter. It declares that the history on disk is no longer the truth. That needs a
migration that somebody writes. It is not a flag.

This quickstart answers `events`. That is the direction that stays cheap. You can fold a log down into
tables whenever you decide to. You cannot turn state back into history that it never recorded.

## What it does not decide

The quickstart does not decide the project's name or the service's name. `generate` always asks these two
questions, because nobody else can answer them. The quickstart leaves nothing else open. The list is short
on purpose. A quickstart that answered fewer questions than this one would not save anybody the afternoon.

It elects **no extensions**. An extension is a third-party package. The first project that somebody ever
generates is the one kit where nobody should get another person's developer tooling.

## It is a default, never an override

Every answer above is a flag that you could have typed. A flag that you do type wins:

```sh
slipwai generate trial --quickstart laptop-trial --persistence memory
```

The transcript prints every answer that the quickstart gave, and marks the answers that were yours. So
nothing is chosen for you without you seeing it.

## Changing it

Copy the directory and edit `quickstart.json`. Keep it beside your own repository. `--quickstart <a path>`
reads a quickstart where it is, so a team's own quickstart never needs to be installed anywhere.

The keel holds a quickstart to one rule: it names packages by version **range**. A quickstart that pinned
`==1.4.2` would hold everybody who used it to the afternoon that it was written. A quickstart is a package
like any other, and [`typescript-ui/`](../typescript-ui/README.md) lists the publisher's verbs.
