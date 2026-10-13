MINOR

**`./init` installs what the target needs, through the target's own hook.** A target package may now answer
`setup`: the project path, from its `scripts`, of a script `./init` runs before anything else production
needs. The keel runs it and reads nothing from it — what a region is, which package manager a tool comes
from, or what a sensible default looks like is the target's to know, never the keel's. `aws` and `azure` ship
`scripts/setup.py`: each installs OpenTofu and its CLI with whatever the machine has (`brew`, `apt`, `dnf`,
`winget`, or the tool's own installer), and settles the region or location with a default on offer. `./init`
installs and signs in `gh` the same way, as the keel's own need; `./init --no-install` only looks. A target
with no hook is checked exactly as before.

**`generate` notices rather than refuses where `./init` will install.** A machine short a tool that the
target's hook puts there is told so and what `./init` will do, and generation goes on. A target without a
hook is still refused, and the refusal now names the `PATH` it searched — a sandbox or an agent's shell with
a trimmed one reads exactly like a machine with nothing on it, and the line is what tells them apart.

**`slipwai package new --kind target` starts a package with a `scripts/setup.py` to fill in.**

**The in-tree copies of `aws` and `azure` are gone.** `packages/aws` and `packages/azure` were byte-for-byte
mirrors of `slipwai-target-aws` and `slipwai-target-azure`, which are where those targets are written and
released from; two sources for one package is how a fix lands in one and not the other. `packages/toy`
stays — it is the suite's fixture, not a published package. The suites that need a cloud skip, as they
always did on a checkout without one; the skiff migration test moved to the aws repository with the script
it exercises.

**Catch-up:** `slipwai migrate` carries each target's `scripts/setup.py` in and rewrites `./init`.
