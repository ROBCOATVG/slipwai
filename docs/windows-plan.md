# Projects on Windows, through Git Bash

A plan for phase 24, asked for on 2026-11-09 when phase 23's app reached Windows and stopped at a project's
first script. The owner's words: "we need native windows support but dont want to change how it works for
mac and linux". A fully native port — Windows twins of `./init`, the Makefile and every `scripts/verify` —
was planned first (appendix A). After looking at how others put GNU Make on Windows, the owner chose the
smaller road: "i think that may be good enough without messing around with full native". So a Windows
project runs the very same files as a Mac one, under the bash that Git for Windows brings, with Make beside
it, and the board puts both there with no administrator and no terminal.

**Status, 2026-11-09:** built, and a generated project gates green on windows-latest. 24.1 to 24.6, 24.8,
24.9, 24.11, 24.12's publishing and 24.13 are done: the `project` job's Windows row installs Make through the
board, proves `SHELL := /bin/bash` and a `#!` script on a plain recipe line, and runs `make verify` on a
project per profile. What the runs found, each fixed: npm on Windows ignores `--prefix`, so the event
model installs from inside its folder; native Make starts a line with no shell characters itself, so the
Makefile sets `.SHELLFLAGS := -hc` on Windows and every line goes to bash; and `text` in `.gitattributes`
rewrote a committed `.pyc`, so it is `text=auto`. 24.3's spike chose ezwinports' Make — a zip the standard
library opens, pinned by the sha256 SourceForge publishes, where MSYS2's is a `.zst` no Python before 3.14
can read — and `.SHELLFLAGS` is what makes it behave as a Unix Make would. 24.7 is merged in the python
package (`MYPYPATH` joined with `;` under Git's bash) and is ticked when a Python project gates there; no
other package joins a path list. 24.10 is folded into 24.9: the projection writes committed files, and a
person's tools path does not belong in every clone, so an agent the person starts gets the board's tools
by being started from *Open a terminal here*. Left: the live run on a clean Windows machine (24.12). The
gap analysis behind the plan is section 5.

**The principle the plan serves:** a Windows person gets the same project, the same gates and the same board
as everyone else, and **on macOS and Linux nothing behaves differently.** A file a Mac or Linux machine runs
may change its bytes where Windows needs it to — a path separator chosen by platform — but never what it
does there. *Owner's rule, 2026-11-09: "allow byte changes".* The fence (24.1) makes every such change a
sentence somebody wrote, and the macOS and Linux gates prove the behaviour.

## 1. What is wrong, in the words of the code

**Everything a project runs after it is made goes through a POSIX shell.** `./init` is `#!/bin/sh`
(`project/init_script.py`). The Makefile says `SHELL := /bin/bash` (`project/makefile.py`). Every
`scripts/verify` is `#!/bin/sh`. The board starts every stage as `make <target>` (`init_run.py`). Windows has
none of `sh`, `bash` or `make`, and its Python is `python` or `py`, never `python3`.

**Git for Windows already carries most of the answer.** Its full install has `bash`, `sh`, `sed`, `grep`,
`mktemp` and the rest under `usr/bin`, and it already runs a repository's hooks with its own `sh`. What it
lacks is Make and a `python3`.

**What already works on Windows:** the keel and the board (UTF-8 throughout, `alive()` through ctypes,
`msvcrt` locks, `taskkill /T` for process trees, the Startup-folder login service). `verify.yml` runs the
keel's suite on windows-latest. What has never run there is a generated project.

## 2. The decisions

**D1. The same files, under Git's bash.** No Windows twins. The Makefile, `./init`, `scripts/verify`, the
hook and the toolkit run as they are, with `bash` from Git for Windows and an MSYS build of GNU Make on the
`PATH` of whatever the board starts.

**D2. Bytes may change; behaviour on macOS and Linux may not.** Where a file both platforms run needs a
Windows branch — a `;` where Windows Python splits paths, a `bash` in front of a script Windows cannot start
by its shebang — it gets one, written so the macOS and Linux path through it is the one that ran before.

**D3. The board brings the tools, as phase 23 brings the rest.** The rule of 23.8 holds: a good copy on the
machine is used as it is; the board installs only where there is none or only one too old, into
`~/.slipwai/tools/`, checksum-checked, on the `PATH` of its own children and never the system's. On Windows
the Git row means Git *with bash*: full Git for Windows, used where the person has it, PortableGit where they
do not. Make is a row of its own.

**D4. `python3` exists in both worlds.** For bash, a two-line `sh` shim named `python3` beside the board's
tools. For Windows programs — which start only `.exe` files, so cannot run the shim — the keel and the
toolkit start Python as `sys.executable` on Windows and `python3` everywhere else, which is exactly what
they start today.

**D5. Outside the board, one button.** The person's own terminal does not have the board's tools on its
`PATH`, and 23.8 promised never to put them there. So Settings gets *Open a terminal here*: Git Bash, in the
project, with the board's `PATH`. Agents launched by the board already inherit it; for one the person starts
themselves, the project's agent instructions say where the tools are.

**D6. Spec Kit's bash scripts on Windows too.** Left alone, Spec Kit picks its PowerShell scripts on
Windows. In a project whose every other script is bash, the board passes `--script sh` there, so the slash
commands and `./init`'s own checks find what they expect.

## 3. The slices

| Slice | What | Size | Done when |
|---|---|---|---|
| 24.1 | The fence: sha256 digests of every file macOS and Linux run — the Makefile, `init`, `scripts/verify*`, the pre-push hook, the harness settings and hooks — across the starter matrix, each change to a digest carrying a line that says why behaviour there is unchanged; the macOS and Linux generated-gate jobs stay required | S | A digest that moves without its reason fails the build; green on today's tree |
| 24.2 | Git with bash: on Windows the Git row requires `bash.exe` beside `git`; full Git for Windows used where it is; PortableGit, checksum-checked and silently extracted into `~/.slipwai/tools/`, where it is not; MinGit no longer offered for this | M | `tests/test_prerequisites.py` proves the Windows row; an install on windows-latest leaves a working `bash` |
| 24.3 | Make for Git Bash: a spike first — MSYS2's `make` (a `.zst` the stdlib cannot open before 3.14, and GPG-signed, so pinned by sha256 in the keel) against ezwinports' native build (whose handling of `SHELL := /bin/bash` must be shown) — then the install the spike picks | M | `make --version` and a two-target Makefile with `SHELL := /bin/bash` run from the board's `PATH` on windows-latest |
| 24.4 | `python3` in both worlds: the `sh` shim in the board's tools; the five keel and two toolkit `["python3", …]` sites as `sys.executable` on Windows; the board's tools ahead of `WindowsApps`, whose `python3.exe` is the Store's stub | S | A test per site on windows-latest; on POSIX the argv is unchanged |
| 24.5 | The board starts projects through bash on Windows: `bash ./init` for `./init`, the same for anything it starts as `./…`; `--script sh` to Spec Kit; `core.longpaths` set in the clone | S | `init_run` on windows-latest runs a generated project's `./init` to the end |
| 24.6 | `.gitattributes`: `init`, `scripts/verify*`, `*.sh` and the hook at LF on every checkout | S | A clone with `core.autocrlf=true` checks `init` out with LF and it runs |
| 24.7 | The languages' path lists: the python language's verify, seed and dev join `PYTHONPATH` and `MYPYPATH` with the platform's separator (a MINOR of the python package); go and java checked for the same and for `.venv/bin`-shaped paths | S | `make typecheck` and `make test` pass on a python project on windows-latest; the fence's digests move with their reason |
| 24.8 | The toolkit on Windows: Try it stops a dev server's tree with `taskkill /T` where it calls `os.killpg`; the moorings join a folder and copy `.env` where they link; `ratchet.py`'s `sh -c` proven with Git's `sh` | S | Each under a test on windows-latest; the POSIX paths and their tests unchanged |
| 24.9 | The board on Windows: the tool table's Windows rows (Git with bash, Make, Python, Node); the *This machine* card's WSL note replaced by *Open a terminal here*, Git Bash in the project with the board's `PATH` | M | `tests/test_prerequisites.py` and the settings page tests prove the rows and the button |
| 24.10 | Agents the person starts themselves: the harness projection names the board's tools path in a Windows project's agent instructions | S | The projection test proves the line on Windows and its absence elsewhere |
| 24.11 | CI on windows-latest: a project generated per published language, `bash ./init` and `make verify` with the board's `PATH`; the path conversions MSYS gets wrong (`$(CURDIR)` handed to Python, `/dev/null`, `--flag=/x`) found and fixed here, each with `MSYS2_ARG_CONV_EXCL` or a recipe change the fence records | M | The job is green and required |
| 24.12 | The Windows app published from the release job once 24.11 is green; the live run on a clean Windows machine — download, open, a brief, a project made, its gate green — timed and recorded here | S | The release carries `slipwai-board.exe`; the time and every prompt met are in this plan's status line |
| 24.13 | The guides: a Windows section in `start-here.md` — the app, *Open a terminal here*, what is slower — and no WSL anywhere | S | `make test-docs` passes; the macOS and Linux steps are unchanged |

**Order.** 24.1 first, before anything moves. 24.2 and 24.3 next: nothing runs without bash and Make, and
24.3's spike is the one unknown that could change the plan. Then 24.4 to 24.6, which make a project start;
24.7 and 24.8 in parallel; 24.9 and 24.10 for the person; 24.11 proves it and finds what is left; 24.12 and
24.13 close it.

**Until 24.11 is green the Windows app is held back:** the release job builds and smokes
`slipwai-board.exe` and does not publish it.

## 4. What this plan does not do

- **Change what macOS or Linux do.** D2; the fence and their gates hold it.
- **Port the project's scripts to Windows.** Appendix A is that road, kept for the day bash on Windows
  proves not good enough.
- **Touch the system `PATH`.** D5's button is the way to the tools outside the board.
- **Make a project's own pipeline Windows.** CI stays Linux: Windows is where a person works, not where the
  product runs.
- **Install Docker.** Backing services need Docker Desktop on Windows, as anywhere; the card names it.

## 5. The gap analysis, 2026-11-09

What stands between "the board puts bash and Make there" and a Windows person getting what a Mac person
gets. Read from the code and the six installed language packages.

**Works unchanged once bash, Make and `python3` exist:** every Makefile recipe (`sed`, `grep`, `mktemp`,
`<(...)` included); `./init`, `scripts/verify` and `mvnw` run as scripts under bash; the pre-push hook, which
Git for Windows runs with its own `sh`; `node_modules/.bin/tsx`, which npm also writes as an `sh` shim; the
board's `make <target>`; and an agent typing `make verify` in PowerShell, since Make runs its recipes in bash
whatever shell asked.

| # | Gap | Where | Slice |
|---|---|---|---|
| A1 | Bash needs full Git for Windows or PortableGit (a `.7z.exe`); MinGit, which 23.8 installs, has none (to confirm) | `tool_install.py` | 24.2 |
| A2 | Make for Git Bash: MSYS2's package is `.zst` and GPG-signed; ezwinports' native build is unproven with `SHELL := /bin/bash` | — | 24.3 |
| A3 | `python3`: bash needs a shim; Windows programs cannot start a shim, and seven sites start `python3` | `stage_steps.py`, `cli_init.py`, `converge.py`, `migrate.py`, `adoption_run.py`, toolkit `benchmark.py`, `models.py` | 24.4 |
| A4 | The board starts `./init` by its shebang, which Windows cannot | `init_run.py` | 24.5 |
| B1 | Path lists joined with `:` — `MYPYPATH="$app/src:$app/tests:…"`, `PYTHONPATH=…` — where Windows Python splits on `;` and MSYS does not rewrite relative lists | python package `python.py`, `python_toolchain.py` | 24.7 |
| B2 | MSYS rewrites arguments that look like POSIX paths, now and then wrongly | found by running | 24.11 |
| B3 | `uv` puts tools in `.venv\Scripts`; no package was found naming `.venv/bin`, go and java to check | language packages | 24.7 |
| B4 | No `.gitattributes`, so a Windows clone checks scripts out with CRLF and `sh` fails on `set -eu\r` | generated tree | 24.6 |
| B5 | Spec Kit picks PowerShell scripts on Windows; `./init` checks the bash ones | `init_run.py` | 24.5 |
| C1 | Try it calls `os.killpg`, which Windows lacks — a crash, not a degradation | toolkit `try_it.py` | 24.8 |
| C2 | The moorings symlink logs and `.env`; Windows refuses without Developer Mode or admin | toolkit `moorings.py`, `harbourmaster.py` | 24.8 |
| C3 | `ratchet.py` runs `sh -c`: works with Git's `usr/bin` on the `PATH`, unproven | adoption `ratchet.py` | 24.8 |
| C4 | The extension menu and the guards read `/dev/tty` and elect nothing; the board passes `--extension` anyway | toolkit | accepted |
| D1 | The person's own terminal lacks the board's tools; `git push` there finds no `python3` for the hook | — | 24.9 |
| D2 | An agent the person starts themselves lacks them too | harness projection | 24.10 |
| D3 | MSYS emulates processes slowly: a Windows gate runs slower | — | accepted, said in 24.13 |
| D4 | `node_modules` can pass Windows' 260-character path limit | clone config | 24.5 |
| E1 | Nothing has ever generated and gated a project on Windows | CI | 24.11 |

## Appendix A. The native road, not taken

Kept for the day bash on Windows is not good enough. Windows twins beside the POSIX files, never
replacements: `make.cmd` and `scripts/make.py` reading a `targets.json` rendered from the same model as the
Makefile; `init.cmd` and a Python port of `./init`; a `verify.py` per language through an optional, additive
protocol member, a language without it refused on Windows by name; a Windows hook under `.githooks/windows`;
PowerShell as the shell the pages speak and `.cmd` shims, since a `.ps1` does not run under Windows 10 and
11's default execution policy. The audit found no recipe structured as data — every one, the keel's and the
languages', is shell text — so this road is twelve slices and a change to each of six language
repositories, against this plan's thirteen small ones and one.
