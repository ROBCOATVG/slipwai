PATCH

**The ratchet now sees findings in an application that is not at the repository root — which, until now, it
never did.** A tool prints the paths it found relative to the directory it ran in, and a wrapped application's
build runs in its own: `cd admin-dev/themes/new-theme && npm exec -- tsc`. Every path it reported was resolved
against the repository root alone, where nothing of that name exists, so the run found no findings at all and
fell back to comparing the exit code — which passes a second error tomorrow exactly as it passed the first.
On a real adoption a plain type error in the project's own source was invisible to it. That is the ratchet
failing at the one thing it exists for, silently, on precisely the repositories it was written for: the ones
whose applications live in subdirectories. A path is now resolved against the directory the build runs in as
well as the root — `project.json` records it — and recorded root-relative either way, so a finding compares
the same however the tool that printed it spelled it.

**Catch-up.** An adopted repository with an application below its root should re-record: its `lint` or
`typecheck` entry in `baseline.json` is almost certainly `{"exit": N, "findings": []}`, which excused the whole
command. `make ratchet-tighten` after reading what the command actually reports replaces it with the findings
that are really there, and the gate holds to no new ones from then on.
