# The build floor

The first step under every strategy, before any strategy-specific phase: **each deployable
builds from a clean clone, through one declared build, with every dependency and every tool version written
down.** Nothing above it can be dated, audited, characterised or upgraded until it holds, so no strategy
skips it. What the strategy changes is how far it goes: whether the old build is brought up to date, or pinned
exactly as it is because it is being replaced.

## 1. What a well-set-up build is

Eight criteria, each checkable in the tree.

| # | Criterion | How it is checked |
|---|---|---|
| 1 | **Declared.** One build per deployable, and a root build that builds them all, in dependency order, with one command | `make build` from the root builds every deployable from a clean clone |
| 2 | **Pinned tools.** The build runs through a committed wrapper or a pinned tool version; no global install is assumed | a wrapper (`mvnw`, `gradlew`), `packageManager` with corepack, `uv`, `go.mod`'s `toolchain`, `global.json`; a toolchain file for the runtime (`.tool-versions`, `.sdkmanrc`, Maven toolchains) — section 3 says how it is detected |
| 3 | **Fetched, not committed.** Every dependency is declared by name and version and fetched from a registry. An unknown binary is identified by its checksum against the registry, or held in a declared local repository with where it came from recorded | the survey finds no tracked archive outside a wrapper |
| 4 | **Locked.** The resolved versions are fixed: a committed lockfile, or the ecosystem's equivalent where it has none (pinned plugin versions and an upper-bound check on the JVM) | the lockfile is committed and current; the build fails on a version conflict |
| 5 | **Explicit target.** What the code is compiled for and runs on is stated, not inherited from whichever tool is installed | a `--release`/`target` setting, `requires-python`, `engines`, the `go` directive |
| 6 | **Nothing generated or built is tracked.** Generated code comes out of the build (a code-generation plugin), not out of the repository | `.gitignore` covers the outputs; the generator is a build step |
| 7 | **One command per verb**, recorded in `project.json`: build, test, lint, typecheck, package, smoke — or a written *no* (`null`) with the reason | the record has no verb left unrecorded |
| 8 | **Inventoried.** The build produces a bill of materials of every dependency (an SBOM), which is what a dependency audit reads | a CycloneDX or SPDX file is a build output |

## 2. The toolset and the target are two different things

- **The toolset** is what runs the build: the build tool and its wrapper, its plugins, and the compiler or
  runtime the build executes on. It can almost always be made fully current — the current build tool on the
  current long-term-support runtime — without changing what the code runs on.
- **The target** is what the code is compiled for and runs on. It has a **ceiling** set by the code and its
  frameworks (an old framework that cannot load newer class files, a library that does not run on a newer
  interpreter), and only the platform rungs lift it.

A current toolset compiling for an old target is normal and safe: a current JDK building with `--release 8`, a
current Node building code whose `engines` still says an older major. Keeping the two apart is what lets the
toolset be modernised on day one while the target waits for its rung.

## 3. Detecting what the build needs

The survey works it out from the tree, then checks this machine.

| What is needed | Where the tree says it |
|---|---|
| The runtime and compiler level | the build file's compiler settings (`source`/`target`/`release`, an enforcer's required version, Ant's `javac` attributes, an IDE project's properties); `.java-version`, `.sdkmanrc`, `.tool-versions`, `.nvmrc`, `.node-version`; `engines`; `requires-python`; `go.mod`; `global.json` |
| The build tool and its version | a wrapper's properties (the distribution URL carries the version); `packageManager`; the lockfile's own format version; for a build tool with no wrapper, the IDE or CI configuration that runs it |
| What it has been built with before | CI files (`setup-java`, `setup-node` and the like); a `Dockerfile`'s `FROM` image |
| What this machine has | the tools on `PATH` and their versions, read when the survey runs — so a missing tool is named as the tool (`ant` is not installed), never as the application |

From these it says three things:

1. **The toolchain the build needs as it is**, e.g. "a JDK that can still compile for Java 5, the build tool's
   1.x line, and Maven 3.9".
2. **Whether a current toolchain can still build it at all.** Toolchains drop old targets on a schedule — the
   JDK removed compile targets below 6 in JDK 9, 6 in JDK 12 and 7 in JDK 20 — so the answer is yes, or no
   with the newest toolchain that still can, and the lowest target the current one accepts.
