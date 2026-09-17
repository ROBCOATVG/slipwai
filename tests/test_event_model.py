"""The event model a generated project carries, and the workflow that publishes it on any forge."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from unittest import mock

from support import FactoryTestCase

from slipwai.backends import NODE_MAJOR
from slipwai.project.ci_workflows import NODE_SETUP
from slipwai.project.event_model import event_model_page_url, event_model_workflow

SETUP_NODE = re.compile(r"actions/setup-node@(v\d+)\n\s+with:\n\s+node-version: '?(\d+)'?")


class EventModelTest(FactoryTestCase):
    def test_event_model_workflow_publishes_on_any_forge_without_overlap(self) -> None:
        model = event_model_workflow()
        render, deploy = model.split("  deploy:")
        # The two publishing paths must never both run: GitHub Pages has an OIDC deploy, another forge has
        # a branch push, and nothing has both.
        self.assertIn("if: github.server_url == 'https://github.com'", deploy)
        self.assertIn(
            "if: github.server_url != 'https://github.com' && github.ref == 'refs/heads/main'"
            " && github.event_name != 'pull_request'",
            render,
        )
        self.assertIn("HEAD:refs/heads/pages", render)
        self.assertIn("git -C _site init -b pages", render)
        self.assertIn("push --force", render)
        self.assertIn("${{ github.token }}", render)
        # Read-only by default, write only on the job that pushes the branch.
        self.assertIn("permissions:\n  contents: read\n", model)
        self.assertIn("    permissions:\n      contents: write\n", render)
        # The arm64 Chrome substitution is a question about the machine, so it asks the machine — a
        # third-party runner need not populate the runner.arch context.
        self.assertIn('case "$(uname -m)" in', render)
        self.assertIn("chromium-headless-shell", render)
        self.assertIn("MERMAID_PUPPETEER_CONFIG", render)
        # No expression context and no step-level `if:` — an x86_64 runner with a working sandbox no-ops
        # inside the step instead.
        chromium = render.split("- name: A Chromium that can start on this runner")[1]
        chromium = chromium.split("      - name:")[0]
        self.assertNotIn("${{", chromium)
        self.assertNotIn("if:", chromium)
        # Both spellings of the binary. Playwright renamed it — the archive is chrome-headless-shell-linux64
        # and the executable inside is `chrome-headless-shell`, where an older pinned version still produces
        # `headless_shell`. Searching for one name found nothing and failed the step after a good download.
        self.assertIn("-name headless_shell -o -name chrome-headless-shell", chromium)
        # A container runner has the sysctl and cannot write it. Refusing the write is information, not
        # failure: the step says so and hands the decision to the step above, which fetches a Chromium that
        # needs no sandbox. Testing the file's existence read that runner as one that never restricted
        # namespaces, and `tee` under `-e -o pipefail` took the whole job down.
        sandbox = render.split("- name: Let Chromium have its sandbox back")[1]
        sandbox = sandbox.split("      - name:")[0]
        self.assertNotIn("if [ -e ", sandbox)
        self.assertIn('SANDBOX_UNAVAILABLE=1" >> "$GITHUB_ENV"', sandbox)
        self.assertIn("SANDBOX_UNAVAILABLE", chromium)

    def test_the_page_address_reads_both_of_its_halves_from_the_environment(self) -> None:
        """Owner and host both belong to whoever is generating, so neither may be baked in here.

        The host is the one that bit: `http://localhost:3301` is not a forge, it is a daemon reading a local
        Gitea's bare repositories off disk. A project on a remote forge publishes its `pages` branch
        perfectly and the link still goes nowhere, with nothing failing to say so.
        """
        with mock.patch.dict(os.environ, {"GITEA_OWNER": "acme", "GITEA_PAGES_URL": "https://pages.example.com"}):
            self.assertEqual(event_model_page_url("shop"), "https://pages.example.com/acme/shop/")
        # A trailing slash on the variable must not double up against the one this joins with.
        with mock.patch.dict(os.environ, {"GITEA_OWNER": "acme", "GITEA_PAGES_URL": "https://pages.example.com/"}):
            self.assertEqual(event_model_page_url("shop"), "https://pages.example.com/acme/shop/")
        # Unset, the local daemon this repository ships — which is what `scripts/gitea-pages.py` serves.
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(event_model_page_url("shop"), "http://localhost:3301/your-owner/shop/")

    def test_it_installs_the_toolchain_the_verify_workflow_does(self) -> None:
        """One repository, two workflows, one Node. They disagreed about both the action major and the
        language major, with nothing forcing them together; `backends.NODE_MAJOR` is now that thing, and
        this is what would notice a second literal appearing beside it."""
        pins = SETUP_NODE.findall(event_model_workflow()) + SETUP_NODE.findall(NODE_SETUP)
        self.assertEqual(len(pins), 2, f"expected one setup-node in each generated workflow, found {pins}")
        # Agreement first, and on its own: the action major is not this repository's number to hold, so
        # moving both workflows to the next one together must pass here rather than read as a disagreement.
        self.assertEqual(len(set(pins)), 1, f"the two workflows disagree: {pins}")
        self.assertEqual({node for _, node in pins}, {str(NODE_MAJOR)}, f"not NODE_MAJOR: {pins}")

    def test_the_event_modeling_skill_targets_this_repositorys_model_layout(self) -> None:
        """The upstream skill prescribes docs/event_model/ per workflow; this repository keeps one
        cumulative docs/event-model/model.yaml, and an agent reading only the skill went to the wrong
        place."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "modelled")
            for relative in (
                "skills/event-modeling/SKILL.md",
                "skills/event-modeling/references/nine-steps.md",
            ):
                text = (repo / relative).read_text()
                self.assertNotIn("docs/event_model", text, relative)
                self.assertIn("docs/event-model/model.yaml", text, relative)
            skill = (repo / "skills/event-modeling/SKILL.md").read_text()
            self.assertIn("skills/global-event-model/SKILL.md", skill)
            self.assertIn("docs/event-model/README.md", skill)
            self.assertIn("specs/<feature>/slices/<id>/examples.md", skill)

    def test_lanes_ship_per_band_and_the_renderer_patches_mermaid(self) -> None:
        """The notation's picture is actors across the top and streams across the bottom, which Mermaid
        allows because a namespace resolves within a band. mermaid-cli still has #7925, which breaks every
        band, so `make model` patches #7986 into the copy it fetches."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "actor-lanes")
            yaml = (repo / "docs/event-model/model.yaml").read_text()
            self.assertIn("lanes:", yaml)
            self.assertIn("ui: actor", yaml)
            self.assertIn("events: stream", yaml)
            self.assertNotIn("actorLanes", yaml)
            self.assertIn("scripts/event-model/.mermaid-cli/", (repo / ".gitignore").read_text())
            render = (repo / "scripts/event-model/render.ts").read_text()
            self.assertIn("patchInstalledMermaid", render)
            self.assertIn(".mermaid-cli", render)
            patcher = repo / "scripts/event-model/patch-mermaid-swimlanes.ts"
            self.assertTrue(patcher.is_file())
            install = subprocess.run(
                ["npm", "--prefix", str(repo / "scripts/event-model"), "install",
                 "--no-audit", "--no-fund", "--loglevel=error"],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            probe = repo / "scripts/event-model/probe-swimlane-fix.mts"
            probe.write_text(
                "import { applySwimlaneFix } from './patch-mermaid-swimlanes.ts';\n"
                "const broken = `\n"
                "function findSwimlaneByNamespace(swimlanes, namespace) {\n"
                "  if (!namespace || namespace.length === 0) {\n"
                "    return void 0;\n"
                "  }\n"
                "  return Object.values(swimlanes).find((swimlane) => swimlane.namespace === namespace);\n"
                "}\n"
                "function calculateSwimlaneProps(frame, swimlanes) {\n"
                "  const namespace = extractNamespace(frame.entityIdentifier);\n"
                "  const sw = findSwimlaneByNamespace(swimlanes, namespace);\n"
                "  switch (frame.modelEntityType) {\n"
                "    case \"ui\":\n"
                "    case \"pcr\":\n"
                "    case \"processor\":\n"
                "      if (sw) {\n"
                "        return {\n"
                "          index: sw.index,\n"
                "          label: sw.namespace || diagramProps.labelUiAutomation\n"
                "        };\n"
                "      } else if (namespace) {\n"
                "        return {\n"
                "          index: findNextAvailableIndex(swimlanes, 0, 100),\n"
                "          label: diagramProps.labelUiAutomationPrefix + namespace\n"
                "        };\n"
                "      }\n"
                "      return { index: 0, label: diagramProps.labelUiAutomation };\n"
                "    case \"rmo\":\n"
                "    case \"readmodel\":\n"
                "    case \"cmd\":\n"
                "    case \"command\":\n"
                "      if (sw) {\n"
                "        return {\n"
                "          index: sw.index,\n"
                "          label: sw.namespace || diagramProps.labelCommandReadModel\n"
                "        };\n"
                "      } else if (namespace) {\n"
                "        return {\n"
                "          index: findNextAvailableIndex(swimlanes, 100, 200),\n"
                "          label: diagramProps.labelCommandReadModelPrefix + namespace\n"
                "        };\n"
                "      }\n"
                "      return { index: 100, label: diagramProps.labelCommandReadModel };\n"
                "    case \"evt\":\n"
                "    case \"event\":\n"
                "    default:\n"
                "      if (sw) {\n"
                "        return {\n"
                "          index: sw.index,\n"
                "          label: sw.namespace || diagramProps.labelEvents\n"
                "        };\n"
                "      } else if (namespace) {\n"
                "        return {\n"
                "          index: findNextAvailableIndex(swimlanes, 200, 300),\n"
                "          label: diagramProps.labelEventsPrefix + namespace\n"
                "        };\n"
                "      }\n"
                "      return { index: 200, label: diagramProps.labelEvents };\n"
                "  }\n"
                "}\n"
                "    swimlane = {\n"
                "      index: swimlaneProps.index,\n"
                "      label: swimlaneProps.label,\n"
                "      r: 0,`;\n"
                "const first = applySwimlaneFix(broken);\n"
                "if (first.status !== 'patched') throw new Error(first.status);\n"
                "if (!first.text.includes('boundaryMin, boundaryMax')) throw new Error('no band match');\n"
                "if (!first.text.includes('namespace: swimlaneProps.namespace')) throw new Error('no store');\n"
                "const second = applySwimlaneFix(first.text);\n"
                "if (second.status !== 'already') throw new Error(second.status);\n"
                "if (applySwimlaneFix('flowchart TD').status !== 'absent') throw new Error('absent');\n"
            )
            probe_run = subprocess.run(
                [str(repo / "scripts/event-model/node_modules/.bin/tsx"), str(probe)],
                cwd=repo / "scripts/event-model", text=True, capture_output=True,
            )
            self.assertEqual(probe_run.returncode, 0, probe_run.stderr + probe_run.stdout)

    def test_the_two_bands_are_namespaced_independently(self) -> None:
        """The reference diagram's shape: actors naming the top lanes and streams naming the bottom ones,
        in one picture. Also the fallbacks — a guarded slice takes its context, and a model written with
        the old `actorLanes` keeps the one band it used to group."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "banded-lanes")
            model = repo / "docs/event-model/model.yaml"
            header = model.read_text().split("slices:")[0]
            slices = (
                "slices:\n"
                "  - id: S1\n    name: Place an order\n    pattern: state-change\n    status: modelled\n"
                "    actor: Guest\n    stream: order-{orderId}\n"
                "    frames:\n      - {type: ui, name: CheckoutScreen}\n"
                "      - {type: cmd, name: PlaceOrder}\n      - {type: evt, name: OrderPlaced}\n"
                "  - id: S2\n    name: Take payment\n    pattern: automation\n    status: modelled\n"
                "    actor: PaymentProcessor\n    context: billing\n    reads: [OrderPlaced]\n"
                "    materialisation: async\n"
                "    guard:\n      by: [order]\n      because: an order is charged once\n"
                "    frames:\n      - {type: rmo, name: Unpaid}\n      - {type: pcr, name: ChargeOnPlaced}\n"
                "      - {type: cmd, name: Charge}\n      - {type: evt, name: Charged}\n"
            )
            install = subprocess.run(
                ["npm", "--prefix", str(repo / "scripts/event-model"), "install",
                 "--no-audit", "--no-fund", "--loglevel=error"],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            emit = repo / "scripts/event-model/probe-lanes.mts"
            emit.write_text(
                "import { renderGlobalMermaid } from './mermaid.ts';\n"
                "import { loadModel } from './workspace.ts';\n"
                "console.log(renderGlobalMermaid(loadModel()));\n"
            )

            def render(render_block: str) -> str:
                model.write_text(render_block + slices)
                done = subprocess.run(
                    [str(repo / "scripts/event-model/node_modules/.bin/tsx"), str(emit)],
                    cwd=repo, text=True, capture_output=True,
                )
                self.assertEqual(done.returncode, 0, done.stderr)
                return done.stdout

            # Shipped defaults: the actor names the ui/pcr lane, the stream names the event lane, and the
            # command band stays in one. The stream's placeholder is gone, so every order shares a lane.
            both = render(header)
            self.assertIn("ui Guest.CheckoutScreen", both)
            self.assertIn("pcr PaymentProcessor.ChargeOnPlaced", both)
            self.assertIn("evt order.OrderPlaced", both)
            self.assertIn("cmd PlaceOrder", both)
            self.assertNotIn("cmd order.PlaceOrder", both)
            # S2 guards with tags rather than a stream, so its events fall back to its context.
            self.assertIn("evt billing.Charged", both)

            # Grouping the middle band too, for a model whose contexts are worth seeing all the way down.
            deep = render("version: 1\nrender:\n  lanes:\n    ui: actor\n    data: context\n    events: stream\n")
            self.assertIn("cmd billing.Charge", deep)
            self.assertIn("rmo billing.Unpaid", deep)

            # The name `lanes` replaced still means what it meant: the ui band only, nothing else.
            legacy = render("version: 1\nrender:\n  actorLanes: true\n")
            self.assertIn("ui Guest.CheckoutScreen", legacy)
            self.assertIn("evt OrderPlaced", legacy)
            self.assertNotIn("evt order.OrderPlaced", legacy)

            off = render("version: 1\nrender:\n  actorLanes: false\n")
            self.assertIn("ui CheckoutScreen", off)
            self.assertNotIn("Guest.", off)

            # Both names is a contradiction, and is refused rather than silently ordered.
            model.write_text("version: 1\nrender:\n  actorLanes: true\n  lanes:\n    ui: context\n" + slices)
            clash = subprocess.run(
                [str(repo / "scripts/event-model/node_modules/.bin/tsx"), str(emit)],
                cwd=repo, text=True, capture_output=True,
            )
            self.assertNotEqual(clash.returncode, 0)
            self.assertIn("actorLanes", clash.stderr)
