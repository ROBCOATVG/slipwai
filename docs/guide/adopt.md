# Bring an existing codebase

Everything so far started from `slipwai generate`. Most code does not. This page is the other door: you
have a repository with history, tests of uneven quality and a deploy somebody understands, and you want the
method around it without a rewrite.

```sh
cd your-repository
slipwai adopt
```

It adds the method **beside** your code. Nothing of yours is written over. The one thing it will not do is
start: a directory that is not a Git repository is refused — `git init` is day zero, not a workaround — as
is an unclean tree, and a repository that already has a `project.json` (that one is `slipwai migrate`).

---

## It is two halves: survey, then wrap

**The survey reads your repository and writes down what it found**, not what it would have chosen: which
directories are buildable, what language each is in, how it is tested, where the database lives, which
forge you use, how a release happens today. Every row of that record carries its **provenance** —
`detected` is the tree's reading, `confirmed` and `overridden` are a person's word, and only the last two
count as answered.

That distinction is the whole design. A tool that silently treats its own guess as your decision is a tool
that has adopted a repository nobody agreed to.

**The wrap** then installs the gate, CI for it, the skills and commands, the agent projections, the
documentation and a `project.json` holding the record — as one commit by the keel, which is how `replay`
finds its base next time.

## Where am I?

The report at the end of an adoption names a sequence that spans days and four tools, and it is printed
once, into a terminal, at the end of the longest output the command produces. It scrolls away. So the
sequence is not remembered — it is **derived**, every time, from marks in the tree:

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

Every step is read off the tree: Spec Kit writes `.specify/integration.json`, the first gate run writes the
ratchet baseline, `/ground` moves a row's provenance off `detected`, a strategy is an accepted ADR. So the
answer to "where was I" is a command rather than a scrollback search, and it is as right as the tree is.

## Confirming what is an application

```sh
slipwai adopt --confirm api
slipwai adopt --confirm worker --language worker=python --purpose "worker=overnight settlement"
slipwai adopt --decline tools        # a buildable directory that is not an application
slipwai adopt --as admin=admin-ui    # confirm it under a name of your own
```

`/ground`, in the agent, is the same thing with the code in front of it and one question at a time. The
gate refuses until at least one candidate is confirmed, because a delivery method wrapped around nothing is
a set of files nobody runs.

## The baseline, and the ratchet

Your repository has lint findings and type errors in it today. The gate does not demand you fix them before
you can use it — its first run records what is there as the **baseline** and then refuses anything *new*:

```console
$ make verify
verify: baseline.json written — 412 lint findings and 86 type errors recorded as the starting line
verify: all gates passed
```

Commit it. From then on the number may fall and may not rise, and `make ratchet-tighten` is how you
deliberately quarantine a red test suite rather than discovering it is being ignored.

**A red test suite stops the run and says so.** It is not baselined away silently, because tests that were
already failing when you arrived are the single most common thing a brownfield adoption quietly inherits
and then builds on.

## Where the work goes

An adopted repository has no event model and often no clean bounded contexts. That is fine, and it is why
the **standard profile** exists — the chart is written by `/chart` with a person present rather than
rendered from a model, and everything downstream of it is identical. Fairways, marks, clearance, berths,
captains, the telegraph, the demo stop: all the same.

The honest limit: fairways are only worth drawing where your code has seams. If one directory holds
everything, you have one fairway, and this becomes a well-gated single-worker loop — which is still worth
having, but it is not two people not waiting on each other. `skills/finding-seams/SKILL.md` is about
getting from the first state to the second, a slice at a time.

## Keeping the record honest

```sh
slipwai adopt --refresh
```

Surveys again, refreshes what was only detected, and **reports what now disagrees with what a person
decided** — rather than overwriting their answer with a fresh guess. That is the same rule as the gate and
the board: a derived reading never silently replaces somebody's word.

## Next

You are now where [your first feature](first-feature.md) begins. Everything from `/chart` onwards is the
same on both doors.

[The adopt runsheet](runsheet-adopt.md) is this page as a checklist, every step in order.

Other pages: [start here](start-here.md) · [a second person joins](a-second-person.md) ·
[let it cruise](let-it-cruise.md) · [the vocabulary](../../GLOSSARY.md)