3. **What is missing to pin it**: a wrapper for the build tool, a toolchain file for the runtime, or both.
   Where an ecosystem's build tool has no wrapper, the floor is either moving to one that has (Ant to Maven or
   Gradle), or running it inside a pinned build container.

## 4. How far it goes, by strategy

The criteria are the same everywhere. What differs is whether the old build is **brought up to date** or
**pinned as it is**, and that follows from one question: is new work built with this toolchain?

| Strategy | New work is built with… | The old build's floor |
|---|---|---|
| In place | the old deployable's toolchain — it is the only system | **Up to date**: the toolset fully current; the target raised as high as the code allows today, the ceiling and the rung that lifts it recorded on the ADR |
| Strangler fig, new home `inside` | the old deployable's toolchain — the new modules live in it | **Up to date**, as in place. The new modules are only as current as the deployable, so this is what makes `inside` viable |
| Strangler fig, new home `beside` | the new home's own toolchain | **Pinned as it is**: the old build in a container with its old toolchain, behind `make build`. Enough to characterise it, patch it under the freeze and run it beside the new home; modernising it is work thrown away |
| Rewrite | the new system's own toolchain | **Pinned as it is**, as `beside` |
| Leave it | the old deployable's toolchain, for the little that changes | **Pinned**, with the toolset brought current only where it does not change what is produced (a current build tool; the same target) — every security fix needs a build that still works |

**The new home and the new system meet the floor on day one.** Whatever `generate` or `add-service` writes
comes with its wrapper, its lockfile and its toolchain pins from the language package, so under `beside` and
under a rewrite — where the new system can be a completely new setup — there is nothing to detect or migrate on
that side.

**Up to date, in practice**: the current build tool through a wrapper; current plugins; the build running on the
current long-term-support runtime; the target at the highest level the code and its frameworks accept, found by
raising it until the characterisation tests or `smoke` say stop. A target below what the current toolchain accepts
is itself the first coupled rung (`in-place.md`, *Coupled rungs and stepping stones*) and is recorded as one, never
taken silently by the build step.

## 5. Steps

**B.1 Read what the build needs.** `/survey` records, per deployable, the build tool and its version, the target,
the toolchain this needs, whether a current one can build it, and what is missing on this machine.
- Who: agent (the survey).
- Evidence: `project.json` carries each deployable's `toolchain` with the needed versions and a `buildable-today`
  yes or no.
- Unblocks: the decision below.

