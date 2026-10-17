# docs/reference

**The rules, stated completely.** [The guide](../guide/) teaches a path: five pages in the order a person
meets them, from a green gate to a slice somebody has accepted. These pages are the layer below it. A guide
page tells you what to do next; a reference page states one rule, says why it is there in a sentence, and
names the one command that exercises it. Nothing here is a walkthrough.

Every page is written against the code as it stands, not against the plan. Where the two disagree, the page
says so and the code wins.

Two guide pages sit between the guide and these rules. [The workflow](../guide/the-workflow.md) lists every
step from a document to an accepted capability, with who does it and where it stops.
[The board](../guide/the-board.md) describes every screen and control of the board, and the file each control
writes.

## The rules

| Page | The rule |
|---|---|
| [The chart and the mark](the-chart-and-the-mark.md) | The contracts, written before the split. The four kinds of mark, one setter each, set once and never moved |
| [Clearance](clearance.md) | What lets a slice start — and why a sibling clears it by having planned, not by having merged |
| [The deck log and the harbour log](the-logs.md) | Every kind in both logs, what writes each, and what a `parked` owes |
| [The fairway, the captain, the harbourmaster](fairways-and-captains.md) | One captain per fairway, who holds what, and how the merge is serialised |
| [The two gates](the-two-gates.md) | What runs per increment, what runs once before `main`, and why they are not one gate |
| [The telegraph](the-telegraph.md) | Five positions, nine numbers, and what banking the fires does |
| [Release modes](release-modes.md) | Open, keystone, flagged, promoted; what each makes a merge mean; hoist and strike |
| [The rungs](the-rungs.md) | How much of its past one service keeps — the one answer that cannot be walked back |
| [The skiff and the liner](the-skiff-and-the-liner.md) | A target's two shapes, and what converging between them actually costs |
| [The kinds of package](package-kinds.md) | Language, extension, target, quickstart; the import surface and its per-kind ceiling of twenty |

Two decision records live here too, each about a thing that was settled once and is read rather than
rediscovered: [install routes](install-routes.md), which of the three ways to install the delivery material
is the supported one; and [fresh native captain acceptance](native-captain-acceptance.md), the record of a
real captain session against a generated fixture.

## The worked examples

Six quickstarts, each a directory of `quickstart.json`, `README.md` and `VERSION`, publishable to a channel
like any other package. They are picked to be *different projects* rather than variations on one, because
what a reader needs from an example is the one nearest their own.

**The keel carries them**, so there is nothing to install: `slipwai quickstart list` names all six on any
machine, both interviews offer them before their first question, and the board's Packages tab shows them as
`built in`. A quickstart you save under one of these names is the one that is found — carried is a default,
the same as every other thing a quickstart gives you.

| Example | What it is |
|---|---|
| [typescript-ui](typescript-ui/) | A quickstart: TypeScript, `codegraph`, `uipro` and `ux-gates`, Event Modeling, a React browser app, Postgres |
| [laptop-trial](laptop-trial/) | Python, SQLite in a file, nothing to install, start or log into — the first project somebody reads, runs and throws away |
| [aws-customer-product](aws-customer-product/) | Python and React on AWS, Postgres, and two Cognito pools — the public in one, the staff who administer them in the other |
| [azure-staff-service](azure-staff-service/) | Java on Spring in an Azure subscription, Postgres, Entra ID, no screens and no public sign-up |
| [existing-platform-service](existing-platform-service/) | Go joining a platform somebody else owns: Postgres and Keycloak that are already there, and a factory that provisions nothing |
| [internal-tool](internal-tool/) | TypeScript on both sides under the standard profile — the one that names no rung and no store, because it is asked for neither |

**Carried, and still never a default.** A quickstart elects extensions, and an extension is a third-party
package. A default quickstart would be this keel choosing somebody's dev tooling for them in every project
they ever generate, on no evidence beyond one person's preference. So the interview's first row is *ask me
every question* and it stays the selected one: carrying these makes them findable, not chosen. Each is read
before it is agreed to, on the page beside it, and `slipwai quickstart show <name>` prints every answer it
would give before any of them is given.

**The target a quickstart answers is a package it needs.** `aws-customer-product` and
`azure-staff-service` answer `target: aws` and `target: azure`, and neither is carried by the keel. The
check that greys an unusable quickstart out of the interview reads that answer along with `languages` and
`extensions`, so on a machine without the cloud installed either is offered as unavailable, naming
`slipwai target install <name>` — rather than being chosen and refused by the generator several questions
later. Both READMEs say it at the top as well, for somebody reading before they install anything.
