PATCH

**A session that has finished no longer keeps the stage waiting.** A Claude Code print session could write its
final `result` line, with every background task it started reported back, and then never exit: the MCP
servers it had started stayed attached, so `make surfaces` (or model, draft, launch, assess, or the captain's
`/sail`) waited for ever until a person killed the session. The stage then read the kill's exit 143 as a
failure and skipped what comes after a drawing. Every script that starts a headless session now runs it
through one helper in `scripts/agents/harness.py`. The helper passes the output through line by line as
before, and notices when the session has said it is finished with no task still out. If the session is still
there 30 seconds later, the helper stops it and every server it started, and the stage carries on with what
the session reported: 0 for a successful result, 1 for anything else. A harness that does not write
stream-json runs exactly as it did.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/harness.py`, `surfaces.py`, `model.py`,
`draft.py`, `launch.py`, `assess.py` and `captain.py`. Nothing else changes.
