---
description: Run the project's gates and say what passed, what failed and what was skipped — each failure with the line the gate printed and what it asks for
argument-hint: [gate]
---

# Verify

`{{make}} verify` is the whole gate: every check this project holds itself to, the one CI runs, and what a
slice has to pass before it merges. This runs it from the session and reads the result back, so nobody has to
scroll for it.

Run `{{make}} -k verify`. The `-k` is the point: make stops at the first failing gate without it, and a person
who fixes one and runs again to find the next has paid for the whole run each time. With it, one run names every
gate that fails. Where `$ARGUMENTS` names a gate (`check-chart`, `lint`), run `{{make}} $ARGUMENTS` instead and
read it the same way.

Then say, in this order:

1. **The verdict, in one line.** `verify: all gates passed` only where that line was printed. Otherwise how many
   gates failed, by name.
2. **Each failure.** The gate — the target in `make: *** [<target>] Error`, not the script behind it — then the
   line it printed naming the file or the rule, and what that line says to run or change. Quote the gate's own
   words. A paraphrase of a refusal is a second thing to be wrong.
3. **What was skipped.** A gate that printed `SKIPPED` or said it did not run has not passed. Say that, and say
   what it needs — a browser, a package, a running service. A warning is not a failure, and is counted rather
   than listed one by one.

**Read, don't repair, unless asked.** The person typed this to find out where the project stands. Where a gate
names a command that only regenerates a derived file — `{{make}} chart`, `{{make}} agents` — say so and leave it
for them to say yes to; running it is a change to the tree.

**Never edit a gate, its configuration, or a pinned record to make it pass.** They come from the factory, the
next migration brings them back, and a gate that has been edited to pass is a project nobody can say anything
about. A gate that is wrong is a report to the factory, not a local fix.

**A red test suite in an adopted repository is the one decision this records.** Where the repository was
adopted, its own lint, type and test findings are held to a committed baseline, and a suite that was red before
the method arrived stops the gate and says so. Say what quarantining means: the failures it lists are recorded
as known, the gate passes on them, and any *new* failure still fails it, until the suite is green and the entry
clears. If the person says to quarantine it, run `{{make}} ratchet-tighten` and say what it recorded — it is
their decision written down, not a gate edited to pass, which is why it waits for them.

Where `.slipwai/catch-up.md` exists and the failures look like gates that arrived with a migration — code that
was correct when it was written, refused by a rule it never had to meet — say `/catch-up` is the command for
that and stop.
