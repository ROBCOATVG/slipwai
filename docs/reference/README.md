# docs/reference

**These pages state the rules completely.** [The guide](../guide/) teaches a path. The path is five pages,
in the order a person meets them, from a green gate to a slice that somebody has accepted. The reference
pages are the layer below the guide:

- A guide page tells you what to do next.
- A reference page states one rule. It gives the reason for the rule in one sentence, and it names the one
  command that uses the rule.

No reference page is a walkthrough.

Each page describes the code as it is now, not the plan. When the code and the plan disagree, the page says
so, and the code is correct.

Two guide pages sit between the guide and these rules:

- [The workflow](../guide/the-workflow.md) lists every step from a document to an accepted capability. For
  each step, it says who does the step and where the step stops.
- [The board](../guide/the-board.md) describes every screen and control of the board, and the file that each
  control writes.

## The rules

| Page | The rule |
|---|---|
| [The chart and the mark](the-chart-and-the-mark.md) | The contracts, which are written before the split. The four kinds of mark. Each mark has one setter, is set once and never moves |
| [Clearance](clearance.md) | What lets a slice start, and why a sibling clears it when the sibling has planned, not when it has merged |
| [The deck log and the harbour log](the-logs.md) | Every kind of line in both logs, what writes each kind, and what a `parked` line needs before it is answered |
| [The fairway, the captain, the harbourmaster](fairways-and-captains.md) | One captain for each fairway, who holds what, and how merges go through one at a time |
| [The two gates](the-two-gates.md) | What runs for each increment, what runs once before `main`, and why they are two gates and not one |
| [The telegraph](the-telegraph.md) | Five positions, ten numbers, and what banking the fires does |
| [Release modes](release-modes.md) | Open, keystone, flagged and promoted; what each mode makes a merge mean; hoist and strike |
| [The rungs](the-rungs.md) | How much of its past one service keeps. This is the one answer that you cannot change back later |
| [The skiff and the liner](the-skiff-and-the-liner.md) | The two shapes of a target, and the real cost of moving between them |
| [The kinds of package](package-kinds.md) | Language, extension, target and quickstart; the import surface, and its limit of twenty names for each kind |

Two decision records are also here. Each record is about a question that was decided once. Read the record
instead of deciding the question again:

- [Install routes](install-routes.md) says which of the three ways to install the delivery material is the
  supported one.
- [Fresh native captain acceptance](native-captain-acceptance.md) records one real captain session against
  a generated fixture.

## The worked examples

There are six quickstarts. Each quickstart is a directory that holds `quickstart.json`, `README.md` and
`VERSION`. You can publish each one to a channel, the same as any other package. Each quickstart is a
*different project*, not a variation of one project, because a reader needs the example that is nearest to
their own project.

**The keel carries the six quickstarts, so you do not install them.**

- `slipwai quickstart list` names all six on any machine.
- Both interviews offer them before their first question.
- The board's Packages tab shows them as `built in`.

If you save a quickstart under one of these names, slipwai finds your quickstart and not the carried one. A
carried quickstart is a default, the same as every other thing that a quickstart gives you.

| Example | What it is |
|---|---|
| [typescript-ui](typescript-ui/) | A quickstart: TypeScript, `codegraph`, `uipro` and `ux-gates`, Event Modeling, a React browser app, Postgres |
| [laptop-trial](laptop-trial/) | Python, SQLite in a file, and nothing to install, start or log into. It is the first project that somebody reads, runs and then deletes |
| [aws-customer-product](aws-customer-product/) | Python and React on AWS, Postgres, and two Cognito pools: one pool for the public, and one for the staff who administer the public |
| [azure-staff-service](azure-staff-service/) | Java on Spring in an Azure subscription, Postgres, Entra ID, no screens and no public sign-up |
| [existing-platform-service](existing-platform-service/) | Go that joins a platform somebody else owns. Postgres and Keycloak are already there, and the factory provisions nothing |
| [internal-tool](internal-tool/) | TypeScript on both sides under the standard profile. It names no rung and no store, because it is asked for neither |

**The keel carries these quickstarts, but none of them is ever a default.** A quickstart elects extensions,
and an extension is a third-party package. A default quickstart would make this keel choose somebody's
developer tooling for every project that they generate. The only evidence for that choice would be one
person's preference. For this reason, the first row of the interview is *ask me every question*, and that
row stays selected. Carrying the quickstarts makes them easy to find. It does not choose them.

Read each quickstart on the page beside it before you agree to it. `slipwai quickstart show <name>` prints
every answer that the quickstart would give, before it gives any of them.

**The target that a quickstart answers is a package that the quickstart needs.** `aws-customer-product`
answers `target: aws`, and `azure-staff-service` answers `target: azure`. The keel carries neither target.
The interview greys out a quickstart that cannot be used. The check that does this reads the `target`
answer, as well as `languages` and `extensions`. On a machine without the cloud target installed, the
interview offers either quickstart as unavailable and names `slipwai target install <name>`. Without this
check, a person could choose the quickstart and then the generator would refuse it several questions later.
Both READMEs also say this at the top, for somebody who reads them before they install anything.
