PATCH

**`./init` has uv make PyYAML importable by the `python3` Spec Kit's scripts call, with nothing to
activate.** Spec Kit's scripts need PyYAML on the bare `python3` they take off the PATH. On a Python that
refuses pip outside a venv (PEP 668: Homebrew's on macOS, Debian's and Ubuntu's), `./init` used to build a
venv at `.delivery-tools/venv` and ask you to `export PATH="$PWD/.delivery-tools/venv/bin:$PATH"` before
starting the agent — in every shell, and in no agent session unless it was started from one. It now runs
`uv pip install --python python3`, into that `python3`'s venv if it is a venv's and otherwise `--target`
its user site, which it already reads: uv is what slipwai is installed with, needs no pip on that Python,
and writes a directory rather than the managed environment, so PEP 668 has nothing to refuse and the
system's packages are never touched. Without uv, `./init` says the line that installs it on that machine.
No venv is made, and no `PATH` line is printed.

**Catch-up.** If `./init` gave you the `export PATH=…/.delivery-tools/venv/bin…` line, run `./init` once
more — with no arguments it leaves Spec Kit alone and only repeats this step — then drop that line from
your shell profile and `rm -rf .delivery-tools/venv`.
