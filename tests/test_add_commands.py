"""The commands that reach back out to the factory: `/add-service`, `/add-frontend`, `/catch-up`.

The first two exist so an agent asked for another application runs the factory rather than copying
`apps/service`, so what they have to do is name the factory's command, insist on the questions only the
user can answer, and say what is there now — which is why they are regenerated when the list changes.

`/catch-up` is the other end of the same relationship and is gated separately below: a migration merges the
factory's newer output, and what is left is code the factory has never seen being held to a rule that did
not exist when it was written. The failure it is against is specific — an agent facing a red gate it did
not cause, editing the gate — so the file has to say which repairs are the project's and which are not.
"""
from __future__ import annotations

import tempfile

from support import FactoryTestCase, commit_all
from test_add_service import add_frontend, add_service

from slipwai.assets import NOTES
from slipwai.catalog import CATALOG


class AddCommandsTest(FactoryTestCase):
    def test_both_commands_send_the_agent_to_the_factory_and_to_the_user(self) -> None:
        for profile, backend, frontend in (("event-modelling", "typescript", "react-vite"), ("standard", "go", "none")):
            with tempfile.TemporaryDirectory() as directory:
                repo = self.generate(directory, "grown", profile, backend, frontend)
                listed = (repo / "docs/skills-and-commands.md").read_text()
                for name, verb in (("add-service", "add-service"), ("add-frontend", "add-frontend")):
                    command = (repo / f"commands/{name}.md").read_text()
                    self.assertIn(f"- `/{name}` — `commands/{name}.md`", listed)
                    # The factory's verb, both ways it can be reached, and a refusal to guess a third.
                    self.assertIn(f"`slipwai {verb}`", command)
                    self.assertIn(f"slipwai/slipwai {verb}`", command)
                    self.assertIn("ask where the\nfactory is", command)
                    self.assertIn("by hand", command)
                    # What only the user decides, and what the command decides for itself.
                    self.assertIn("Decide with the user, not for them", command)
                    self.assertIn("the next one free", command)
                    # The tree has to be clean, and the undo is spelled out beside the reason.
                    self.assertIn("git status --porcelain", command)
                    self.assertIn("git clean -fd", command)
                    self.assertIn("make verify", command)
                    self.assertIn("Nothing is committed", command)
                    # The harness projection reads these two keys.
                    self.assertRegex(command, r"^---\ndescription: .+\nargument-hint: .+\n---\n")
                service = (repo / "commands/add-service.md").read_text()
                self.assertIn(f"- `service` — {backend}, port 3000", service)
                self.assertIn(f"is `{backend}`, like `service`", service)
                for axis in CATALOG["axes"]:
                    self.assertIn(f"`--{axis}`", service)
                self.assertIn("--framework quarkus|spring-boot", service)
                self.assertIn("one `DATABASE_URL`", service)
                web = (repo / "commands/add-frontend.md").read_text()
                self.assertIn("--api <service>", web)
                self.assertIn("Without it, `service`", web)
                if frontend == "none":
                    self.assertIn("No browser app yet", web)
                else:
                    self.assertIn("- `web` — browser app on port 5173, `/api` to `service`", web)
                    self.assertNotIn("No browser app yet", web)
                    self.assertIn("WEB_HOST=0.0.0.0", web)

    def test_the_commands_list_what_is_there_after_an_application_is_added(self) -> None:
        """Both files name the applications, so they are among the files the list drives — `add-service`
        reports them as regenerated, and the next reader sees the new application by name."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "regrown", "standard", "typescript", "none", event_store="memory")
            result = add_service(repo, "payments", "--language", "python")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("commands/add-frontend.md", result.stdout)
            self.assertIn("commands/add-service.md", result.stdout)
            service = (repo / "commands/add-service.md").read_text()
            self.assertIn("- `payments` — python, port 3001", service)
            # The default stays the first service, however many arrive after it.
            self.assertIn("is `typescript`, like `service`", service)
            commit_all(repo, "add payments")
            result = add_frontend(repo, "web", "--api", "payments")
            self.assertEqual(result.returncode, 0, result.stderr)
            web = (repo / "commands/add-frontend.md").read_text()
            self.assertIn("- `web` — browser app on port 5173, `/api` to `payments`", web)
            self.assertNotIn("No browser app yet", web)


class CatchUpCommandTest(FactoryTestCase):
    def test_the_command_sends_the_agent_to_the_factory_and_names_the_three_answers(self) -> None:
        """A failing gate after a migration is one of three things and the response differs for each, so
        the command's job is to make an agent say which before it changes anything — and in the one case
        that is a decision already recorded the other way, to stop and ask rather than pick a side."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "caught-up", "event-modelling", "go", "none", target="aws")
            command = (repo / "commands/catch-up.md").read_text()

            self.assertIn("- `/catch-up` — `commands/catch-up.md`",
                          (repo / "docs/skills-and-commands.md").read_text())
            # It runs no factory command: `slipwai migrate` leaves the notes in the project and this reads
            # them, so there is one command to run and not two — and the second is the forgettable one.
            self.assertIn(NOTES, command)
            self.assertIn("written by `slipwai migrate` before it returns", command)
            self.assertIn("Never conclude\nfrom an absent file that the versions crossed asked nothing", command)
            self.assertNotIn("slipwai catch-up", command)
            # The three answers, and that the middle one is the user's.
            self.assertIn("The rule is right and this project has not done it yet", command)
            self.assertIn("this project already decided the opposite, on purpose", command)
            self.assertIn("ask the user which stands", command)
            self.assertIn("The rule does not fit this project", command)
            # The repair that must not happen, which is the one an agent reaches for first.
            self.assertIn("**Never edit a gate to make it pass.**", command)
            self.assertRegex(command, r"^---\ndescription: .+\n---\n")

    def test_the_command_points_at_the_code_index_when_the_project_has_one(self) -> None:
        """`./init --extension codegraph` indexes the project and appends a block to `AGENTS.md` telling an
        agent to query it for blast radius — and until now nothing in any command reached for it, so the
        extension was installed and unused at exactly the moment it was most useful. The pointer is prose
        rather than a generated-or-not paragraph because extensions are chosen at `./init`, after this file
        is written."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "indexed", "event-modelling", "python")
            command = (repo / "commands/catch-up.md").read_text()

            self.assertIn("Use the code index, if this project has one", command)
            self.assertIn("CodeGraph", command)
            self.assertIn("blast-radius question", command)
            self.assertIn("Ask it *before* grepping", command)
            # And it says what to do when there is no index, so the absence is not a stop.
            self.assertIn("has no index and grep is the tool", command)
            self.assertIn("codegraph", CATALOG["extensions"], "the catalog no longer offers the index named")

    def test_a_project_with_nowhere_to_deploy_is_not_told_a_push_is_a_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            local = self.generate(directory, "local-catch-up", "standard", "go")
            self.assertNotIn("a push to `main` here is a deploy",
                             (local / "commands/catch-up.md").read_text())