**B.2 Decide: up to date, or pinned as it is.** Read off the strategy (section 4); a person confirms where the
answer is not obvious, such as a leave-it whose build tool cannot be updated without changing the output.
- Who: board, from the strategy ADR; person where asked.
- Evidence: the ADR's `Build:` line — `up-to-date, target ceiling <level> (lifted by rung <n>)` or `pinned as-is
  (<image or toolchain>)`.
- Unblocks: B.3.

**B.3 Declare the build.** A root build over every deployable; each deployable's dependencies declared by name and
version, unknown binaries identified by checksum or held in a declared local repository with their origin; the
same versions as today in this step, only resolved differently; generated code produced by a build plugin.
- Who: agent.
- Evidence: criteria 1, 3 and 6 hold; the artefact the new build produces matches the old one (a diff of its
  contents, empty except for intended changes).
- Unblocks: B.4, and every dependency audit.

**B.4 Pin the tools.** A wrapper for the build tool; a toolchain file for the runtime, or the pinned build
container for a build pinned as it is; the lockfile committed.
- Who: agent.
- Evidence: criteria 2, 4 and 5 hold; `make build` works on a machine with nothing but the runtime the toolchain
  file names (or nothing but the container runtime).
- Unblocks: CI, and reproducing a build anywhere.

**B.5 Bring the toolset up to date** (up to date only). The current build tool and plugins, the build on the
current long-term-support runtime, the target raised to its ceiling, the ceiling recorded.
- Who: agent; the ceiling confirmed by the characterisation tests and `smoke`.
- Evidence: the wrapper names the current build tool; the toolchain file names the current long-term-support
  runtime; the ADR records the target and what lifts it.
- Unblocks: the platform rungs — most upgrade recipes run as build plugins on a current toolset.

**B.6 Record the verbs and the inventory.** Each of build, test, lint, typecheck, package and smoke recorded, or a
written *no*; the SBOM produced by the build.
- Who: agent.
- Evidence: criteria 7 and 8 hold; the gate builds through the recorded command in CI from a clean checkout.
- Unblocks: the dependency audit, and every strategy-specific phase.

## 6. The Build row on the map

A convergence-map row, measured like the others and read off the tree, so the floor is a fact on the map and not a
hope: `undeclared` → `declared` (criteria 1, 3) → `pinned` (2, 4, 5) → `reproducible` (6, 7: built in CI from a
clean checkout) → `inventoried` (8). Under *up to date*, `reproducible` additionally needs the toolset current.

## 7. How the method carries it

- **The board's decide step** writes a `Build:` line into the strategy ADR, derived from the strategy, alongside
  the strategy's own lines.
- **The adoption sequence** (the board's voyage, and `slipwai adopt --next`) puts the build floor first after the
  decision, then `smoke`, before the constitution, whatever the strategy.
- **The programme** names the build steps from what the tree shows, including an Ant build, a missing compile
  target, and a Java target no current JDK accepts. For that last one it names the newest JDK that still can
  compile it, and `--release 8` as the stepping stone.
- **The ratchet** names a missing build tool as the tool, not as a failed build.

**Not built yet:**
- An SBOM command proposed automatically.
- Toolchain-needs detection beyond Java targets: other ecosystems' wrappers, toolchain files, and machine tool checks
  at survey time.
- The gate failing on a tracked archive, a missing lockfile or an unrecorded verb once the row is at `reproducible`.

## 8. Anti-patterns

| Anti-pattern | How it is detected |
|---|---|
| The build works only on one machine (an IDE build, a global install, a path baked in) | the gate's clean-checkout build in CI fails |
| The build floor quietly raises the target, and an old framework stops loading | the target in the build file changes without an ADR `Build:` line owning it; `smoke` fails |
| Modernising the old build of a system that is being replaced | the ADR says `beside` or rewrite, and the old build's toolset moves |
| Pinning as-is under in place or strangler `inside`, so new work is built on an old toolchain | the ADR says `pinned` while the strategy is in place or the new home is `inside` |
| Generated code edited by hand because it is committed | generated sources tracked; criterion 6 fails |

## 9. Worked example: an internal booking app

The app builds from an IDE project with its libraries committed in a folder, targets an old runtime level that the
current toolchain no longer accepts, and commits its generated code. The survey records: the build tool, about forty
unversioned libraries, a target two levels below what the current toolchain accepts, and a build tool not installed
on this machine.

- **Under in place, or a strangler fig with its new home `inside`:** the build moves to a wrapped, declared build;
  every library is identified by checksum and declared at its current version; the generator becomes a build
  plugin; the toolset goes to the current build tool on the current long-term-support runtime; the target goes to
  the lowest level that toolset accepts, and the characterisation tests and `smoke` confirm the frameworks still
  load there — the ADR records it as the first coupled rung, with the framework rung that lifts it further.
- **Under a rewrite, or a strangler fig with its new home `beside`:** the same declared build and checksummed
  libraries, but run inside a build container pinned to the old toolchain, with the target unchanged. The new
  system is generated with its own current toolchain and meets the floor on day one.

## 10. Sources

- Maven Wrapper: https://maven.apache.org/wrapper/
- Gradle Wrapper: https://docs.gradle.org/current/userguide/gradle_wrapper.html
- Maven toolchains: https://maven.apache.org/guides/mini/guide-using-toolchains.html
- Maven Enforcer, requireJavaVersion: https://maven.apache.org/enforcer/enforcer-rules/requireJavaVersion.html
- JEP 182, the policy for retiring javac's old source and target options: https://openjdk.org/jeps/182
- Node.js corepack: https://nodejs.org/api/corepack.html
- Go toolchains: https://go.dev/doc/toolchain
- .NET global.json: https://learn.microsoft.com/en-us/dotnet/core/tools/global-json
- uv: https://docs.astral.sh/uv/
- CycloneDX: https://cyclonedx.org/
- Reproducible Builds: https://reproducible-builds.org/
