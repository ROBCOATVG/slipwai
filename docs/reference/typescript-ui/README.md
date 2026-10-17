# typescript-ui

This is a quickstart. It gives TypeScript, `codegraph`, `uipro` and `ux-gates`, with Event Modeling as the
delivery foundation, a React browser app, and Postgres behind the service. It is the kit that one person
puts together by hand each time they start a repository, written down once.

**It is an example, and it is not a default.** The keel carries it, so the interview lists it. But the
interview never selects it, and no generation uses it unless you ask. A default quickstart would be a
default set of third-party extensions, and nobody asked this keel to choose those. `codegraph`, `uipro` and
`ux-gates` are packages that other people publish. This directory is here for you to read, copy and change.

## Using it

```sh
slipwai quickstart list                               # this keel carries it; nothing to install
slipwai quickstart show typescript-ui                 # what it would do, before it does any of it
slipwai generate bookings --quickstart typescript-ui
```

Always run `show` first. It prints every answer that this quickstart would give, and every extension that
it would elect. This includes the fact that `codegraph` would be allowed to **refuse a search**. That is a
guard. The person who wrote this quickstart agreed to the guard. The quickstart carries the guard so that
nobody is asked the same question in every repository (13.4). If you would not agree to the guard, copy
this file, remove the `guards` line, and use your copy.

Every answer that the quickstart gives is a flag that you could have typed. A flag that you do type wins:

```sh
slipwai generate bookings --quickstart typescript-ui --profile standard
```

## Changing it

Copy the directory and edit `quickstart.json`. Keep it beside your own repository. `--quickstart <a path>`
reads a quickstart where it is, so a team's own quickstart never needs to be installed anywhere.

The keel holds a quickstart to one rule: it names packages by version **range**. A quickstart that pinned
`==1.4.2` would hold everybody who used it to the afternoon that it was written.

## Publishing it

A quickstart is a package, so you publish it with the same verbs as any package:

```sh
slipwai package check docs/reference/typescript-ui
slipwai package release docs/reference/typescript-ui
slipwai package register docs/reference/typescript-ui --channel <a channel checkout>
```

After it is registered in a channel, `slipwai search --kind quickstart` lists it beside the languages, and
`slipwai quickstart install typescript-ui` fetches it.
