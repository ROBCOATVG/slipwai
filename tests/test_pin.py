"""The Pin stage of adoption: `/characterise`, `/survey`, and the `adopt --refresh` the second one runs.

Experimental (`AGENTS.md` says what the word means here). Two commands only an adopted repository gets,
and one rule under which a fresh survey meets the record: a fact that was only detected follows the tree, a
fact a person decided is never changed behind their back but put beside what the tree now says, and a
directory that starts building is reported, not adopted. The files the record drives follow the record, and
nothing is committed.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from support import FactoryTestCase
from test_adopt import node_repository, slipwai
from test_replay import git


class PinTest(FactoryTestCase):
    def test_an_adopted_repository_has_the_two_pin_commands_and_the_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            characterise = (repo / "delivery/commands/characterise.md").read_text()
            self.assertIn("## Refuse \"full coverage first\"", characterise)
            self.assertIn("## Doubles are fakes you write, not a framework you add", characterise)
            self.assertIn("Mockito, Moq, gomock", characterise, "named, so a Java agent meets the rule")
            self.assertIn("`delivery/skills/characterisation-tests/SKILL.md`", characterise)
            self.assertIn("`delivery/skills/finding-seams/SKILL.md`", characterise)
            self.assertIn("- `shop` (`.`, javascript): `npm run test`", characterise)
            self.assertIn("Append one row to `delivery/survey/pinned.md`", characterise)
            survey = (repo / "delivery/commands/survey.md").read_text()
            self.assertIn("`slipwai adopt --refresh`, from this directory", survey)
            self.assertIn("**Disagrees.**", survey)
            self.assertNotIn("## The event model", survey, "the standard profile has no model to speak of")
            ledger = (repo / "delivery/survey/pinned.md").read_text()
            self.assertIn("| Date | Behaviour | Seam | Tests | Runs with |", ledger)
            written = (repo / "delivery/.written").read_text().splitlines()
            self.assertIn("delivery/commands/characterise.md", written)
            self.assertNotIn("delivery/survey/pinned.md", written, "the ledger is the repository's, never replaced")
            # How the application is run is proven into a file the repository owns; the skill only points there.
            running = (repo / "delivery/survey/running.md").read_text()
            self.assertIn("## `.` (javascript)\n\nNot yet proven.", running)
            self.assertNotIn("delivery/survey/running.md", written)
            skill = (repo / "delivery/skills/run-the-app/SKILL.md").read_text()
            self.assertIn("**`delivery/survey/running.md`**", skill)
            self.assertIn("never here", skill)
            page = (repo / "delivery/docs/adoption.md").read_text()
            self.assertIn("`/characterise` pins the current behaviour", page)

            event = node_repository(Path(directory) / "ev")
            self.assertEqual(slipwai(event, "adopt", "--yes", "--profile", "event-modelling").returncode, 0)
            self.assertIn("`external: true`", (event / "delivery/commands/survey.md").read_text())

    def test_a_re_survey_removes_what_the_record_no_longer_drives(self) -> None:
        """The first real adoption's refresh read the forge as `none`, dropped the gate from `.written` and left the
        workflow in the tree, where the next survey took it for the repository's own CI. Two rules now: the forge a
        detected gate was written for stands while the gate is the only CI in the tree — the repository retiring a
        workflow of its own did not move it to another forge, and the gate is working CI there — and what the record
        no longer drives, because a person moved the forge, is removed with its directory and said."""
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            self.assertEqual(slipwai(repo, "adopt", "--yes").returncode, 0)
            gate = repo / ".github/workflows/verify-delivery.yml"
            self.assertTrue(gate.is_file(), "their GitHub Actions CI made the gate a workflow beside it")
            git(repo, "rm", "-q", ".github/workflows/ci.yml")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "no more CI of their own")
            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertNotIn("forge refreshed", refreshed.stdout, "the gate is CI in the tree; the forge stands")
            self.assertNotIn("removed:", refreshed.stdout)
            self.assertTrue(gate.is_file())
            document = json.loads((repo / "project.json").read_text())
            self.assertEqual(document["ci"]["forge"], "github")
            self.assertEqual(document["ci"]["evidence"],
                             "the delivery gate this factory wrote, .github/workflows/verify-delivery.yml")
            self.assertEqual(document["survey"]["ci"], [], "the factory's own gate was never their CI")
            # A person moves the forge: the record no longer drives the workflow, and it goes — with its directory.
            document["ci"].update(forge="none", provenance="overridden")
            (repo / "project.json").write_text(json.dumps(document, indent=2) + "\n")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-qam", "CI runs nowhere now")
            moved = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(moved.returncode, 0, moved.stderr)
            self.assertIn("removed: `.github/workflows/verify-delivery.yml`", moved.stdout)
            self.assertFalse(gate.exists(), "the orphan is gone, not left for the next survey to find")
            self.assertFalse((repo / ".github").exists(), "and so is the directory it emptied")
            self.assertEqual(json.loads((repo / "project.json").read_text())["ci"]["forge"], "none")

    def test_a_re_survey_refreshes_what_was_detected_and_questions_what_was_decided(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = node_repository(Path(directory))
            result = slipwai(
                repo, "adopt", "--yes", "--command", "shop:test=node --test test/", "--infrastructure", "unmanaged"
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            # The build gains a typecheck script, infrastructure code appears, and a second directory builds.
            package = json.loads((repo / "package.json").read_text())
            package["scripts"]["typecheck"] = "node -e 'process.exit(0)'"
            (repo / "package.json").write_text(json.dumps(package))
            (repo / "infra").mkdir()
            (repo / "infra/main.tf").write_text("# tf\n")
            (repo / "tools/reports").mkdir(parents=True)
            (repo / "tools/reports/go.mod").write_text("module reports\n\ngo 1.22\n")
            dirty = slipwai(repo, "adopt", "--refresh")
            self.assertNotEqual(dirty.returncode, 0)
            self.assertIn("uncommitted changes", dirty.stderr)
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "grows")

            refreshed = slipwai(repo, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertTrue(refreshed.stdout.startswith("re-surveyed (experimental)"))
            # The recorded test command was overridden, so the fresh detection is reported, not applied.
            self.assertIn("disagrees: shop: commands was overridden as", refreshed.stdout)
            self.assertIn(
                "infrastructure: home was overridden as `unmanaged`, and the tree now proposes `here`", refreshed.stdout
            )
            self.assertIn("not wrapped: `tools/reports` builds (go, go, from `tools/reports/go.mod`)", refreshed.stdout)
            document = json.loads((repo / "project.json").read_text())
            shop = document["deployables"]["shop"]
            self.assertEqual(shop["commands"]["test"], "node --test test/", "a decided fact stands")
            self.assertIsNone(shop["commands"]["typecheck"], "commands is one record: the new script waits")
            self.assertEqual(shop["provenance"]["commands"], "overridden")
            self.assertEqual(document["infrastructure"]["home"], "unmanaged")
            self.assertEqual(document["infrastructure"]["describedBy"], ["opentofu / terraform"])
            self.assertEqual(sorted(document["deployables"]), ["shop"])
            self.assertIn("tools/reports", (repo / "delivery/survey/survey.md").read_text())
            self.assertNotEqual(git(repo, "status", "--porcelain").stdout, "", "nothing is committed")

            # Recorded as detected, the same facts follow the tree, and the Makefile follows the record.
            detected = node_repository(Path(directory) / "det")
            self.assertEqual(slipwai(detected, "adopt", "--yes").returncode, 0)
            package = json.loads((detected / "package.json").read_text())
            package["scripts"]["typecheck"] = "node -e 'process.exit(0)'"
            (detected / "package.json").write_text(json.dumps(package))
            (detected / ".nvmrc").write_text("22\n")
            git(detected, "add", "-A")
            git(detected, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "lint")
            refreshed = slipwai(detected, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertIn("refreshed: shop: commands refreshed from `package.json`", refreshed.stdout)
            self.assertIn("refreshed: shop: toolchain refreshed from `package.json`", refreshed.stdout)
            shop = json.loads((detected / "project.json").read_text())["deployables"]["shop"]
            self.assertEqual(shop["commands"]["typecheck"], "npm run typecheck")
            self.assertEqual(shop["toolchain"]["version"], "22")
            self.assertEqual(shop["provenance"]["commands"], "detected")
            makefile = (detected / "delivery/Makefile").read_text()
            self.assertIn("ratchet.py shop typecheck -- 'npm run typecheck'", makefile)
            self.assertIn("node-version: '22'", (detected / ".github/workflows/verify-delivery.yml").read_text())
            # The runtime version a person confirmed stands through a refresh — the first real adoption's tree pinned
            # nothing, and every `/survey` reset a confirmed version to nothing — and a tree that pins another is a
            # disagreement, as a command is; the ecosystem's other facts still follow the tree.
            document = json.loads((detected / "project.json").read_text())
            document["deployables"]["shop"]["toolchain"]["version"] = "18"
            document["deployables"]["shop"]["provenance"]["toolchain"] = "confirmed"
            (detected / "project.json").write_text(json.dumps(document, indent=2) + "\n")
            git(detected, "add", "-A")
            git(detected, "-c", "user.name=t", "-c", "user.email=t@local", "commit", "-q", "-m", "runs on 18")
            refreshed = slipwai(detected, "adopt", "--refresh")
            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            self.assertIn('disagrees: shop: toolchain.version was confirmed as "18", and `package.json` now pins "22"',
                          refreshed.stdout)
            shop = json.loads((detected / "project.json").read_text())["deployables"]["shop"]
            self.assertEqual(shop["toolchain"]["version"], "18", "a confirmed version is never reset from the tree")
            self.assertIn("node-version: '18'", (detected / ".github/workflows/verify-delivery.yml").read_text())

            generated = self.generate(directory, "made", "standard", "typescript")
            refused = slipwai(generated, "adopt", "--refresh")
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("generated, not adopted", refused.stderr)
