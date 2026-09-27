# Learning path: adopt an existing repository

> **Experimental.** As [AGENTS.md](../AGENTS.md#versioning-is-not-optional) defines the word: the files
> `adopt` writes, the facts `project.json` records and the questions it asks may change in a MINOR release.
> Every place this reaches you says so until it stops being true. Surprises belong on the public issue tracker.

Four sessions: install the command, wrap an existing tree with the delivery method, keep the command
current, then migrate **and run `/catch-up`**. This is **adopt the method**, not **generate the skeleton**
— nothing about strangler-versus-rewrite has to be decided first. Full reference:
[Adopt an existing repository](adopting.md), [Install the command](executable.md), [Bring a generated
project forward](upgrading.md) (the same merge path).

---

## 1. Install the command

Needs **Python 3.11+** and **Git**. **`uv` is the recommended installer**:

```sh
uv tool install slipwai
slipwai --version
```

```text
slipwai 1.0.0
```

Alternatives are in [Install the command](executable.md).

---

## 2. Adopt the repository

Start at the **root** of a repository the factory did not make. The tree must be clean — `adopt` leaves
one factory commit, and `git reset --hard HEAD^` undoes exactly that:

```sh
cd /Users/you/dev/legacy-worker
git status   # nothing to commit
slipwai adopt
```

It surveys the tree, shows every directory that builds, and asks one question — where your CI runs, a fact
about your forge rather than your code. In the list, ↑/↓ move and Enter chooses:

```text
Adopt the delivery method here (experimental). The survey read the tree; what it
found is below. Nothing here is recorded as an application yet: which of these the gate should hold,
what each is called and what it owns are questions the code answers, and the agent asks them with the
code in front of it. This asks the one thing the tree cannot settle on its own.

2 directories that build:
  .   python      from requirements.txt  (2 of 8 targets have a command)
  ui  javascript  from ui/package.json  (3 of 8 targets have a command)

Where does this repository's CI run? (decides what shape the gate's CI
configuration can take, which is a fact about your forge and not about your
code)
    github — GitHub — the gate is an Actions workflow under .github/workflows
    gitea — Gitea or Forgejo — the same Actions workflow, which they run too
    gitlab — GitLab — the gate is a job to include from .gitlab-ci.yml
    other — Jenkins, Azure, Bitbucket, CircleCI or another — nothing is written;
    your CI runs the gate's command
  ❯ none — no CI runs this repository — nothing is written until one does
CI forge: none
adopted legacy-worker with slipwai 1.3.0 — experimental: this path is new, its shape may change in a MINOR, …
291 files written under delivery/ and beside it; nothing of the repository's own was written over. One
commit by the factory; `git reset --hard HEAD^` undoes all of it.
  2 buildable directories, none of them recorded as an application yet — what each is, what it is called
  and what it owns are questions the code answers:
    . (python, from requirements.txt), 2 of 8 targets have a command
    ui (javascript, from ui/package.json), 3 of 8 targets have a command
  Until one is confirmed, `verify` refuses rather than passing over nothing: /ground asks about each with
  the code in front of it, and `slipwai adopt --confirm <name>` records the answer.
…
Next: ./delivery/init is running now — it installs Spec Kit and projects the skills and commands …
Then: /ground, in the agent — it asks what the tree could not say, starting with which of the directories
above is an application …
Then: make verify — the gate, once a candidate above has been confirmed …
```

**Nothing is wrapped yet.** Every directory that builds is recorded in `project.json` as a *candidate*, and
which of them is an application — a directory whose build the gate holds — is `/ground`'s first question,
asked by your coding agent after it has read the code ([ADR 0003](adr/0003-a-wrapped-application-begins-as-a-candidate.md)).
Until one is confirmed, `make verify` refuses rather than passing over nothing.

Your `README.md` is left alone. `AGENTS.md` and `.gitignore` each get a marked block, appended once. The
method lives under `delivery/` by default (`--delivery` names another directory). `--integration <agent>`
names your coding agent; it is taken from the agent you ran `adopt` inside, where there is one.

`--yes` is the unattended path: nothing is asked, and every directory that builds is wrapped as an
application unlooked-at, each fact recorded `detected`. Flags override one answer either way. Outside a
terminal without `--yes`, `adopt` refuses rather than guessing.

That closing list takes longer than one sitting, and it scrolls away. `slipwai adopt --next` says where you
are in it whenever you come back — done, now, then — read off the tree rather than remembered. The same
sequence in prose, with what each step forfeits, is `delivery/docs/adoption.md`; [the brownfield
runsheet](runsheet-brownfield.md) is every command in order.

### Bootstrap, ground, and prove the gate

In a terminal, `adopt` runs `./delivery/init` for you once the adoption is committed (`--no-init` leaves it
to you). It is the same prompt as generate: agent first, then optional extensions as a checkbox menu (Escape
skips; `--extension <key>` names one or adds one later). What it writes is left uncommitted for you to read.

Then, in your coding agent, `/ground`: which candidates are applications, then one row of the map at a time,
then how each application is started. It records answers one at a time and asks you to commit once. Then:

```sh
make verify
```

A red test suite stops that first run and says so: read the failures, then `make ratchet-tighten`
quarantines it deliberately. Commit `delivery/baseline.json`. Next in the agent: `/speckit-constitution`,
`/speckit-specify`, then `/drive`. [The two workflows](two-workflows.md) places this beside generate.

---

## 3. Update the command

Same as the generate path — upgrade the installed `slipwai`:

```sh
slipwai upgrade --check
slipwai upgrade
slipwai upgrade --pre      # count the snapshot of main as well
```

```text
$ slipwai upgrade
slipwai 1.0.0, installed as: uv tool
newest published: 1.1.0
running: uv tool upgrade slipwai
```

An installation configured for a private mirror may still need that mirror's
credentials. Public PyPI installs need none. Detail:
[Upgrade it](executable.md#upgrade-it).

---

## 4. Migrate, then catch up

Adoption writes factory material under `delivery/` the same way generate writes it at the root. When a
newer factory changes that material — or the experimental contract — bring it forward from the repository
root on a clean tree. **The merge is not the end of the upgrade:** `/catch-up` is the work a merge cannot
finish.

```sh
cd /Users/you/dev/legacy-worker
slipwai migrate
```

```text
$ slipwai migrate
migrated legacy-worker from 1.0.0 to slipwai 1.1.0: 32 files
One merge commit. The files this project had changed itself were kept; the rest are what the
factory now generates for its answers.
Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.
What the versions crossed ask of code already here — which no merge can do — is written to
.slipwai/catch-up.md, git-ignored and disposable.
Next: /catch-up, which reads .slipwai/catch-up.md — what these versions ask of code already here — and
runs make verify against it.
```

Your product code stays yours; conflicts land where both you and the factory edited the same lines of
method material. `/survey` re-reads the tree when detection, not the factory's files, is what moved.

Then, in an agent session from the repository root, **do this before considering the upgrade done:**

```sh
/catch-up
```

It reads `.slipwai/catch-up.md` and runs `make verify` against those notes — including catch-up the
experimental adoption contract left. Skipping it leaves the method on a newer factory with obligations
nobody has worked through.

Full recipe: [Bring a generated project forward](upgrading.md); adoption-specific notes stay in
[Adopt an existing repository](adopting.md).

---

## Next

| | |
|---|---|
| [Adopt an existing repository](adopting.md) | Survey, flags, convergence map, ratchet, what it forfeits |
| [The two workflows](two-workflows.md) | Generated and adopted side by side |
| [Gates](verification.md) | The ratchet and day-one green |
| [Generate a new project](learn-generate.md) | The other learning path — a fresh skeleton from answers |
