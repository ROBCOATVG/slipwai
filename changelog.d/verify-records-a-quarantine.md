PATCH

**In an adopted repository, `/verify` is where a red test suite is quarantined.** It says what quarantining
means — the failures listed are recorded as known, any new one still fails — and runs `make ratchet-tighten`
only when the person says to, so the decision is theirs and written down. `slipwai adopt`, its `--next` steps and
the adoption guides point there instead of at `make ratchet-tighten`, and say what the root `Makefile` include
gives — the gate from the root — rather than that `make verify` is one word.

**Catch-up:** `slipwai migrate` brings the new `commands/verify.md` and `docs/adoption.md`.
