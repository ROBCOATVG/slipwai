PATCH

**An extension that declares a hook or a guard and does not ship its script fails conformance.** The suite
looked for the `init` script and no other, and reported a package missing even that one as "not run", which
is a pass. So a package could declare a hook at any point, leave the file out, pass
`slipwai package check` and be published: `codegraph` 1.0.0 declared `after-stage` as `hooks/sync.py`,
shipped no such file, and synced its index after no stage for the life of that version. Conformance now
prints a `ships` line before the six obligations and fails it for each declared script that is not in the
package, naming the point and the path; the defaults count, so a package with no `init.py` that names
another script at `init` has to name one at `project` too. `slipwai extension list` and
`slipwai extension check` say which of an extension's points have no script, where they listed the point as
though it were there. A manifest's `tools` are names an agent calls, not files, so nothing of theirs is held.

`docs/extensions.md` gave `"stages": ["implement", "converge"]` as its example of an `after-stage` hook.
A captain fires `before-stage` and `after-stage` with two names, `drive` and `decide`, so that example
described a hook that never ran. The page now says which names are fired and its example uses one.

**Catch-up:** nothing for a generated project. A publisher runs `slipwai package check .` before the next
release, and a package whose hook names `stages` checks them against `drive` and `decide`. If
`slipwai extension list` says an installed package is not whole, `slipwai extension install <key>` takes a
release that is.
