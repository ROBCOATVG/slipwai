# internal-tool

This is a quickstart. It gives TypeScript on both sides, the standard profile, and **no rung and no store at
all**. It is the kit that somebody puts together by hand for the kind of admin screen that every company has
a dozen of: a few forms, a list and a search box. Whoever was unlucky maintains it, and nobody will ever ask
what a row looked like last March.

**It is an example, and it is not a default.** The keel carries it, so the interview lists it. But the
interview never selects it, and no generation uses it unless you ask. This directory is here for you to
read, copy and change.

## Using it

```sh
slipwai quickstart list                            # this keel carries it; nothing to install
slipwai quickstart show internal-tool              # what it would do, before it does any of it
slipwai generate rates --quickstart internal-tool
```

Always run `show` first. It prints four answers and two axes. That is all of it, and that is the point.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile standard` | **This is the reason that this example exists.** The profile gives the walking skeleton, the executable test and the CD gate, with no model of the workflow behind them. It is the honest answer when the system does not own its truth, its behaviour really is field updates, and nobody will ask what happened last month. If you model a workflow that is only a form over a table, you get ceremony, not insight |
| `target existing` | It runs wherever the company's other internal tools run. The factory provisions nothing |
| `language typescript` | The same language on both sides of the wire. For a tool this size, that means one toolchain, one formatter and one person's afternoon |
| `frontend react-vite` | The screen is the product. Everything here is the screen |
| `auth keycloak` | People who work here sign in with the login that the company already runs. The container and the group mapping are scaffolded, so there is an issuer to develop against |
| `users none` | There is no public. "People who work here" is the whole audience |

## Why it names no rung, and no store either

Under `event-modelling`, a quickstart would answer `write-model` and `persistence`. This quickstart answers
neither. That is not an omission: **under `standard`, the keel does not ask either question.**

- **`write-model`** describes the write side of a model. The standard profile has no model to describe. Its
  services keep the current state. There is no choice between `events` and `state`, so there is no rung.
- **`persistence`** is the store behind the driven port that the modelled profile's write side uses. The
  standard profile has no such port. The tool talks to its database in the ordinary way.

If a quickstart names either axis under `standard`, the keel refuses it. It does not ignore it. For example,
`--persistence postgres` under `--profile standard` is refused, and the refusal gives the reason.

So the rule that this example carries is stricter than "leave out what you do not need". **A quickstart can
only answer a question that its profile asks.** If a quickstart answered a question that its profile does
not ask, the menu would offer it, a person would choose it, and generation would then refuse it.

So `internal-tool` is the only one of the six quickstarts that cannot answer `write-model` at all. Wherever
a quickstart answers `write-model`, that answer is the one that `./init` can never change later. Here there
is no such answer, because there is no such axis. This is not a smaller version of the other quickstarts. It
is a different kind of project, and this page shows what that difference looks like.

## What it does not decide

- **The project's name and the service's name.** Nobody else can give these two answers.
- **Where the data lives.** This is not deferred. Nobody asks it. See above.
- **Whether the standard profile was the correct choice.** If, after a year, somebody does start to ask
  what a row looked like last March, the answer is a different profile, and a service that earns the
  modelled rung. A quickstart cannot keep that decision fixed, and this quickstart does not try. Add
  `--profile event-modelling` on the command line to override it. The two axes above then become questions
  again.
- **Any extension.** An extension is a third-party package. This quickstart elects none.

## It is a default, never an override

Every answer above is a flag that you could have typed. A flag that you do type wins:

```sh
slipwai generate rates --quickstart internal-tool --auth none
```

The transcript prints every answer that the quickstart gave, and marks the answers that were yours.

## Changing it

Copy the directory and edit `quickstart.json`. Keep it beside your own repository. `--quickstart <a path>`
reads a quickstart where it is. Packages are named by version **range**, never by an exact pin. A
quickstart that named `==1.4.2` would hold everybody who used it to the afternoon that it was written. A
quickstart is a package like any other, and [`typescript-ui/`](../typescript-ui/README.md) lists the
publisher's verbs.
