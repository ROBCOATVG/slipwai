# Bring an existing codebase

The pages before this one started from `slipwai generate`. Most code does not start that way. This page is
the other way in. You have a repository with history, tests of uneven quality, and a deploy that somebody
understands. You want the method around it, without a rewrite.

```sh
cd your-repository
slipwai adopt
```

`slipwai adopt` adds the method **beside** your code. It writes over nothing of yours. It refuses to start in
these cases:

- The directory is not a Git repository. `git init` is the first step, not a workaround.
- The tree is not clean.
- The repository already has a `project.json`. For that repository, use `slipwai migrate`.

---

## It is two halves: survey, then wrap

**The survey reads your repository and writes down what it found.** It does not write down what it would
have chosen. It records:

- which directories can be built
- the language of each directory
- how each directory is tested
- where the database is
- which forge you use
- how a release happens today

Every row of that record has a **provenance**, which says where the answer came from:

- `detected` means the survey read it from the tree.
- `confirmed` and `overridden` mean that a person gave the answer.

Only `confirmed` and `overridden` count as answered.

That difference is the whole design. If a tool silently treats its own guess as your decision, it has
adopted a repository in a way that nobody agreed to.

**The wrap** then installs these things:

- the gate, and CI for the gate
- the skills and commands
- the agent projections
- the documentation
- a `project.json` that holds the record

The keel makes all of this as one commit. This is how `replay` finds its starting point next time.

## Where am I?

At the end of an adoption, the report names a sequence of steps. The sequence takes days and uses four
tools. The report prints once, into a terminal, at the end of the longest output that the command makes. It
scrolls away. So slipwai does not remember the sequence. It **works out** the sequence each time, from marks
in the tree:

```console
$ slipwai adopt --next
  done  ./init
        installs Spec Kit and projects the skills and commands into the agent that gets them

  next  confirm what the survey found
        3 buildable directories (api, worker, admin) are recorded as candidates and none as an
        application — /ground asks which of them is one, with the code in front of it, and
        `slipwai adopt --confirm <name>` records the answer. `verify` refuses until one is confirmed

        /ground, in the agent
        9 of 14 rows of the map are nobody's word yet — it asks one at a time, shows the evidence
        and the rungs first, and records each answer with its provenance

        make verify
        the gate. Its first run records the lint and typecheck findings that are there as the
        baseline; commit baseline.json
```

Each step is read from the tree:

- Spec Kit writes `.specify/integration.json`.
- The first gate run writes the ratchet baseline.
- `/ground` moves a row's provenance off `detected`.
- A strategy is an accepted ADR (architecture decision record).

So "where was I?" is answered by a command, not by a search of your scrollback. The answer is as correct as
the tree is.

## Confirming what is an application

```sh
slipwai adopt --confirm api
slipwai adopt --confirm worker --language worker=python --purpose "worker=overnight settlement"
slipwai adopt --decline tools        # a buildable directory that is not an application
slipwai adopt --as admin=admin-ui    # confirm it under a name of your own
```

`/ground`, in the agent, does the same thing with the code in front of it, one question at a time. The gate
refuses to run until you confirm at least one candidate. A delivery method around nothing is a set of files
that nobody runs.

## The baseline, and the ratchet

Your repository has lint findings and type errors in it today. The gate does not make you fix them before
you can use it. Its first run records what is there as the **baseline**. After that, it refuses anything
*new*. Type `/verify` in the agent; it runs the gate and reads it back:

```console
> /verify
verify: baseline.json written — 412 lint findings and 86 type errors recorded as the starting line
verify: all gates passed
```

Commit the baseline. After that, the numbers can go down but cannot go up. To put a red test suite in
quarantine on purpose, tell `/verify` so when it shows you the failures: it records them with
`make ratchet-tighten`. Then the suite is not ignored without anybody knowing.

**A red test suite stops the run, and the run says so.** The baseline does not hide it. Tests that already
fail when you arrive are the thing that a brownfield adoption most often inherits without noticing, and
then builds on.

## Where the work goes

An adopted repository has no event model, and often has no clean bounded contexts. That is acceptable. It
is the reason for the **standard profile**. On the standard profile, `/chart` writes the chart with a person
present. The chart is not rendered from a model. Everything after the chart is identical: fairways, marks,
clearance, berths, captains, the telegraph and the demo stop.

There is a limit. Fairways are useful only where your code has seams. If one directory holds everything, you
have one fairway. You then get a well-gated loop for a single worker. That is still useful, but it does not
let two people work without waiting for each other. `skills/finding-seams/SKILL.md` describes how to get
from one fairway to more, one slice at a time.

## Keeping the record honest

```sh
slipwai adopt --refresh
```

This surveys the repository again and refreshes the answers that were only detected. It then **reports
where the tree now disagrees with what a person decided**. It does not write over the person's answer with a
new guess. The gate and the board follow the same rule: a calculated reading never silently replaces a
person's answer.

## Next

You are now at the point where [your first feature](first-feature.md) starts. From `/chart` onwards,
everything is the same for both ways in.

[The adopt runsheet](runsheet-adopt.md) is this page as a checklist, with every step in order.

Other pages: [start here](start-here.md) · [a second person joins](a-second-person.md) ·
[let it cruise](let-it-cruise.md) · [the vocabulary](../../GLOSSARY.md)
