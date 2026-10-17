# Release modes

**A release mode says how dark a merge is. The state of the product decides the mode.** A merge is dark
when real actors cannot see what it changed. There are four modes.

A person does not set the mode for each slice. The mode follows from one fact about the product, which is
recorded once. A setting that somebody must remember to change is wrong each time they forget. A fact about
the state of the product gets corrected, because everybody can see when it is untrue.

The fact is `state` in `project.json`:

```
slipway      no production, or one only the team sees   → open
sea trials   a production with known pilot actors       → keystone
in service   real actors use what trunk deploys         → flagged
```

The three states are spelled `slipway`, `sea-trials` and `in-service`. The default is `slipway`.

---

## The four modes

| Mode | What a merge means | What the factory does |
|---|---|---|
| **open** | Visible at once — trunk is the demo | No flags, no reader, `check-flags` has nothing to hold. The gate is `make verify` plus the hand's verdict |
| **keystone** | Dark by omission — every slice lands except the entry point, which is the capability's last slice's last task | The chart names the keystone per capability. Intermediate slices are demoed at the `http` or `cli` rung. No flag in domain code, and no two-path tests |
| **flagged** | Dark behind a key seeded off, which only a person hoists | Version 1's behaviour, with the three changes below |
| **promoted** | Visible on trunk and in preview; production takes only what passes the promotion gate | Flags are optional |

**No state gives the `promoted` mode.** `promoted` is a fact about how a team deploys, not about the state of
the product. So a project that wants `promoted` declares it, and keeps the declaration. If `project.json`
declares any *other* mode, the keel ignores it and uses the mode that the state gives. A declared mode that
disagreed with the state would bring back the version 1 setting.

**Only a person moves the product to a new state, and the move needs an ADR** (architecture decision
record). The reason is that the move changes what every later merge means:

- Move to sea trials when the first pilot actor appears.
- Move to in service when there are actors that a change must not surprise.

A run never changes the state. `/cruise` never changes it.

Only `flagged` generates a flag reader. Most of the value of the modes comes from this. On the slipway there
is no reader to call, no second test path, no key to hoist before a demo, and no park for a slice that
nothing holds back.

---

## Where it is recorded today

The field is `releaseMode` in `project.json`, beside `state`.

**A crossing writes both fields.** `slipwai migrate` reads the repository's own flag history:

- It records `releaseMode` as `open` when the project's target is `none`, and as `flagged` otherwise.
- It records `state` as `in-service` when any flag in that file's history was ever seeded on, and as
  `slipway` when no flag was.
- It starts the hoist clock of every existing flag on the day of the crossing. Rule 5 below then has a date
  to measure from.

If `project.json` had a conflict, the crossing says so, and it names the two lines to write by hand.

**An adopted repository has a `release-mode` row on its convergence map.** The row climbs from
`unrecorded` to `recorded` to `confirmed`. A crossing records the row as evidence. Only a person moves it to
`confirmed`. A resurvey never moves it back down, because the build files cannot show a release choice that
actors can see.

`slipwai generate` does not write either field yet. So a newly generated project has no recorded state, and
the rule above has nothing to read. The module has the rule, but generation does not use it yet.

---

## The three changes to flagged

1. **There is one flag for each fairway capability, and the chart names it.** When the flag is named at the
   split, no slice has to stop to name it.
2. **Flags are only at the entry wiring.** A release flag is one `if` at the route or the menu. It is never
   inside a decider or a use case. The two-path test becomes the route's test.
3. **Each environment has a default.** The flag reader resolves to on in local development and in preview.
   The production seed is off. A demo never needs a hoist.

---

## Hoist and strike

To **hoist** a flag is to turn it on for real actors. To **strike** a flag is to remove it after it has been
on everywhere for long enough. **Only a person hoists.** The harbourmaster records both in the
[harbour log](the-logs.md): `flag-hoisted`, with where, and `flag-struck`.

Accepting a demo and hoisting a flag are two different claims. Neither claim comes from the other:

- Accepting says that the capability is correct.
- Hoisting says that the business wants the capability live. That can be in another quarter, or never.

A capability can stay accepted and dark for as long as the business wants. Under `open`, a capability has no
flag at all, and it still has a demo.

---

## What `check-flags` holds

```
python3 scripts/check-flags.py
```

`check-flags` holds five rules. Without each rule, something would fail without anybody noticing:

1. **Declared and never read.** A key in `infra/service/flags.auto.tfvars` that no code asks for is a switch
   that is connected to nothing. Changing it does nothing, and nobody finds out until they change it.
2. **Read and never declared.** When code asks for a key that the infrastructure does not declare, the key
   reads as *off* for ever. The capability stays dark, and no change to any flag can reach it.
3. **Seeded with any value except `off`.** A new flag that is seeded on is a release at merge time. A flag
   exists to prevent exactly that.
4. **Read around the reader.** If code names `FLAG_<KEY>` at the point of use, three things are lost: the
   single spelling, the transform, and the seam through which a test drives both paths. Ask the reader by
   key.
5. **Hoisted everywhere and never struck.** A flag records its hoist date in a trailing comment. After
   thirty days on everywhere, the flag is overdue. A flag that is never struck costs three things: a code
   path that nobody uses, a branch that every later change must carry, and a test matrix that is twice the
   size it needs to be. The careen carries the task that strikes the flag.

**The kinds of flag are kept apart.** Operations flags (kill switches), permission flags and experiment
flags belong to the service. Each is declared with `kind:` in its own comment. They are exempt from rule 5,
because they are meant to stay for ever. A flag without a written kind is read as a release flag. A release
flag is the only kind with a clock.

---

Next: [the two gates](the-two-gates.md) · [the skiff and the liner](the-skiff-and-the-liner.md), the other
thing the product state decides · [let it cruise](../guide/let-it-cruise.md)
