# The kinds of package

The keel names no language, no extension and no cloud. Everything that names one is a package. Every
package is found in the chandlery, signed, installed, loaded and released in the same way, and the same verb
makes every package.

```
slipwai package new <name> --kind language|extension|target|quickstart
slipwai package check
slipwai search --kind extension
```

**There are four kinds.** `--kind` refuses any other value, and the refusal lists the four kinds.

| Kind | Manifest | What it is | When the keel asks it |
|---|---|---|---|
| `language` | `language.json` | Every answer for one language family, or one framework of a family | At `slipwai generate`, to write the skeleton |
| `extension` | `extension.json` | Developer tooling a project elects | At `./init`, after the skeleton exists. It never changes generated code |
| `target` | `target.json` | Somewhere a project goes to production: the stacks, the pipeline, the preflight, [the two shapes](the-skiff-and-the-liner.md) | At `slipwai generate`, and at `add-service` |
| `quickstart` | a `quickstart` block | The languages, answers and extensions somebody settled once, under a name | At `slipwai generate --quickstart <name>` |

---

## A framework is not a fifth kind

A **family** and a **framework** are both language packages. The package's `language.json` says which one
the package is.

- A **family** package names the family that it is (`family`). It can name a `default_framework`. Its
  `backends` can be empty only when it names a `default_framework`.
- A **framework** package names the same `family` key. It also has a `requires` block that names
  **exactly** its family, with a version range. A framework must not declare a `default_framework`. Only a
  family declares that.

The family resolves before the framework. For example, `java` is a family and `java-quarkus` is a framework
of it. `java-quarkus` must stay inside the version range of the `java` family.

---

## A quickstart is a default, never an override

A quickstart must carry one piece of text: `suits`, a sentence about the product that the quickstart fits.
The keel refuses a quickstart package without `suits`. A list of package names does not help the reader
that a quickstart is for. That reader does not know what `uipro` is, or that an extension must be elected
as well as installed.

A quickstart is **not** a profile:

- A profile is the delivery foundation, and it is hard to undo.
- Everything that a quickstart holds can be undone.

When a quickstart is applied, every answer goes behind a flag that a person typed. So the quickstart is a
default, and a person can override it one answer at a time. A quickstart names its packages **by version
range, never by a snapshot version**. So a quickstart written today does not pin a team to the version that
was installed on the afternoon that somebody saved it.

There is no default quickstart, and the keel offers none. A quickstart elects extensions, and an extension
is a third-party package. A default quickstart would make the keel choose somebody's developer tooling for
every project that they generate. A worked example is in [`typescript-ui/`](typescript-ui/).

---

## The import surface, and its ceiling of twenty

**A package can import only the keel modules that `import-surface.txt` lists *for its kind*.**

```
make check-structure
```

The file **is the schema. It does not describe a schema.**

- `scripts/check-structure.py` reads the file. It fails a package that imports a keel module that the file
  does not list.
- The suite fails the file itself if the file lists a module that the keel does not have.

Each line in the file is a promise. Nobody can withdraw it without breaking a package that was built
somewhere this repository cannot see.

**The file has one section for each kind, and each section has the same ceiling of twenty modules.**
Twenty is the number that the six language packages really import. A package that needs more than twenty is
reaching into the keel, instead of being answered by it. That is the same problem for every kind. So the
ceiling is **for each kind. It is not a budget that the kinds share.** With one flat list, a target's first
line would have used up part of the language's promise. A promise that nobody can withdraw would then have
come from nothing.

Lines before the first section header belong to the language section. Before there was a second kind, the
whole file was the language list.

The language section has twenty modules now, and the target section has six. `tests/test_structure.py` holds
the ceiling. It also holds the language section at exactly twenty.

**The rule also works in the other direction.** The keel must not name a product. A `slipwai_language_*` or
`slipwai_target_*` import anywhere in `src/` fails the gate. This includes an import that is deferred
inside a function, because that is still the keel knowing a product.

**Extensions are not in the schema.** An extension's executable part is the `init.py` that runs inside a
generated project. The keel is not installed there, so nothing from the keel can be imported. Quickstarts
have no executable part.

Inside a package's source, the gate also refuses two things:

- a symlink. The gate does not read the symlink's target, because a package holds its own files;
- a compiled module that the gate cannot read.

---

## What each kind is proved against

| Who | Proves | When |
|---|---|---|
| The keel's gate | That the conformance suite and the matrix work, against one toy package held in-tree as a fixture | Every commit |
| Each package's CI | That *that* package passes the suite against a pinned keel, and imports nothing off the surface | Every commit to that package |
| The keel's release | That the published packages still pass against the keel about to ship | Once, at release |

**There is no build-time link between the keel and a language package.** The keel's repository pins no
language package, and its gate never runs a package's own suite. The repository does hold the two target
packages, `packages/aws` and `packages/azure`, as public git submodules. It holds them because the
structure gate and the loader refuse an empty package directory. A keel whose gate checks seven packages is
a keel that nobody can change without them. That is the coupling that the packages were split out to
remove. When a keel change breaks a package, that package's CI finds it. The release job is the backstop,
and it runs once.

---

## Further

- [`docs/extensions.md`](../extensions.md): the extension manifest, the six obligations, the ten hook
  points and the guards
- [`docs/backend-protocol.md`](../backend-protocol.md): what a language package's `LANGUAGE` object answers
- [`import-surface.txt`](../../import-surface.txt): the list itself, with the reason for each line
- [The skiff and the liner](the-skiff-and-the-liner.md): the two shapes of the target protocol
- [Bring an existing codebase](../guide/adopt.md)
