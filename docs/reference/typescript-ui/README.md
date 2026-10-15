# typescript-ui

A quickstart: TypeScript, `codegraph`, `uipro` and `ux-gates`, with Event Modeling as the delivery
foundation, a React browser app and Postgres behind the service. It is the kit one person assembles by hand
every time they start a repository, written down once.

**It is an example and it is not a default.** Nothing installs it, nothing offers it until you do, and no
generation anywhere reaches for it. A default quickstart would be a default set of third-party extensions,
and nobody asked this keel to choose those — `codegraph`, `uipro` and `ux-gates` are packages published by
people who are not it. What this directory is for is to be read, copied and changed.

## Using it

```sh
slipwai quickstart list                               # this keel carries it; nothing to install
slipwai quickstart show typescript-ui                 # what it would do, before it does any of it
slipwai generate bookings --quickstart typescript-ui
```

`show` first, always. It prints every answer this quickstart would give and every extension it would elect,
including that `codegraph` would be allowed to **refuse a search** — a guard the person who wrote this
quickstart agreed to, which is carried so that nobody is asked the same question in every repository
(13.4). If you would not have agreed to that, copy this file, take the `guards` line out, and use yours.

Every answer it gives is a flag you could have typed, and a flag you do type wins:

```sh
slipwai generate bookings --quickstart typescript-ui --profile standard
```

## Changing it

Copy the directory, edit `quickstart.json`, and keep it beside your own repository — `--quickstart
<a path>` reads one where it lies, so a team's own never has to be installed anywhere. The rule the keel
holds it to is that packages are named by **range**: a quickstart that pinned `==1.4.2` would hold
everyone who used it to the afternoon it was written.

## Publishing it

It is a package, so the publisher's verbs are the ones you already know:

```sh
slipwai package check docs/reference/typescript-ui
slipwai package release docs/reference/typescript-ui
slipwai package register docs/reference/typescript-ui --channel <a channel checkout>
```

Registered in a channel, `slipwai search --kind quickstart` lists it beside the languages, and
`slipwai quickstart install typescript-ui` fetches it.
