PATCH

**`./init` checks that Spec Kit's scripts have the PyYAML they compose the preset templates with, and puts it
right where it can.** From Spec Kit 1.0.9 its bash scripts read a preset's `preset.yml` through the bare
`python3` they call, and a project whose python3 lacks the module learned so at its first `/speckit-specify`:
"PyYAML is required to resolve preset template composition", with no remedy — and on a Homebrew or Debian
Python the obvious `pip install` is refused too (PEP 668). Where the installed Spec Kit's scripts mention it
and `python3` cannot import it, `./init` now installs it into the user site, or, where that Python refuses
pip outside a venv, into a venv at `.delivery-tools/venv` that shares the system's packages and prints the
`PATH` line that puts it first; where neither is possible it says exactly what to install. Never fatal, and
silent on a Spec Kit whose scripts never mention it. `docs/speckit-preset.md` says the same.

**Catch-up.** `slipwai migrate` brings the new `./init`; rerun it once after the merge on a machine whose
`python3` lacks PyYAML.
