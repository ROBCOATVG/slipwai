"""Try it on the board: the card that says what the project's `try_it.py` is doing, and what a generated
project carries so that there is something for it to do.

The card is read off `.slipwai/try-it/state.json`, the file the script writes, so each case writes that file
and reads the card — never the script, Docker or a browser.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import checkout_packages

from slipwai.assets import BACKING_SERVICE_ROOT
from slipwai.catalog import CATALOG
from slipwai.scaffold import project_files
from slipwai.selection import resolve_selection
from slipwai.services import default_apps
from slipwai.try_card import act, card, card_html, payload, status, walk_file, walks_of


def state_of(root: Path, state: dict) -> None:
    home = root / ".slipwai/try-it"
    home.mkdir(parents=True, exist_ok=True)
    (home / "state.json").write_text(json.dumps(state), encoding="utf-8")


class CardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        (self.root / "project.json").write_text(json.dumps({"layout": {"delivery": "."}}), encoding="utf-8")
        (self.root / "scripts/agents").mkdir(parents=True)
        (self.root / "scripts/agents/try_it.py").write_text("", encoding="utf-8")

    def test_a_project_without_the_script_has_no_card_and_keeps_the_old_link(self) -> None:
        (self.root / "scripts/agents/try_it.py").unlink()
        self.assertEqual(card(self.root), "")
        self.assertEqual(json.loads(payload(self.root))["html"], "")
        with self.assertRaisesRegex(ValueError, "slipwai migrate"):
            act(self.root, "start")

    def test_never_started_is_a_start_button_and_what_it_will_do(self) -> None:
        shown = card(self.root)
        self.assertIn('data-try="start"', shown)
        self.assertIn("every merged slice switched on", shown)
        self.assertIn('class="pill stopped"', shown)

    def test_starting_shows_the_steps_done_and_the_one_under_way(self) -> None:
        state_of(self.root, {"state": "starting", "runner": __import__("os").getpid(), "step": "applying migrations",
                             "steps": ["workspace at abc1234", "applying migrations"]})
        shown = card(self.root)
        self.assertIn("starting · applying migrations", shown)
        self.assertIn("✓ workspace at abc1234\n› applying migrations", shown)
        self.assertEqual(json.loads(payload(self.root))["state"], "starting")

    def test_a_start_whose_runner_has_gone_is_a_failure_that_says_where(self) -> None:
        state_of(self.root, {"state": "starting", "runner": 999999, "step": "installing dependencies"})
        self.assertEqual(status(self.root)["error"], "stopped while installing dependencies")
        self.assertIn('data-try="start"', card(self.root))

    def test_ready_is_the_app_who_to_sign_in_as_its_data_what_to_try_and_its_switches(self) -> None:
        shown = card_html({
            "state": "ready", "url": "http://localhost:6173", "commit": "d3c2e39729bd", "behind": 2,
            "people": [{"name": "Amara Shah", "username": "amara@example.test", "password": "amara"}],
            "seeded": ["001/L01"], "seed_failed": [{"slice": "001/L06", "step": "agree", "said": "422 late"}],
            "links": [{"slice": "001/L01", "label": "Priya Raman's record", "path": "/leaver-records/r-1"}],
            "new": [{"slice": "L18", "title": "Close as withdrawn", "steps": ["Press <b>Close</b>"]}],
            "previous": "abc", "flags": {"leaver-record-withdrawal": "on", "leaver-record-corrections": "off"}})
        self.assertIn('href="http://localhost:6173"', shown)
        self.assertIn('data-try="refresh"', shown, "trunk has moved, so it can be brought up to date")
        self.assertIn("2 newer commits on trunk", shown)
        self.assertIn("<code>amara@example.test</code>", shown)
        self.assertIn('href="http://localhost:6173/leaver-records/r-1" target="try-it-app"', shown,
                      "every link into the app opens in the one tab a person signed in to")
        self.assertNotIn('target="_blank"', shown.split("Watch it work")[0])
        self.assertIn("agree: 422 late", shown)
        self.assertIn("New since the last update · 1", shown)
        self.assertIn("Press &lt;b&gt;Close&lt;/b&gt;", shown, "a quickstart's words are text, never markup")
        self.assertIn("1 of 2 switches on", shown)
        self.assertIn('data-key="leaver-record-withdrawal" data-value="off"', shown)

    def test_the_example_data_is_grouped_under_who_to_sign_in_as_and_the_rest_are_listed(self) -> None:
        people = [{"name": "Amara Shah", "username": "amara@example.test", "password": "amara"},
                  {"name": "Joel Mensah", "username": "joel@example.test", "password": "joel"},
                  {"name": "Sam Lee", "username": "sam@example.test", "password": "sam"}]
        shown = card_html({
            "state": "ready", "url": "http://localhost:6173", "commit": "f5784e0", "people": people,
            "links": [{"slice": "001/L18", "label": "James's record", "path": "/r/1", "as": "amara@example.test"},
                      {"slice": "001/L02", "label": "Grace's record", "path": "/r/2", "as": "joel@example.test"},
                      {"slice": "001/L07", "label": "Sofia's record", "path": "/r/3", "as": "amara@example.test"}],
            "new": [{"slice": "L18", "title": "Close as withdrawn", "steps": [], "as": "amara@example.test"}]})
        amara = shown.index("Sign in as <b>Amara Shah</b> · <code>amara@example.test</code> · password "
                            "<code>amara</code>")
        joel = shown.index("Sign in as <b>Joel Mensah</b>")
        self.assertLess(amara, shown.index("James&#x27;s record"))
        self.assertLess(shown.index("Sofia&#x27;s record"), joel, "one person's records together, under them")
        self.assertLess(joel, shown.index("Grace&#x27;s record"))
        self.assertIn("Also there to sign in as", shown)
        self.assertIn("<b>Sam Lee</b>", shown.split("Also there to sign in as")[1])
        self.assertNotIn("<b>Amara Shah</b>", shown.split("Also there to sign in as")[1].split("</table>")[0])
        self.assertIn("Close as withdrawn</b> <span class=\"empty\">· sign in as Amara Shah</span>", shown)

    def test_ready_and_current_offers_no_update(self) -> None:
        shown = card_html({"state": "ready", "url": "http://localhost:6173", "commit": "d3c2e39", "behind": 0})
        self.assertNotIn('data-try="refresh"', shown)
        self.assertIn("up to date", shown)

    def test_a_ready_app_whose_process_has_gone_is_a_failure(self) -> None:
        state_of(self.root, {"state": "ready", "pids": {"service": 999999}, "commit": ""})
        found = status(self.root)
        self.assertEqual(found["state"], "failed")
        self.assertIn("service stopped", found["error"])

    def test_behind_counts_the_commits_trunk_has_made_since_it_started(self) -> None:
        def git(*argv: str) -> str:
            return subprocess.run(["git", "-C", str(self.root), "-c", "user.email=a@b", "-c", "user.name=a",
                                   *argv], capture_output=True, text=True, check=True).stdout.strip()
        git("init", "-q", "-b", "main")
        git("commit", "-q", "--allow-empty", "-m", "one")
        started = git("rev-parse", "HEAD")
        git("commit", "-q", "--allow-empty", "-m", "two")
        git("commit", "-q", "--allow-empty", "-m", "three")
        state_of(self.root, {"state": "stopped", "commit": started})
        self.assertEqual(status(self.root)["behind"], 2)

    def test_the_walks_the_demo_hand_recorded_are_listed_by_slice_and_served_from_their_folder(self) -> None:
        home = self.root / ".slipwai/walks/001-shop/L18"
        home.mkdir(parents=True)
        (home / "l18-1.webm").write_bytes(b"video")
        (home / "notes.md").write_text("not a video", encoding="utf-8")
        (self.root / ".slipwai/secret.webm").write_bytes(b"outside")
        found = walks_of(self.root, "hVn0")
        self.assertEqual([(one["slice"], one["example"]) for one in found], [("L18", "l18-1")])
        self.assertTrue(found[0]["href"].startswith("/walks/001-shop/L18/l18-1.webm?seat=hVn0&v="))
        self.assertIn("Watch it work · 1 walked example", card(self.root, "hVn0"))
        self.assertEqual(walk_file(self.root, "001-shop/L18/l18-1.webm"), (home / "l18-1.webm").resolve())
        for refused in ("001-shop/L18/notes.md", "001-shop/../secret.webm", "../../.slipwai/secret.webm",
                        "001-shop/L18"):
            self.assertIsNone(walk_file(self.root, refused), refused)

    def test_only_its_own_verbs_are_handed_on(self) -> None:
        with self.assertRaisesRegex(ValueError, "no 'rm'"):
            act(self.root, "rm")
        with self.assertRaisesRegex(ValueError, "on or off"):
            act(self.root, "flag", "x", "maybe")


class GeneratedTest(unittest.TestCase):
    """What a generated project carries for Try it to run."""

    def test_a_project_with_an_app_has_the_try_targets_and_ignores_the_state(self) -> None:
        selection = resolve_selection({"persistence": "postgres"}, "event-modelling", "toy-plain", "none")
        files = project_files("shop", "event-modelling", "none", default_apps("toy-plain", "none", selection))
        makefile = files["Makefile"]
        for target in ("try", "try-update", "try-fresh", "try-stop"):
            self.assertIn(f"\n{target}: ## ", makefile)
        self.assertIn(".PHONY: try try-update try-fresh try-stop", makefile)
        self.assertIn("python3 scripts/agents/try_it.py start", makefile)
        self.assertIn(".slipwai/try-it/\n", files[".gitignore"])
        self.assertIn(".slipwai/walks/\n", files[".gitignore"])
        self.assertIn("scripts/agents/try_it.py", files)

    @unittest.skipUnless(checkout_packages.installed("typescript"), "the browser app is written with TypeScript's")
    def test_the_browser_app_listens_where_try_it_tells_it(self) -> None:
        selection = resolve_selection({"persistence": "postgres", "http": "fastify"}, "event-modelling",
                                      "typescript", "none")
        files = project_files("shop", "event-modelling", "none", default_apps("typescript", "react-vite", selection))
        self.assertIn("port: Number.parseInt(process.env.WEB_PORT ?? '', 10) || 5173,",
                      files["apps/web/vite.config.ts"],
                      "the dev server listens where Try it tells it to, and on its own port otherwise")

    def test_every_client_a_browser_signs_in_through_issues_a_subject(self) -> None:
        """Keycloak 25 moved `sub` into the `basic` scope; a client that lists its scopes without it issues
        tokens a service keyed on `sub` refuses."""
        for path in (BACKING_SERVICE_ROOT / "keycloak/realms").glob("*.json"):
            for client in json.loads(path.read_text(encoding="utf-8")).get("clients") or []:
                scopes = client.get("defaultClientScopes")
                if scopes is not None and client.get("redirectUris"):
                    self.assertIn("basic", scopes, f"{path.name}: {client['clientId']}")
        self.assertTrue(CATALOG)


if __name__ == "__main__":
    unittest.main()
