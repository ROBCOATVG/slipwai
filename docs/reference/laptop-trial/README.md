# laptop-trial

A quickstart: Python, Event Modeling, SQLite in a file, and nothing else switched on. It is the kit somebody
assembles by hand on the afternoon they are *evaluating* this factory — one service, on their own machine,
with a store they can open in a viewer and a repository they expect to delete on Friday.

**It is an example and it is not a default.** Nothing installs it, nothing offers it until you do, and no
generation anywhere reaches for it. What this directory is for is to be read, copied and changed.

## Using it

```sh
slipwai quickstart install docs/reference/laptop-trial      # from this checkout
slipwai quickstart show laptop-trial                        # what it would do, before it does any of it
slipwai generate trial --quickstart laptop-trial
```

`show` first, always. It prints every answer this quickstart would give before any of them is given.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile event-modelling` | The thing being evaluated. A trial run under `standard` would tell you what the walking skeleton and the CD gate are like and nothing about the model, which is the part somebody is here to see |
| `target none` | Nothing is deployed anywhere and `make verify` is the end of the road. A trial that asked for a cloud account on its first afternoon is a trial that does not happen |
| `language python` | One language, loaded by one `slipwai install python`, with no toolchain to put on the machine first |
| `frontend none` | A browser app is a second thing to run and a second thing to read. The service is what is being read here |
| `write-model events` | The log is the truth. It is the answer the profile is for, and the one worth looking at in a store you can open |
| `persistence sqlite` | A real store, in a single file, with no container and nothing to start. The in-memory adapter would lose the log on restart, which is exactly what a reader wants to come back to; Postgres would be a Docker daemon between somebody and their first five minutes |
| `auth none` | There is nobody to authenticate. An OIDC issuer here is a container, a realm and a redirect URI to get right before anything runs |
| `users none` | Same, for the people the product would be for. There is no product yet |

**`write-model` is the one `./init` can never change afterwards.** Every other axis here is prunable — a
project that chose SQLite can drop to the in-memory adapter later, and pruning only ever subtracts. The rung
cannot be walked back, because `state` on a service that has been keeping a log does not take an adapter
away, it declares that the history on disk is no longer the truth. That is a migration somebody writes, not a
flag. This quickstart answers `events`, which is the direction that stays cheap: a log folds down into tables
whenever you decide it should, and state cannot be turned back into history it never recorded.

## What it does not decide

The project's name and the service's name, which are the two questions `generate` always asks, because they
are the only two answers nobody else can give. Nothing else is left open: this is a short list on purpose,
and a quickstart that answered fewer questions than this one would not have saved anybody the afternoon.

It elects **no extensions**. An extension is a third-party package, and the one kit nobody should be handed
somebody else's dev tooling in is the first one they ever generate.

## It is a default, never an override

Every answer above is a flag you could have typed, and a flag you do type wins:

```sh
slipwai generate trial --quickstart laptop-trial --persistence memory
```

The transcript prints every answer the quickstart gave and marks the ones that were yours, so nothing is
chosen on your behalf out of sight.

## Changing it

Copy the directory, edit `quickstart.json`, and keep it beside your own repository — `--quickstart <a path>`
reads one where it lies, so a team's own never has to be installed anywhere. The rule the keel holds it to is
that packages are named by **range**: a quickstart that pinned `==1.4.2` would hold everyone who used it to
the afternoon it was written. It is a package like any other, and
[`typescript-ui/`](../typescript-ui/README.md) states the publisher's verbs once.
