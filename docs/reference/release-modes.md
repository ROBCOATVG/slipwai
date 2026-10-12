# Release modes

**How dark a merge is, decided by where the product is.** There are four modes, and the mode is not a knob a
person turns per slice — it is one fact about the product, recorded once, that the mode follows from. A
setting somebody has to remember to turn is wrong whenever they forget; a fact about where the product is
gets corrected because it is visibly untrue.

The fact is `state` in `project.json`:

```
slipway      no production, or one only the team sees   → open
sea trials   a production with known pilot actors       → keystone
in service   real actors use what trunk deploys         → flagged
```

The three states are spelled `slipway`, `sea-trials` and `in-service`, and `slipway` is the default.

---

## The four modes

| Mode | What a merge means | What the factory does |
|---|---|---|
| **open** | Visible at once — trunk is the demo | No flags, no reader, `check-flags` has nothing to hold. The gate is `make verify` plus the hand's verdict |
| **keystone** | Dark by omission — every slice lands except the entry point, which is the capability's last slice's last task | The chart names the keystone per capability. Intermediate slices are demoed at the `http` or `cli` rung. No flag in domain code, and no two-path tests |
| **flagged** | Dark behind a key seeded off, which only a person hoists | Version 1's behaviour, with the three changes below |
| **promoted** | Visible on trunk and in preview; production takes only what passes the promotion gate | Flags are optional |

**`promoted` is the one mode no state implies.** It is a fact about how a team deploys rather than about
where the product is, so a project that wants it declares it and keeps declaring it. Any *other* mode
declared in `project.json` is ignored in favour of the state — a mode that disagreed with where the product
is would be the version 1 setting back again.

**Moving the product is a person's decision and an ADR**, because it changes what every later merge means:
to sea trials when the first pilot actor appears, to in service when there are actors it cannot surprise.
A run never changes it, and `/cruise` never changes it.

Only `flagged` generates a flag reader at all. That is most of what the modes buy: on the slipway there is
no reader to call, no second test path, no key to hoist before a demo, and no park for a slice with nothing
holding it back.

---

## Where it is recorded today

The field is `releaseMode` in `project.json`, beside `state`.

**A crossing writes both.** `slipwai migrate` reads the repository's own flag history: it records
`releaseMode` as `open` where the project's target is `none` and `flagged` otherwise, and `state` as
`in-service` where any flag was ever seeded on in that file's history and `slipway` where none was. It also
starts every existing flag's hoist clock on the crossing day, so rule 5 below has a date to measure from.
Where `project.json` conflicted, the crossing says so and names the two lines to write by hand.

**An adopted repository carries a `release-mode` row on its convergence map**, which climbs `unrecorded` →
`recorded` → `confirmed`. A crossing records it as evidence; only a person moves it to `confirmed`, and a
resurvey never knocks it back down — an actor-visible release choice cannot be inferred from build files.

`slipwai generate` writes neither field yet, so a freshly generated project has no recorded state and the
derivation above has nothing to derive from. The rule is the module's; the wiring into generation is not
there.

---

## The three changes to flagged

1. **One flag per fairway capability, named on the chart.** Naming the flag at the split removes a stop from
   every slice.
2. **Flags live at the entry wiring only.** A release flag is one `if` at the route or the menu, never
   inside a decider or a use case. The two-path test becomes the route's test.
3. **Environment defaults.** The flag reader resolves to on in local development and in preview; the
   production seed is off. A demo never needs a hoist.

---

## Hoist and strike

To **hoist** a flag is to turn it on for real actors. To **strike** it is to remove it after it has been on
everywhere for long enough. **Only a person hoists.** The harbourmaster records both, as `flag-hoisted` with
where, and `flag-struck`, in the [harbour log](the-logs.md).

Accepting a demo and hoisting a flag are two different claims and neither is derived from the other.
Accepting says the capability is right; hoisting says the business wants it live, which may be another
quarter or never. A capability may sit accepted and dark for as long as the business wants, and under `open`
it has no flag at all and still has a demo.

---

## What `check-flags` holds

```
python3 scripts/check-flags.py
```

Five rules, each because its absence fails quietly:

1. **Declared and never read.** A key in `infra/service/flags.auto.tfvars` that no code asks for is a switch
   wired to nothing. Flipping it does nothing and nobody finds out until they flip it.
2. **Read and never declared.** Code asking for a key the infrastructure does not declare reads as *off* for
   ever: the capability is dark and no amount of flipping will reach it.
3. **Seeded anything but `off`.** A new flag seeded on is a release that happened at merge time, which is
   the one thing a flag exists to prevent.
4. **Read round the reader.** Naming `FLAG_<KEY>` at the point of use loses the single spelling, the
   transform, and the seam a test drives both paths through. Ask the reader by key.
5. **Hoisted everywhere and never struck.** A flag records its hoist date in a trailing comment, and after
   thirty days on everywhere it is overdue. A flag that is never struck is a code path kept alive for
   nobody, a branch every later change has to carry, and a test matrix twice the size it needs to be. The
   careen carries the task that strikes it.

**Kinds of flag are kept apart.** Operations flags (kill switches), permission flags and experiment flags
belong to the service, are declared with `kind:` in their own comment, and are exempt from rule 5 — they are
meant to live for ever. A flag with no kind written down is read as a release flag, which is the only kind
on a clock.

---

Next: [the two gates](the-two-gates.md) · [the skiff and the liner](the-skiff-and-the-liner.md), the other
thing the product state decides · [let it cruise](../guide/let-it-cruise.md)
