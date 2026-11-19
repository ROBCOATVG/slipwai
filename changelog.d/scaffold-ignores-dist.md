PATCH

**A scaffolded package can be released twice.** `make release` writes into `dist/` inside the package, and
a release is refused while the package differs from `HEAD` — so the second release was refused over the
first one's output. `slipwai package new` now writes a `.gitignore` holding `dist/` for every kind of
package. For a package scaffolded before, the refusal says that `dist/` is all that differs and gives the
line that ignores it; it is still a refusal, and nothing is ignored or deleted on a publisher's behalf. A
`.gitignore` is a tracked file, so a package that adds one releases it with the rest: no release already
published changes.

**Catch-up:** in a package scaffolded before this, once:
`echo dist/ >> .gitignore && git add .gitignore && git commit -m 'Ignore dist/'`.
