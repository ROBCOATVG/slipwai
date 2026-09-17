PATCH

**A `./init` rerun that asks nothing of Spec Kit no longer reinstalls it, so adding an extension or
re-answering an axis finishes where github.com is unreachable.** Every `./init` ran
`specify init --here --force`, and where the `specify` CLI is not already installed that means fetching
Spec Kit from its repository — so `./init --extension codegraph` in an offline sandbox, or
`./init --repository <url>` once the forge tools were finally there, died on the network before doing any
of the local work it was actually asked for. Now, when the argument scan leaves nothing to forward and
`.specify/integration.json` records an installed integration — the file only `specify init` writes, since
generation itself ships presets under `.specify/` — the bootstrap is skipped and the script says so.
Anything Spec Kit-bound still delegates exactly as before: the first `./init`, and any rerun passing
`--integration <agent>` or another forwarded flag.
