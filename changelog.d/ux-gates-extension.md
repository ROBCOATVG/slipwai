MINOR

**`./init --extension ux-gates` puts objective UX gates in `make verify`.** It installs plugin87's
ux-ui-agent-skills kit under `tools/ux-gates/` (ignored by Git, pinned, reproducible) and adds
`check-ux-gates`: the kit's no-literal-values gate over each browser app's `src/` — a colour, pixel size or
duration outside `tokens.css` fails the build, which is the rule `docs/design.md` already stated, now
measured — and, where Node and Playwright are present, its real-render gates over every `*.html` under
`<app>/screens/`: contrast in light and dark across default, hover and focus, visible focus, target size,
no overflow at phone widths, and axe. With no browser the render gates are reported as skipped, never as
passed; a checkout without the kit is likewise skipped, and `UX_GATES_REQUIRE=1` makes that the failure it
is wherever the kit is expected. The generated baseline passes the file gate: the focus ring's width and
offset became tokens (`--focus-ring`, `--focus-ring-offset`) rather than the two literal pixels they were.
Every generated Makefile carries the target whether or not the extension is adopted; unadopted, it says so
and passes.

**Catch-up.** A merge brings the new Makefile target and `scripts/check-ux-gates.py`, and the tokenised
focus ring in `tokens.css` and `base.css` (take the factory's side unless the project restyled the ring).
Adopt the gates with `./init --extension ux-gates` where a browser app exists.
