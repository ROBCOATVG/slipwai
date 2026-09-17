# Work in this repository

The factory is held to the standard it generates. `make verify` is the gate — lint, typecheck, structure,
tests — and a change is not finished until it passes. [docs/maintaining.md](docs/maintaining.md) says how to
run it, how the source is laid out, and how to see what a change does to a generated project.

## Versioning is not optional

`VERSION` at the root is the only place this factory's version is written. `pyproject.toml` reads it
(`[tool.hatch.version]`), `assets.py` exposes it, `slipwai --version` prints it, and the wheel carries it as
`slipwai/_bundle/VERSION`. Never repeat the number in a second file, and never edit one under `release/` —
those are build outputs, not sources.

**`main` carries the release it is working towards, as a snapshot.** `VERSION` reads `1.3.0.dev0`: the
next release, marked as not there yet. Every push to `main` that passes every verify job is published as
that snapshot — `1.3.0.dev<N>`, `N` the commits since the last release — the wheel to the registry and the
executable to the forge's rolling `snapshot` pre-release, each replacing the one before. A `.dev` version is
a pre-release, which every installer passes over unless asked, so a snapshot never reaches anyone who did not
ask for it. `make release` is what turns the snapshot into the release: `VERSION` becomes `1.3.0`, the
fragments in `changelog.d/` are assembled into that release's entry in the same commit, that commit is
tagged `v1.3.0`, the next commit opens `1.3.1.dev0`, and all of it is one atomic push
([docs/publishing.md](docs/publishing.md#cutting-a-release)). A released number is never left sitting on
`main` unpublished.

**Every change that reaches a user decides what the release it lands in is.** A user here is whoever runs
`slipwai generate` or works in a repository it made, so a change under `assets/`, `catalog.json`,
`src/slipwai/` or the CLI is user-visible; a change to `tests/`, `docs/` or this file is not. When you are
unsure which a change is, prove it rather than guess: `make starters` materializes every combination under
`build/`, so the diff of that tree before and after is the answer.

| Level | When | Examples |
|---|---|---|
| MAJOR | An answer a project already gave stops being answerable the way it was, or the public configuration contract breaks | An axis, an option or a CLI flag removed or renamed; `schemaVersion` raised in `catalog.json` |
| MINOR | Something a project can newly be given, with every existing answer still meaning what it meant | A backend, a framework, a target, an axis option, an extension, a new generated file |
| PATCH | The same answers, generated better | A fixed asset, a pruning bug, a corrected page that ships into a project |

Rules that hold without exception:

- **The number on `main` is the smallest claim the changes since the last release justify.** A release
  opens the next number as a PATCH, `1.3.1.dev0`, over an empty `changelog.d/`. The first change that
  needs more raises it — to `1.4.0.dev0`, or `2.0.0.dev0` — in the commit that makes the change, and its
  fragment claims that level. The two are checked against each other: the highest level the fragments claim,
  applied to the last released entry, is the number `VERSION` has to carry, and `tests/test_changelog.py`
  fails when it does not. A number is raised, never lowered, and never by a commit that changes nothing a
  user sees.
- **The highest level wins.** A release carrying a fix and a new option is a MINOR, not both, and its
  entry says so once.
- **A released version is spent.** A `v*` tag runs `verify.yml` against the tagged commit, and its `release`
  job publishes once every gate job is green — never beside them, because a published version cannot be
  taken back. The registry accepts a name and version once ([docs/publishing.md](docs/publishing.md)). The tag is `v`
  followed by the release, exactly, and the commit it names is the one whose `VERSION` says that release
  with no suffix. Never move a `v*` tag, never reuse a number, never publish from a checkout whose `VERSION`
  differs from the tag being built. `make release` is the only thing that writes a release into `VERSION`,
  and it holds the checkout to every one of those — run `python3 scripts/tag-release.py --dry-run` to see
  what it checks. The one tag that does move is `snapshot`: it is not a version, nothing is built from it,
  and it is remade by CI on every green push.
- **Say the level out loud.** A change that raises the number names the level and the reason in its
  commit message; a change that does not raise it says why not if it touched a user-visible tree.
- **Experimental is a written exemption, not a mood.** A feature this file names as experimental — today,
  the brownfield adoption path: `layout.delivery` in `project.json` and everything built on it —
  may change or drop what it offers in a MINOR, where the table would say MAJOR; everything else keeps the
  table exactly as written. The exemption holds only while every place a user meets the feature says so:
  the verb's `--help`, the first line of its report, the top of its page under `docs/` and of the page it
  writes into a project, and its changelog lines. A generated project meets none of it and sees no label. A
  change under the exemption still writes its catch-up note, so `migrate` carries an adopted repository
  forward like any other. The label comes off in one commit — a MINOR that names what became stable and
  deletes the banners; nothing is stable by default.
- **Write the entry in the same commit, as a fragment.** [CHANGELOG.md](CHANGELOG.md) carries one entry
  per *released* version; the entry being written is [`changelog.d/`](changelog.d), one file per change with
  its bump level on the first line. Every user-visible change adds a fragment saying what it changed for
  whoever runs this and, where it asks anything of a repository already generated, what that is. The person
  making the change is the only one who knows that last part, which is why it is not written at release
  time — and one file per change is why two branches in flight never conflict over it, however the forge
  decides to test the merge. `make release` assembles them into the entry, in the commit it tags, and
  deletes them. `make changelog` lists the commits since the last release, split by whether they reached a
  user, with the fragments already written, so the entry is a judgement and not a memory test.
  [`changelog.d/README.md`](changelog.d/README.md) has the shape. A generated project records which factory
  made it in `project.json`'s `generator`, and that number — a release, or the snapshot it was heading for —
  is what its maintainer reads the changelog against.
- **The first public release has no predecessor to bump.** `1.0.0.dev0` is therefore the one snapshot
  allowed while `CHANGELOG.md` has no released entry. Its fragments still state what ships; `make release`
  writes the first `## 1.0.0` entry without a bump label, tags it, then opens `1.0.1.dev0`. After that,
  every release follows the arithmetic above.
