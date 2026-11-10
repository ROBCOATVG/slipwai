PATCH

**A project on a Homebrew or recent Debian Python runs its scripts from the board.** Where `python3` refuses
pip (PEP 668), `./init` puts PyYAML in `.delivery-tools/venv` and tells a person to put it first on their
`PATH`; what the board starts in that project — its steps, the agents' sessions, Try it, the fleet's reads
and the terminal on Windows — now has it first, so the project's scripts find PyYAML instead of stopping at
their first `import yaml`.

**Catch-up:** nothing.
