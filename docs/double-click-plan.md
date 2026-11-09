# Download, double-click, done

A plan for phase 23, asked for on 2026-11-09 after the question "how can a non-technical person install
slipwai so they can use the UI?". The honest answer was: with a terminal, once — `uv tool install slipwai`,
then `slipwai bridge install` — plus Git and Node by hand. Three pieces were named that would remove the
terminal: a signed executable on the releases page, a first launch that sets the board up by itself, and a
board that finds and offers what the machine is missing. This plan is those three pieces.

**Status, 2026-11-09:** built, uncommitted, on `acp-22-8`: 23.1 to 23.4, 23.7 to 23.9 and 23.11, with
`tests/test_prerequisites.py` and `tests/test_first_run.py`. `Slipwai.app` is built and smoked on this Mac
(`make test-executable` serves the board from it) and packed into an 18 MB `.dmg`; the Windows build is
written and unrun. Two faults the build found and fixed: the spec's `collect_submodules("slipwai")` could not
import the package, so every executable shipped without the modules only a language imports
(`slipwai.project.composition`) and could not load a language; and inside a macOS bundle the keel's root
sat on the link side of `Contents/Resources`, so every asset read as an escape. 23.5 and 23.6 are deferred: the pilot
ships unsigned (section 6); 23.10 on a clean Mac and a clean Windows machine. The app has no icon of its own yet: the
brand is an SVG and the bundle wants `.icns` and `.ico`.

**The principle the plan serves:** a non-technical person meets slipwai as an app — a file they download
and open — and the first thing they see is the board. Everything the terminal did for them before, the app
does or the board offers as a button. **The command line does not change.** `slipwai` in a terminal, `uv tool
install slipwai`, the executable run from a shell, `slipwai bridge install`: each does exactly what it does
today, and the suite's existing tests are the proof. The app is a second face on the same keel, beside the
first, never in front of it.

## 1. What is wrong, in the words of the code

**Only the command is published.** A tag runs `verify.yml`'s `publish` job, which attaches each
platform's CLI executable and its `.sha256` to the GitHub release (`release-artifacts.yml` is the rehearsal,
read-only on purpose). *Corrected 2026-11-09: this plan first said nothing was published, having read only
the rehearsal.* What no release carries is anything a person can open without a terminal.

**The executable is a terminal program.** `slipwai.spec` builds one `EXE` with `console=True`. On macOS a
bare Mach-O binary double-clicked in Finder opens Terminal.app and runs in it; Gatekeeper refuses it
outright when it is unsigned and quarantined, which every download is. On Windows a console executable
double-clicked opens a black window that closes the board when it is closed, and SmartScreen warns on an
unsigned file.

**A bare `slipwai` opens the board only for a person at a terminal.** `cli_start.will_open` is
`interactive and NO_BROWSER not in argv`. An app opened from Finder or Explorer has no terminal, so it would
print the usage message to nowhere. That is the right rule for a script and must stay the rule for one.

**The board dies with the window that started it.** `open_board` serves in the foreground of the command
that ran it. `slipwai bridge install` (`at_login.py`) is the fix — a launchd agent, a systemd user unit or a
Startup-folder file, each in the person's own account — but a person has to know to type it.

**The login service names whatever copy wrote it.** `at_login.argv` runs `assets.relaunch()`, which for a
frozen copy is `[sys.executable]`. An app opened from `~/Downloads` on macOS runs from a randomised,
read-only App Translocation path; a service written from there points at a path that is gone after the next
reboot. On Windows it would point into Downloads, which people empty.

**Nothing checks the machine.** `agent_ready.py` says it plainly: "Nothing here installs the board, Python,
Node or a cloud target." A missing Git surfaces as a failed generate, mid-way, in a log; a missing Node as an
agent row that cannot launch. Nobody is told before they start what the route they chose needs.

## 2. The decisions

**D1. Two faces, one keel.** The CLI executable ships as it is. The app is the same frozen keel built a
second way — windowed — with one difference in how it starts: it knows it was opened as an app, and then
it opens the board instead of reading `argv`. On macOS the bundle's `Info.plist` sets `LSEnvironment`
`SLIPWAI_APP=1`; on Windows the windowed build is its own file, `slipwai-board.exe`, and its entry point
says so. `will_open` is not touched.

