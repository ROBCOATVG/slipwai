MINOR

**`slipwai generate` works in PowerShell, and a generated repository's scripts stay runnable in a Windows
clone.** Every file slipwai reads or writes, and every one the Python scripts a project ships read or write,
is now opened as UTF-8 by name. Before, they took the locale's encoding, which is cp1252 on Windows, so the
first `slipwai generate` there stopped with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d`
reading slipwai's own skill files; setting `PYTHONUTF8=1` was the workaround, and is no longer needed. A
test now holds every text-mode `open`, `read_text` and `write_text` to it. Every text file they *write*
is also written with LF (`newline="\n"`): on Windows a write without it turns each line ending into CRLF,
so the pruner `generate` runs left the new project's files, `./init` among them, CRLF on disk.

A generated repository gets a root `.gitattributes`: `* text=auto eol=lf`, with CRLF kept for `.bat` and
`.cmd`. Git for Windows defaults `core.autocrlf` to `true`, which checked every file out with CRLF, and a
`#!/bin/sh` script with CRLF does not run (`/bin/sh^M: bad interpreter`), which made `./init` and the gate
unrunnable under Git Bash and printed an "LF will be replaced by CRLF" warning per file on every commit. An
adopted repository keeps its own root `.gitattributes` untouched and gets one scoped to the delivery
directory (experimental), which decides only for the files under it.

**Catch-up.** `slipwai migrate` brings the `.gitattributes`. In a Windows clone whose files were already
checked out with CRLF, re-check them out once so they take it: with a clean tree,
`git rm -r --cached -q . && git reset --hard`.
