MINOR

**A service's purpose and bounded contexts can be recorded after the scaffold: `slipwai describe-service`.**
`purpose` and `contexts` are what the delivery loop places a slice against, and `generate` and `add-service`
take them at scaffold time — but a purpose is often left unsaid at the start, and the contexts are found later,
in the model's lanes or the specification's vocabulary, which is where `/drive` says to record them. Until now
that meant editing `project.json` by hand against a file the factory owns, while `docs/architecture.md` went on
saying "no purpose recorded yet". `describe-service <name> --purpose "..." --context <name>` edits the entry in
place — a field given replaces what was recorded, one not given is kept — and regenerates every file that
prints the two fields, derived the same way `add-service` derives its set. `/drive`, `/cruise`, the
architecture page and the `add-service` report now name it wherever they say a purpose or a context is
recorded.