**D2. No installer program.** macOS gets a `.dmg` with `Slipwai.app` and an Applications shortcut, the
drag every Mac user knows. Windows gets one signed `slipwai-board.exe` that places itself on first launch.
Nothing needs an administrator: `at_login.py` already works entirely inside the person's account, and an
installer would be the first thing in slipwai that asked for a password.

**D3. The app places itself before it registers anything.** The login service is written only from a
copy that will still be there tomorrow: on macOS `/Applications` or `~/Applications`, never a translocated
path; on Windows `%LOCALAPPDATA%\Programs\slipwai\`, with a Start-menu shortcut. Where it is somewhere
else, the first page it shows says so and offers the move as a button.

**D4. The board installs a tool only where the machine has none, or only one too old.** Git, Make, Python
and Node are looked for first, on the `PATH` of the login environment the board's children run in. A good
copy is used as it is: no *Install* button, no download, no second copy beside it. Where there is none, the
tool is fetched from its own publisher's archive, checked against the publisher's checksum, and unpacked
under `~/.slipwai/tools/` — the pattern `agent_install.py` already follows for agents — and goes on the end
of the board's children's `PATH`. Where the machine's copy is older than the tool's floor (a Mac's own
`python3` is 3.9; a project needs 3.11), the board installs a newer one the same way and puts it at the
front of its children's `PATH`, since the old copy cannot be replaced and would otherwise still be found.
*Owner's rule, 2026-11-09: "only do this if they aren't already on the machine", then for a copy too old,
"need to update".* The old copy itself, the system `PATH` and the shell profile are never touched.

**D5. Updating tells, it does not replace.** As `upgrade.py` already decides for the executable: a running
copy cannot replace itself. The board shows a strip when a newer release exists, with the download link.
Self-replacement (a Sparkle-style updater) is a later phase if the strip proves not enough.

**D6. macOS and Windows first.** The non-technical person this serves is on one of the two. Linux keeps the
CLI executable and `uv tool install`; an AppImage is a later phase.

**D7. Harness-neutral, as ever.** The app bundles no coding agent and names none. Settings already lists
every agent this machine can launch and installs one; the app's first page sends a person there.

## 3. The three pieces

### Piece 1 — a signed app on the releases page

The release workflow gains a tag-triggered job, separate from the preparation workflow so that one stays
read-only. It builds per platform, signs, and attaches to the GitHub release:

| Platform | File | Signed with |
|---|---|---|
| macOS (arm64 and x86_64) | `Slipwai.dmg` holding `Slipwai.app`; `slipwai-macos` (the CLI) | Developer ID Application, hardened runtime, notarised with `notarytool`, ticket stapled |
| Windows | `slipwai-board.exe` (the app); `slipwai.exe` (the CLI) | Authenticode, via Azure Trusted Signing or an OV certificate |
| Linux | `slipwai-linux` (the CLI) | Sigstore, as the wheel |

Each file has a `.sha256` beside it, which is what `upgrade.py` already tells people to check.
`macos-latest` is arm64, so the x86_64 build needs its own build machine or a universal2 Python; which is an open
point.

### Piece 2 — the first launch

Opened as an app, the keel runs `first_run.py` before anything else:

1. **Place.** If this copy is translocated, or not in an Applications folder (macOS), or not in its
   per-user programs folder (Windows), serve one page: "Move slipwai to Applications" (or "Set slipwai up
   on this PC"), one button. macOS moves the bundle; Windows copies itself and writes the Start-menu
   shortcut. Then it relaunches from the new place.
2. **Register.** `at_login.install` with the placed path, so the board runs from now on. Where a service
   already exists and names another copy — an older download, a moved app — it is rewritten to this one.
3. **Open.** The board, on the home folder, in the default browser — `open_board`, as today.

Every later launch is step 3 alone: the board is already running, so the app opens a tab on it and exits.
Settings gains a *Remove from this machine* button: `at_login.remove`, and the line that says where the
app is so it can be dragged to the bin.

### Piece 3 — the board checks the machine

`prerequisites.py` holds one table: each tool, how it is found, which routes and packages need it, and how
it is installed on each platform. Its rows come from 23.1's audit of the code, not from this page; the
expected rows are Git (every generate and adopt), Node (TypeScript and JavaScript projects, `npx` agents),
and whatever 23.1 finds the generated project's own gate needs on the machine (`make`, a `python3` new
enough for the toolkit's scripts).

The board shows it in two places. **Settings** gets a *This machine* card: each tool, found or not, its
version, and an *Install* button. **The three start pages** check the rows their route needs before the
person starts and say what is missing at the top, with the same button — so nobody types a brief for ten
minutes and then meets a Git error.

*Install* follows D4, and appears only on a row the machine does not have. On macOS Git has a second way, Apple's own: `xcode-select --install` opens the
system's dialog and needs no download of ours. Where a tool cannot be installed by the board on this
platform, the card says what to install and links to its publisher's page.

## 4. The slices

| Slice | What | Size | Done when |
|---|---|---|---|
| 23.1 | The prerequisites audit: what a project made or adopted from the board needs on the machine, per route and per package, read from the code and the toolkit, recorded as `prerequisites.py`'s table and a section here | S | Every row names the code that needs it; a test fails when a language package declares a tool the table lacks |
| 23.2 | The release carries the app: `verify.yml`'s tag job, which already publishes the CLI executables, smokes the app and adds `Slipwai-<v>-macos-arm64.dmg` and `slipwai-board-<v>-windows-x64.exe` with their `.sha256` | S | A release candidate tag has the files |
| 23.3 | The app face: `slipwai.spec` gains `Slipwai.app` (windowed, `LSEnvironment`, the brand icon) and `slipwai-board.exe` (`console=False`); the app entry opens the board without a terminal and writes nothing to a stdout it does not have | M | `scripts/smoke-executable.py` gains an app mode that launches it with no terminal and reads `/board.json`; the CLI smoke is unchanged |
| 23.4 | The first launch: `first_run.py` — place, register, open; the translocation and Downloads checks; the relaunch from the placed copy; the service rewritten where it names another copy; *Remove from this machine* on Settings | M | `tests/test_first_run.py` over a fake home proves each branch; a bare `slipwai` in a terminal is byte for byte what it was |
| 23.5 | *Deferred: the pilot ships unsigned.* macOS signed and notarised: hardened runtime and the entitlements PyInstaller needs, `notarytool`, staple, the `.dmg` | M | A downloaded `.dmg` opens on a clean macOS account with no Gatekeeper prompt beyond "downloaded from the internet". Waits on the owner's Apple Developer account |
| 23.6 | *Deferred: the pilot ships unsigned.* Windows signed: both executables Authenticode-signed in the job | S | The signature verifies with `Get-AuthenticodeSignature`. Waits on the owner's signing route |
| 23.7 | *This machine*: the card on Settings and the check at the top of the three start pages, from 23.1's table | M | `tests/test_settings_page.py` and the start pages' tests prove found, missing and the route-specific check; a machine with everything sees nothing new on the start pages |
| 23.8 | Install from the board, only where the machine has no copy or one too old: Git and Node fetched, checksum-checked and unpacked under `~/.slipwai/tools/` with `agent_install`'s fetch, check and unpack; put on the board's children's `PATH`; `xcode-select --install` offered on macOS | M | `tests/test_prerequisites.py` over a local archive proves the checksum refusal and the `PATH`, and that a machine with a good copy is offered no install and fetches nothing; a copy too old gets a newer one ahead of it on the children's `PATH` |
| 23.9 | The update strip: the board reads the latest release and says when this copy is older, with the link | S | A board older than the latest release shows the strip; the same version shows nothing; no network means no strip and no error |
| 23.10 | The live run: a clean macOS account and a clean Windows VM — download, open, a brief on the first page, a generated project with its gate passing — timed and recorded here | S | The two times and every prompt the person met are in this plan's status line |
| 23.11 | The guide: `start-here.md` opens with the download for a person with no terminal, and keeps every command line exactly where it is | S | `make test-docs` passes; the terminal steps are unchanged |

**Order.** 23.1 first, because 23.7 and 23.8 are its table drawn on a page. 23.2 and 23.3 next, in either
order. 23.4 needs 23.3. 23.5 and 23.6 can start the day the accounts exist, and 23.10 needs everything.

## 5. What this plan does not do

- **Create the coding agent's account.** Settings installs an agent and starts its sign-in; the account
  behind it (a subscription, an API key) is the person's to have.
- **Replace itself.** D5: the strip tells; it does not update in place.
- **Ship Linux as an app.** D6.
- **Install Docker** for the backing services that need it. The *This machine* card names it where a
  chosen package needs it, and links to it.
- **Change the command line.** The principle above; 23.4's test holds it.

## 6. Open points

- **Whose name is on the certificates.** *Decided 2026-11-09: unsigned, for an internal pilot* (the owner
  chose option D of four: Volaris, a business unit, a personal account, or unsigned). The release notes and
  `start-here.md` say how to open it the first time: on macOS, System Settings → Privacy & Security → *Open
  Anyway*; on Windows, *More info* → *Run anyway*. 23.5 and 23.6 stay in the table, deferred until the
  app goes past the pilot; whose name then goes on the certificates is asked again at that point.
- **Intel Macs.** A second build machine or a universal2 build. Worth it only if the people this serves still
  have them.
- **The generated project on Windows.** *Answered 2026-11-09: Windows projects through Git Bash and an MSYS Make the
  board installs, macOS and Linux behaving as before — phase 24, [the Windows plan](windows-plan.md); the
  Windows app is held back until its CI is green.*
  The question as first asked: If 23.1 finds that the project's gate needs `make` and a POSIX
  shell, Windows needs either those as tools (D4) or the gate's Windows path. The recent Windows commits on
  the protocol suggest the latter is under way; 23.1 says.
- **`slipwai` on the `PATH` for the app's owner.** The agents and the project's scripts may call the
  command by name. If 23.1 finds they do, 23.4 also links the CLI into a per-user `bin` directory, or the
  board's children get it on their `PATH` the way D4's tools do.

## 7. The audit (23.1), 2026-11-09

Read from the code, not the docs. What a route needs on the machine, and the evidence; `prerequisites.py`
holds the rows the board checks.

| Tool | Needed by | Evidence |
|---|---|---|
| Git | `generate`, `adopt`, every gate, the captains | `scaffold.py` commits the first tree; `adopt.py`; `check-dispatch.py` has no guard for its absence |
| Make | every gate, every stage the board starts | `project/makefile.py`; `init_run.py` runs `make draft`, `surfaces`, `launch` and the rest |
| Python 3.11+ as `python3` | `./init`, every recipe, the pre-push hook — even under a frozen keel | recipes are `python3 scripts/…`; 12 toolkit scripts import `datetime.UTC`, new in 3.11, though `make check-python` accepts 3.10 |
| Node | `verify` on the default event-modelling profile whatever the language; TypeScript and JavaScript; `npx` agents | `project/model_targets.py` (`check-drawio`); `harness.py` |
| uv, Go, a JDK | the python, go and java languages | each language's toolchain recipes |
| `/bin/sh`, `bash` | `./init`, `scripts/verify`, every recipe (`SHELL := /bin/bash`) | `project/init_script.py`, `project/makefile.py` |
| Docker | backing services only, never `verify` | `project/makefile.py` `services-up` |

**Found on the way, not fixed here:** `make check-python` and `preflight.py` accept Python 3.10, which the
toolkit cannot run on. The toolkit has no Windows path: a Windows person needs WSL, which the *This machine*
card says. Agent prompts tell agents to run `slipwai` by name, so the app links it for the board's children
where the machine has none (`first_run.link_command`). Languages declare no tools in `language.json`; the
table's `LANGUAGES` is the one place, until the language protocol grows a member for it.

**Decided 2026-11-09:** a Mac with Apple's developer tools has `/usr/bin/python3` at 3.9. The owner's answer
was "need to update", so a copy too old gets a newer one from the board, ahead of it on the children's
`PATH` (D4).
