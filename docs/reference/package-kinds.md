# The kinds of package

The keel names no language, no extension and no cloud. Everything that does is a package: found in the
chandlery, signed, installed, loaded and released the same way, and made by the same verb.

```
slipwai package new <name> --kind language|extension|target|quickstart
slipwai package check
slipwai search --kind extension
```

**There are four kinds**, and `--kind` refuses anything else by listing them.

| Kind | Manifest | What it is | When the keel asks it |
|---|---|---|---|
| `language` | `language.json` | Every answer for one language family, or one framework of a family | At `slipwai generate`, to write the skeleton |
| `extension` | `extension.json` | Developer tooling a project elects | At `./init`, after the skeleton exists. It never changes generated code |
| `target` | `target.json` | Somewhere a project goes to production: the stacks, the pipeline, the preflight, [the two shapes](the-skiff-and-the-liner.md) | At `slipwai generate`, and at `add-service` |
| `quickstart` | a `quickstart` block | The languages, answers and extensions somebody settled once, under a name | At `slipwai generate --quickstart <name>` |

---

## A framework is not a fifth kind

A **family** and a **framework** are both language packages; which one a package is, is a question its
`language.json` answers.

- A **family** package names the family it is (`family`), and may name a `default_framework`. Its `backends`
  may be empty only when it does.
- A **framework** package names the same `family` key, and a `requires` block that names **exactly** its
  family, with a range. A framework may not declare a `default_framework` — that is a family's to say.

The family resolves before the framework, so `java` is a family and `java-quarkus` is a framework of it,
held to that family's version range.

---

## A quickstart is a default, never an override

A quickstart carries required prose — `suits`, a sentence about the product it fits — and a package without
one is refused. A list of package names is no help to the reader a quickstart exists for: the person who
does not know what `uipro` is, or that an extension has to be elected as well as installed.

It is **not** a profile. A profile is the delivery foundation, which is hard to undo; everything a
quickstart holds is reversible. Applying one puts every answer behind a flag a person typed, so it is a
default that can be overridden one answer at a time. Packages in it are named **by range, never by
snapshot**, so a quickstart written today does not pin a team to the version that was installed the
afternoon somebody saved it.

There is no default quickstart, and the keel offers none: a quickstart elects extensions, an extension is a
third-party package, and a default one would be the keel choosing somebody's dev tooling for every project
they ever generate. A worked example lives in [`typescript-ui/`](typescript-ui/).

---

## The import surface, and its ceiling of twenty

**A package may import only the keel modules `import-surface.txt` lists *for its kind*.**

```
make check-structure
```

The file is **the schema, not a description of one**. `scripts/check-structure.py` reads it and fails a
package that imports a keel module not listed, and the suite fails the file itself if it lists a module the
keel does not have. A line on it is a promise that cannot be withdrawn without breaking a package built
somewhere this repository cannot see.

**A section per kind, and each section has the same ceiling of twenty.** Twenty is what the six language
packages actually import. Past it a package is reaching into the keel rather than being answered by it,
which is the same question whichever kind is asking — so the number is **per kind and not a budget shared
between them**. A flat list would have made a target's first line come out of a language's promise, and a
promise that cannot be withdrawn would have come out of nothing. Lines before the first header are the
language's, which is what the whole file was before there was a second kind.

The language section is at twenty and the target section currently holds six. The ceiling is held by
`tests/test_structure.py`, which also holds the language section at exactly twenty.

**The other direction is held too.** The keel may name no product: a `slipwai_language_*` or
`slipwai_target_*` import anywhere in `src/` fails the gate, including one deferred inside a function —
which is still the keel knowing a product.

**Extensions are not on the schema at all.** An extension's executable half is the `init.py` that runs
inside a generated project, where the keel is not installed and nothing of it can be imported. Quickstarts
have no executable half.

The gate also refuses, inside a package's source, a symlink (whose target it does not read — a package holds
its own files) and a compiled module it cannot read.

---

## What each kind is proved against

| Who | Proves | When |
|---|---|---|
| The keel's gate | That the conformance suite and the matrix work, against one toy package held in-tree as a fixture | Every commit |
| Each package's CI | That *that* package passes the suite against a pinned keel, and imports nothing off the surface | Every commit to that package |
| The keel's release | That the published packages still pass against the keel about to ship | Once, at release |

**There is no build-time link between a keel and a package.** The keel's repository pins no package, holds
no submodule, and its gate never reads one. A keel whose gate checks seven packages is a keel that cannot be
changed without them, which is the coupling the packages were split out to remove. A keel change that breaks
a package is found by that package's CI; the release job is the backstop, and it runs once.

---

## Further

- [`docs/extensions.md`](../extensions.md) — the extension manifest, the six obligations, the ten hook
  points and the guards
- [`docs/backend-protocol.md`](../backend-protocol.md) — what a language package's `LANGUAGE` object answers
- [`import-surface.txt`](../../import-surface.txt) — the list itself, with the reason for each line
- [The skiff and the liner](the-skiff-and-the-liner.md) — the target protocol's two shapes
- [Bring an existing codebase](../guide/adopt.md)
