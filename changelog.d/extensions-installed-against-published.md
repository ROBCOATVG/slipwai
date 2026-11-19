MINOR

**`slipwai upgrade` lists each installed extension against what is published, and a migration names an
elected extension whose copy in the project is not the installed package.** Nothing said either. `upgrade
--check` reported the keel and each language, and listed every extension as a language it could not upgrade;
`slipwai extension` had no verb that compared. One project ran `ux-gates` 1.0.0 for a day after 1.0.1 had
fixed the path its CI job calls. `upgrade` now ends with an `extensions:` section — `ux-gates 1.0.0 → 1.0.1
available: slipwai extension install ux-gates`, or `(newest published)` — and its `languages:` section holds
languages only. It moves no extension itself. A project's `scripts/extensions/<key>/` is brought forward by
`slipwai migrate`, which merges what the installed package changed; the catch-up page now has a section
naming each elected extension whose copy still differs afterwards, with both versions, the files, and the
`diff -r` that shows how — and one elected here that is not installed on this machine. No file of a
project's is rewritten to make the two agree: a difference is a change somebody made there, and theirs to
keep or drop.

**Catch-up:** `slipwai upgrade --check`, then `slipwai extension install <key>` for each extension it shows
behind, then `slipwai migrate` in each project that elected it.
