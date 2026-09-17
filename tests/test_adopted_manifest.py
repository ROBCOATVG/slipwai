"""`project.json` for a repository the factory did not make: `origin`, `provenance`, and an application recorded
`"generated": false`.

Brownfield adoption (experimental, as `AGENTS.md` defines the word) needs the manifest to say
three things it never had to: how the repository came to have the factory's material, where each recorded
fact came from — detected, confirmed by the user, or overridden — and which applications already existed
when the method was installed around them. Those last are described, not generated: any language, no
selection, no skeleton, and `commands` saying how their own build answers the Make targets, with a written
`null` where the ecosystem has no answer.

Three readers had to learn this, and each is gated here. The manifest reader carries such a record as
written and hands it to nothing that would ask it a generated service's questions; `add-service` grows the
project beside it and leaves it untouched; `replay` reproduces it byte for byte, which is the proof that the
manifest records these as answers. And the pruner, which reads each service's language to know its layout,
skips it rather than refusing a language it has no layout for. The schema number does not move: every
field is new and optional, and a manifest without them means exactly what it always did.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_add_service import add_service
from test_replay import replay, tree

from slipwai.assets import VERSION
from slipwai.errors import GenerationError
from slipwai.manifest import ORIGINS, PROVENANCES, apps_from_manifest, check_known, origin_of
from slipwai.origin import Adoption, adoption_of
from slipwai.scaffold import project_files
from slipwai.selection import Selection
from slipwai.services import default_apps, services_of, wrapped_of

# A C# service that already existed: a language the factory cannot generate, in a directory of its own choosing,
# with its build's answers to the Make targets — and two written no's.
LEDGER = {
    "kind": "service",
    "generated": False,
    "path": "legacy/Ledger",
    "language": "csharp",
    "commands": {
        "install": "dotnet restore legacy/Ledger",
        "lint": "dotnet format legacy/Ledger --verify-no-changes",
        "typecheck": "dotnet build legacy/Ledger --no-restore",
        "test": "dotnet test legacy/Ledger --no-build",
        "integration": None,
        "adversarial": None,
        "mutation": None,
        "audit": "dotnet list legacy/Ledger package --vulnerable",
    },
    "purpose": "Posts journal entries and keeps the ledger balanced.",
    "contexts": ["ledger"],
    "provenance": {"language": "detected", "commands": "confirmed", "purpose": "overridden"},
    "eventSourced": False,
    "capabilities": [],
}


def apps():
    return default_apps("typescript", "none", Selection({"http": "fastify"}))


def adopted(document: dict) -> dict:
    """The manifest as an adoption would write it: `origin` after `generator`, the existing service last."""
    rebuilt: dict = {}
    for key, value in document.items():
        rebuilt[key] = value
        if key == "generator":
            rebuilt["origin"] = "adopted"
    rebuilt["deployables"] = {**document["deployables"], "ledger": LEDGER}
    return rebuilt


class AdoptedManifestTest(FactoryTestCase):
    def test_an_existing_application_is_read_as_written_and_asked_nothing(self) -> None:
        document = adopted(json.loads(project_files("brown", "event-modelling", "none", apps())["project.json"]))
        read = apps_from_manifest(document)
        check_known(read)  # `csharp` is no backend of this catalog, and that is not a refusal
        self.assertEqual([app.name for app in read], ["service", "ledger"])
        self.assertEqual([app.name for app in services_of(read)], ["service"])
        ledger = wrapped_of(read)[0]
        self.assertEqual(ledger.name, "ledger")
        self.assertFalse(ledger.generated)
        self.assertFalse(ledger.first, "an existing application is never the one `make dev` speaks of")
        self.assertEqual(ledger.language, "csharp")
        self.assertEqual(ledger.commands, LEDGER["commands"])
        self.assertEqual(ledger.provenance, LEDGER["provenance"])
        self.assertEqual(ledger.context_names, ("ledger",))
        # What it records is what it was given: the answers, with nothing added or renamed.
        recorded = {key: value for key, value in LEDGER.items() if key not in ("eventSourced", "capabilities")}
        self.assertEqual(ledger.record(), recorded)
        # And the whole manifest, written again from what was read, is the one that was read.
        files = project_files("brown", "event-modelling", "none", read, adoption=adoption_of(document))
        rewritten = json.loads(files["project.json"])
        rewritten["generator"] = document["generator"]
        self.assertEqual(rewritten, document)
        self.assertEqual(origin_of(document), "adopted")
        self.assertIsNone(origin_of({}), "a manifest without the key is a generated project")

    def test_what_the_manifest_cannot_mean_is_refused_by_name(self) -> None:
        document = adopted(json.loads(project_files("brown", "event-modelling", "none", apps())["project.json"]))
        with self.assertRaises(GenerationError) as refused:
            origin_of({**document, "origin": "found"})
        self.assertIn(" and ".join(ORIGINS), str(refused.exception))
        for broken, missing in (
            ({"generated": "yes"}, "'generated' as true or false"),
            ({"provenance": {"language": "guessed"}}, ", ".join(PROVENANCES)),
            ({"commands": ["dotnet test"]}, "'commands' as a map"),
            ({"commands": {"test": 3}}, "'commands' as a map"),
        ):
            with self.assertRaises(GenerationError, msg=repr(broken)) as refused:
                deployables = {**document["deployables"], "ledger": {**LEDGER, **broken}}
                apps_from_manifest({**document, "deployables": deployables})
            self.assertIn(missing, str(refused.exception))
            self.assertIn("'ledger'", str(refused.exception))

    def test_a_project_with_no_generated_service_is_assembled_and_passes_its_own_gate(self) -> None:
        """The repository the method is installed around: nothing in it was made by the factory, so every part
        that used to reach for "the first service" speaks of what is there instead, and the gate runs the
        recorded commands — a written `null` passing with a line that says so, never an empty recipe."""
        from slipwai.scaffold import write_project
        from slipwai.services import App

        ledger = App(
            "ledger", "legacy/Ledger", "service", "csharp", None, 0, generated=False,
            commands={
                "install": "true", "lint": "test -f legacy/Ledger/README.md", "typecheck": None,
                "test": "sh -c 'test -n \"$HOME\"'", "integration": "test -d legacy",
                "adversarial": None, "mutation": None, "audit": None,
            },
            purpose="Posts journal entries.", contexts=("ledger",), provenance={"language": "detected"},
        )
        for profile in ("standard", "event-modelling"):
            files = project_files("brown", profile, "none", [ledger], adoption=Adoption())
            self.assertEqual(json.loads(files["project.json"])["origin"], "adopted")
            self.assertIn("legacy/Ledger", files["skills/run-the-app/SKILL.md"])
            self.assertIn("`--language` is required", files["commands/add-service.md"])
            # An adopted repository keeps its own README; assembled for the root, the README says what is here.
            self.assertNotIn("README.md", files)
            plain = project_files("brown", profile, "none", [ledger])
            self.assertIn("No service here was made by the factory", plain["README.md"])
            self.assertNotIn("apps/service", files["skills/hexagonal-architecture/SKILL.md"])
            self.assertTrue(
                any(
                    "TypeScript-as-pseudocode until idiomatic Csharp" in text
                    for path, text in files.items() if path.startswith("skills/")
                ),
                "the snippets are disclaimed in the language of the code that is here",
            )
        makefile = files["Makefile"]
        self.assertIn("\tpython3 scripts/ratchet.py ledger lint -- 'test -f legacy/Ledger/README.md'\n", makefile)
        self.assertIn("scripts/ratchet.py", files, "the ratchet ships wherever code older than the gate is")
        # The recorded command reaches the ratchet as one quoted word, with its own quotes spliced the shell's way.
        self.assertIn("""-- 'sh -c '"'"'test -n "$$HOME"'"'"''""", makefile, "a recorded `$` is doubled for Make")
        self.assertIn("@echo 'ledger: no typecheck command recorded in project.json (legacy/Ledger)'", makefile)
        self.assertNotIn("\t\n", makefile, "no target is left with an empty recipe")
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "brown"
            (repo / "legacy/Ledger").mkdir(parents=True)
            (repo / "legacy/Ledger/README.md").write_text("# Ledger\n")
            write_project(repo, "brown", "standard", "none", [ledger], adoption=Adoption())
            verified = subprocess.run(["make", "verify"], cwd=repo, text=True, capture_output=True)
            self.assertEqual(verified.returncode, 0, verified.stdout[-3000:] + verified.stderr[-3000:])
            self.assertIn("ledger: no typecheck command recorded", verified.stdout)
            self.assertIn("verify: all gates passed", verified.stdout)
            grown = add_service(repo, "payments")
            self.assertNotEqual(grown.returncode, 0)
            self.assertIn("--language", grown.stderr)
            grown = add_service(repo, "payments", "--language", "python")
            self.assertEqual(grown.returncode, 0, grown.stderr)
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(list(document["deployables"]), ["ledger", "payments"])
            self.assertTrue(document["deployables"]["payments"]["port"], 3000)

    def test_every_command_carries_an_existing_application_through_untouched(self) -> None:
        """`replay` reproduces the manifest byte for byte, `add-service` grows the project beside the existing
        application, and the pruner — which reads each service's language — passes over it."""
        from slipwai.scaffold import write_project

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "brown"
            document = adopted(json.loads(project_files("brown", "event-modelling", "none", apps())["project.json"]))
            write_project(repo, "brown", "event-modelling", "none", apps_from_manifest(document), adoption=Adoption())
            manifest = repo / "project.json"
            self.assertEqual(json.loads(manifest.read_text())["deployables"]["ledger"], LEDGER)
            before = tree(repo)

            replayed = replay(repo)
            self.assertEqual(replayed.returncode, 0, replayed.stderr)
            self.assertEqual(tree(Path(directory) / f"brown-at-{VERSION}"), before)

            grown = add_service(repo, "payments", "--language", "python")
            self.assertEqual(grown.returncode, 0, grown.stderr)
            document = json.loads(manifest.read_text())
            self.assertEqual(document["origin"], "adopted")
            self.assertEqual(list(document["deployables"]), ["service", "ledger", "payments"])
            self.assertEqual(document["deployables"]["ledger"], LEDGER)
            self.assertEqual(document["deployables"]["payments"]["language"], "python")
            # The gate runs what it recorded; nothing else generated speaks of it — Compose and CI are the
            # generated services', and nothing is scaffolded for an application that exists.
            self.assertIn("dotnet test legacy/Ledger --no-build", (repo / "Makefile").read_text())
            for path in ("docker-compose.yml", ".github/workflows/verify.yml"):
                if (repo / path).is_file():
                    self.assertNotIn("legacy/Ledger", (repo / path).read_text(), path)
            self.assertFalse((repo / "legacy").exists())

            listed = subprocess.run(
                ["python3", "scripts/backing-services.py", "--list"], cwd=repo, text=True, capture_output=True
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertNotIn("csharp", listed.stdout + listed.stderr)
