"""The command line: the version it reports, what it refuses, and the questions it asks when given nothing."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from support import FactoryTestCase

from slipwai.assets import ROOT
from slipwai.catalog import CATALOG, validate_catalog
from slipwai.targets import reserved_words


class CliTest(FactoryTestCase):
    def test_version_flag(self) -> None:
        expected = (ROOT / "VERSION").read_text().strip()
        result = subprocess.run(
            [str(ROOT / "slipwai"), "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        self.assertEqual(result.stdout.strip(), f"slipwai {expected}")

    def test_generate_is_a_verb_and_a_bare_name_is_refused_with_the_verbs(self) -> None:
        """`slipwai generate <name>` beside `add-service`, `add-frontend`, `migrate`, `replay`, `upgrade` and `adopt`,
        and `slipwai <name>` is a mistake named as one: the old bare form scaffolded, and an installed
        `slipwai` run that way must say which verb it wanted rather than complain about a flag."""
        bare = subprocess.run([str(ROOT / "slipwai")], text=True, capture_output=True)
        self.assertEqual(bare.returncode, 2)
        self.assertIn(
            "a verb is required: generate, add-service, add-frontend, migrate, replay, upgrade, adopt or converge",
            bare.stderr
        )
        named = subprocess.run([str(ROOT / "slipwai"), "my-product"], text=True, capture_output=True)
        self.assertEqual(named.returncode, 2)
        self.assertIn("invalid choice: 'my-product'", named.stderr)
        self.assertIn("generate", named.stderr)
        for verb in ("add-service", "add-frontend", "migrate", "replay", "upgrade", "adopt"):
            shown = subprocess.run(
                [str(ROOT / "slipwai"), verb, "--help"], check=True, text=True, stdout=subprocess.PIPE
            ).stdout
            self.assertTrue(shown.startswith(f"usage: slipwai {verb}"), shown.splitlines()[0])

    def test_existing_target_is_never_updated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "evolving-product")
            (repo / "product-change.txt").write_text("owned by the product\n")
            before = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
            ).stdout.strip()

            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate", "evolving-product", "--output", directory],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("refusing to overwrite existing target", result.stderr)
            self.assertEqual(
                subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
                ).stdout.strip(),
                before,
            )
            self.assertEqual((repo / "product-change.txt").read_text(), "owned by the product\n")

    def test_a_name_the_target_s_cloud_reserves_is_refused_at_generation(self) -> None:
        """A Cognito hosted-login domain is `<project>-<environment>-staff` and rejects any prefix
        containing `aws`, `amazon` or `cognito` — so a project named `aws-gh` builds a stack whose first
        apply dies after the cluster, the balancer and the distributions are up. The name is the only thing
        that fixes it and it is refused where it is still a choice, naming the word and both ways out."""
        self.assertEqual(reserved_words(CATALOG, "aws"), ["amazon", "aws", "cognito"])
        self.assertEqual(reserved_words(CATALOG, "none"), [])
        with tempfile.TemporaryDirectory() as directory:
            for name, word in (("aws-gh", "aws"), ("amazon-shop", "amazon"), ("our-cognito", "cognito")):
                with self.subTest(name=name):
                    refused = self.refuse(directory, name, target="aws")
                    self.assertIn(
                        f"project name '{name}' contains '{word}', which the aws target reserves anywhere "
                        f"in a name",
                        refused,
                    )
                    self.assertIn("fail partway through its first apply", refused)
                    self.assertIn("reserves 3 words in all, listed in docs/aws-target.md", refused)
                    self.assertIn("--target none", refused)
            # The word is only reserved where the cloud that reserves it is, and a name without one still
            # goes to production the way it always did.
            self.generate(directory, "aws-gh", target="none")
            self.generate(directory, "gh-shop", target="aws", http="fastify")

    def test_bare_generate_prompts_for_each_value_and_accepts_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            factory_before = subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout

            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate"],
                # name, event modelling?, production target, language, service name, what it owns, its
                # bounded context, frontend, browser app name, then one line per axis, then output parent
                input=f"interactive-product\n\n\n\n\n\n\n\n\n\n\n\n\n{directory}\n",
                text=True,
                capture_output=True,
                check=True,
            )

            repo = Path(directory) / "interactive-product"
            metadata = json.loads((repo / "project.json").read_text())
            self.assertEqual(metadata["profile"], "event-modelling")
            self.assertEqual(metadata["deployables"]["service"]["language"], "typescript")
            self.assertEqual(metadata["frontend"], "react-vite")
            # The target is asked second, because it decides the menus that follow, and local only is the
            # default: a project has to ask to go anywhere.
            self.assertEqual(metadata["target"], "none")
            self.assertIn("Production target:", result.stdout)
            # Every axis is asked, separately, and accepting the offered answer gives a project a real
            # event store and the HTTP transport its backend actually has.
            self.assertEqual(
                metadata["deployables"]["service"]["selection"],
                {"event-store": "postgres", "http": "fastify", "auth": "none", "users": "none"},
            )
            prompts = [
                "Project name:",
                # The profile is the one answer a generated project can never revisit, so both foundations
                # and the reason the choice is asymmetric are on screen before the question is asked.
                "Delivery foundation:",
                "event-modelling — Event Modeling —",
                "standard — Standard —",
                "Only one direction is cheap.",
                "flat cost per slice, not a cheap start",
                "Use Event Modeling?",
                "Production target:",
                "none — Local only",
                "aws — AWS",
                "existing — Existing",
                "Choose (none/aws/azure/existing) [none]:",
                "Language (",
                "Service name [service]:",
                # What the first service owns and which context it answers to are asked, because they are
                # what the delivery loop places work against once there is a second service; blank is a
                # legal answer for the first one.
                "What does service own?",
                "Bounded contexts service holds, comma-separated [service]:",
                "Frontend (",
                "Browser app name [web]:",
                "Event store:",
                "memory — In-memory",
                "Choose (memory/sqlite/postgres) [postgres]:",
                "HTTP transport:",
                "Choose (none/fastify) [fastify]:",
                "Staff authentication:",
                # The description is where the reason the axis is not called `oidc` is shown.
                "Every provider on this axis is an OIDC issuer",
                "Choose (none/keycloak) [none]:",
                "Customer authentication:",
                "Never the staff directory",
                "Output parent [",
            ]
            positions = [result.stdout.index(prompt) for prompt in prompts]
            self.assertEqual(positions, sorted(positions))
            self.assertTrue((repo / ".git").is_dir())
            self.assertEqual(
                subprocess.run(
                    ["git", "remote"], cwd=repo, check=True, text=True, stdout=subprocess.PIPE
                ).stdout,
                "",
            )
            self.assertEqual(
                subprocess.run(
                    ["git", "status", "--porcelain=v1"],
                    cwd=ROOT,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                ).stdout,
                factory_before,
            )

    def test_the_profile_question_argues_the_recommendation_it_makes(self) -> None:
        """The profile is the only answer a generated project can never give again — every axis can be
        answered down later with `./init`, this one cannot — so it is held to the axis options' rule that a
        label nobody can read is not a choice being offered, and the recommendation has to state its own
        case. That case runs against the usual "don't buy architecture you cannot name a requirement for"
        instinct: `event-modelling` costs more up front and is the direction that can be walked back, since a
        log folds down into tables while state cannot become history nobody recorded. If the default ever
        flips, the argument in `docs/axes.md` has to be rewritten with it rather than left standing.
        """
        self.assertEqual(CATALOG["default"]["profile"], "event-modelling")
        self.assertTrue(all(profile.get("label") for profile in CATALOG["profiles"].values()))
        without_label = json.loads(json.dumps(CATALOG))
        del without_label["profiles"]["standard"]["label"]
        with self.assertRaisesRegex(ValueError, "profile standard must carry the label"):
            validate_catalog(without_label)
        guidance = (ROOT / "docs/axes.md").read_text()
        self.assertIn("### Which profile", guidance)
        self.assertIn("`event-modelling` is the reversible choice", guidance)
        self.assertIn("flat *marginal* cost", guidance)

    def test_bare_generate_reprompts_after_invalid_answers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [str(ROOT / "slipwai"), "generate"],
                # A Go standard project is asked the transport and identity questions but
                # not the event-store one: that axis belongs to the profile that has the port.
                # The service is asked its name after its language, then what it owns and which bounded
                # context it answers to, and the browser app after its framework; a name that cannot be a
                # directory and a package is refused, so is the service's own, and so is a context spelled
                # like neither. The production target comes between the foundation and the language, and a
                # destination the catalog does not offer is refused like any other answer.
                input=(
                    f"Bad Name\ninteractive-go-product\nmaybe\nno\nmars\n\nrust\ngo\nBad_Name\ncore\n\nBad Context\n\n"
                    f"angular\nreact-vite\ncore\nteller\n\n\n\n{directory}\n"
                ),
                text=True,
                capture_output=True,
                check=True,
            )

            metadata = json.loads((Path(directory) / "interactive-go-product" / "project.json").read_text())
            self.assertEqual(metadata["profile"], "standard")
            self.assertEqual(metadata["deployables"]["core"]["language"], "go")
            self.assertEqual(metadata["deployables"]["core"]["path"], "apps/core")
            self.assertEqual(metadata["deployables"]["teller"]["api"], "core")
            self.assertEqual(metadata["frontend"], "react-vite")
            self.assertIn("Invalid project name", result.stderr)
            self.assertIn("Invalid answer: enter yes or no", result.stderr)
            self.assertIn("Invalid choose: choose one of none/aws/azure/existing", result.stderr)
            self.assertEqual(metadata["target"], "none")
            self.assertIn("Invalid language", result.stderr)
            self.assertIn("Invalid service name: 'Bad_Name' cannot name an application", result.stderr)
            self.assertIn("Invalid bounded context: 'Bad Context' cannot name a bounded context", result.stderr)
            # Blank answers: nothing recorded, rather than "" — the loop tells unanswered from answered.
            self.assertNotIn("purpose", metadata["deployables"]["core"])
            self.assertNotIn("contexts", metadata["deployables"]["core"])
            self.assertIn("Invalid frontend", result.stderr)
            self.assertIn("Invalid browser app name: 'core' is already the name", result.stderr)
            self.assertEqual(
                metadata["deployables"]["core"]["selection"], {"http": "net-http", "auth": "none", "users": "none"}
            )
            self.assertNotIn("Event store:", result.stdout)
            # The default transport is per backend: Go is offered net/http, not the TypeScript answer.
            self.assertIn("Choose (none/net-http) [net-http]:", result.stdout)

    def test_a_terminal_gets_a_list_to_move_through_rather_than_a_word_to_type(self) -> None:
        """Every fixed-list question is an arrow-key menu when both ends are a terminal: ↓ moves, Enter
        picks, and the list collapses to the answer. Driven through a pseudo-terminal, because that is the
        one condition the typed path — which every other test here drives — never meets."""
        import os
        import pty
        import select

        with tempfile.TemporaryDirectory() as directory:
            # Typed answers where the question is free text; for each menu, a keystroke sequence.
            answers = iter([
                "menu-product\n",      # project name
                "\n",                  # Use Event Modeling? (typed yes/no)
                "\x1b[B\r",            # production target: down one, to aws
                "\r",                  # language: typescript
                "\r",                  # service name
                "\n",                  # what it owns
                "\n",                  # bounded context
                "\r",                  # frontend: react-vite
                "\n",                  # browser app name
                "\r",                  # event store: postgres
                "\r",                  # http: fastify
                "c\r",                 # staff authentication: jump to cognito
                "\r",                  # customer authentication: none
                f"{directory}\n",      # output parent
            ])
            pid, fd = pty.fork()
            if pid == 0:  # pragma: no cover - the child is the generator
                # Choosing aws checks the machine for tofu, aws and a forge; this test is about the menu.
                os.execv(str(ROOT / "slipwai"), ["slipwai", "generate", "--skip-checks"])
            transcript = b""
            pending = b""  # what the generator has written since the last answer went in
            stalled = False
            while True:
                ready, _, _ = select.select([fd], [], [], 10)
                if not ready:
                    stalled = True
                    break
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                transcript += chunk
                pending += chunk
                # A typed prompt ends with ": ", trailing space included; a menu has hidden the cursor. Judged
                # on everything since the last answer, not on the chunk: under load a question arrives in
                # pieces, and its header line — "Customer authentication:" — is not yet a question.
                text = pending.decode(errors="replace")
                prompted = text.endswith(": ") or "\x1b[?25l" in text
                answer = next(answers, None) if prompted else None
                if answer is not None:
                    os.write(fd, answer.encode())
                    pending = b""
            if stalled:
                os.kill(pid, 9)
            os.waitpid(pid, 0)
            shown = transcript.decode(errors="replace")
            self.assertFalse(stalled, f"the generator stopped answering; transcript so far:\n{shown[-2000:]}")
            self.assertIn("❯ none — Local only", shown)
            self.assertIn("Choose: aws", shown)
            self.assertIn("Choose: cognito", shown)
            metadata = json.loads((Path(directory) / "menu-product" / "project.json").read_text())
            self.assertEqual(metadata["target"], "aws")
            self.assertEqual(metadata["deployables"]["service"]["selection"]["auth"], "cognito")
            self.assertEqual(metadata["deployables"]["service"]["selection"]["users"], "none")
