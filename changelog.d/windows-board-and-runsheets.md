PATCH

**On Windows, the board no longer interrupts itself when it asks whether a captain is running.** It asked
with `os.kill(pid, 0)`, and signal 0 on Windows is a Ctrl-C to every process on the console — the board,
and whatever started it, ended with a `KeyboardInterrupt` whenever the Voyage checked for a running fleet
or a model session. Both checks now ask Windows through the process handle, as `fleet.py` already did.

**Clearance prints its whole answer when its output is piped on Windows.** The `slots:` line carried a
minus sign and a `≤` that a Windows pipe's encoding has not got, so the print raised after the first line
and every slice line after it was lost — which is what a captain and the board read. It says `-` and `<=`.

**Two runsheets are back**: [generate a new project](docs/guide/runsheet-generate.md) and
[adopt an existing repository](docs/guide/runsheet-adopt.md), every step in order with where to type it
and how you know it worked. The README, the start-here and first-feature guides and what is new now
describe the board's Voyage tab, starting from a requirements document, and the interview's last two
questions.

**Catch-up:** `slipwai migrate` brings the corrected `scripts/agents/clearance.py`. The board's fix needs
nothing; a board kept running by the login service is restarted by `slipwai bridge install`.
