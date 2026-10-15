# internal-tool

A quickstart: TypeScript on both sides, the standard profile, and **no rung and no store named at all**. It
is the kit somebody assembles by hand for the admin screen every company has a dozen of — a handful of forms,
a list, a search box, maintained by whoever drew the short straw, and nobody will ever ask what a row looked
like last March.

**It is an example and it is not a default.** Nothing installs it, nothing offers it until you do, and no
generation anywhere reaches for it. What this directory is for is to be read, copied and changed.

## Using it

```sh
slipwai quickstart list                            # this keel carries it; nothing to install
slipwai quickstart show internal-tool              # what it would do, before it does any of it
slipwai generate rates --quickstart internal-tool
```

`show` first, always. It will print four answers and two axes. That is the whole of it, and it is the point.

## What it answers, and why

| Answer | Why this one |
|---|---|
| `profile standard` | **The reason this example exists.** The walking skeleton, the executable test and the CD gate, and no model of the workflow behind them. It is the honest answer where the system is not the owner of its truth, its behaviour really is field updates, and nobody will ask what happened last month. Modelling a workflow that is a form over a table produces ceremony, not insight |
| `target existing` | It runs wherever the company's other internal tools run. Nothing is provisioned by the factory |
| `language typescript` | The same language either side of the wire, which for a tool this size is one toolchain, one formatter and one person's afternoon |
| `frontend react-vite` | The screen is the product. There is nothing here that is not the screen |
| `auth keycloak` | People who work here, signing in with the login the company already runs. The container and the group mapping are scaffolded so there is an issuer to develop against |
| `users none` | There is no public. "For people who work here" is the whole of the audience |

## Why it names no rung — and no store either

Under `event-modelling` a quickstart would answer `write-model` and `persistence`. This one answers neither,
and not by omission: **under `standard` neither axis is a question the keel asks.**

- **`write-model`** is a reading of the write side of a model, and the standard profile has no model to read.
  Its services keep current state. There is no `events`-or-`state` choice to make, so there is no rung.
- **`persistence`** is the store behind the driven port the modelled profile's write side is written against,
  and the standard profile has no such port. The tool talks to its database the ordinary way.

Both are refused outright rather than ignored if a quickstart names them: `--persistence postgres` under
`--profile standard` is a refusal with the reason in it. So the rule this example carries is sharper than
"leave out what you do not need" — **a quickstart may only answer a question its profile actually asks**, and
one that answered a question the profile does not ask would be offered in the menu, chosen, and refused at
generation.

It follows that `internal-tool` is the only one of these five with nothing that cannot be walked back.
Everywhere `write-model` is answered, that answer is the one `./init` can never change afterwards. Here there
is no such answer, because there is no such axis. That is not a smaller version of the other quickstarts; it
is a different kind of project, and this is what that difference looks like written down.

## What it does not decide

- **The project's name and the service's name.** The two answers nobody else can give.
- **Where the data lives.** Not deferred — not asked. See above.
- **Whether the standard profile was the right call.** If, a year in, somebody does start asking what a row
  looked like last March, the answer is a different profile and a service that earns the modelled rung. A
  quickstart cannot make that decision stick, and this one does not try: `--profile event-modelling` on the
  command line overrides it, and then the two axes above become questions again.
- **Any extension.** An extension is a third-party package; this quickstart elects none.

## It is a default, never an override

Every answer above is a flag you could have typed, and a flag you do type wins:

```sh
slipwai generate rates --quickstart internal-tool --auth none
```

The transcript prints every answer the quickstart gave and marks the ones that were yours.

## Changing it

Copy the directory, edit `quickstart.json`, and keep it beside your own repository — `--quickstart <a path>`
reads one where it lies. Packages are named by **range**, never by pin: one that named `==1.4.2` would hold
everyone who used it to the afternoon it was written. It is a package like any other, and
[`typescript-ui/`](../typescript-ui/README.md) states the publisher's verbs once.
