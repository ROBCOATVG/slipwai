"""`scripts/agents/try_it.py`: trunk's newest merge, running for a person to use.

The script is copied into a temporary project with a `project.json`, a Compose file, a realm and a git
history, and loaded from there, because where the project is, is where it reads everything from. What is
held is what it would hand the processes it starts, what it would show a person, and what it does with the
example data a slice describes — never Docker, a package manager or a browser, which a suite cannot own.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from slipwai.assets import TOOLKIT_ROOT

SCRIPT = TOOLKIT_ROOT / "scripts/agents/try_it.py"

COMPOSE = """services:
  postgres:
    image: postgres:17-alpine
    ports:
      - '${POSTGRES_PORT:-5433}:5432'
  keycloak:
    image: quay.io/keycloak/keycloak:26.7
    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: boss
      KC_BOOTSTRAP_ADMIN_PASSWORD: secret
    ports:
      - '${KEYCLOAK_PORT:-8081}:8080'
"""

QUICKSTART = """# Quickstart: Slice L18 — Close the record as withdrawn

Synthetic data only.

1. Build with the flag on, then `make dev`.
2. Sign in as Amara Shah, open James Whitfield's record
   (E-101392, Warehouse Supervisor).
3. Press **Close as withdrawn**.

## By route

1. Not a step a person takes.
"""


def git(root: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True, check=True).stdout


class Project(unittest.TestCase):
    """A project with two services, two browser apps, a Compose file, a realm and flags in its code."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()) / "shop"
        place = self.root / "scripts/agents"
        place.mkdir(parents=True)
        (place / "try_it.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        self.manifest({"service": {"kind": "service", "path": "apps/service", "port": 3000,
                                   "selection": {"http": "fastify"}},
                       "worker": {"kind": "service", "path": "apps/worker", "port": 3001,
                                  "selection": {"http": "none"}},
                       "web": {"kind": "web", "path": "apps/web", "port": 5173, "api": "service"},
                       "admin": {"kind": "web", "path": "apps/admin", "port": 5174, "api": "service"}})
        (self.root / "docker-compose.yml").write_text(COMPOSE, encoding="utf-8")
        (self.root / ".env.example").write_text(
            "# a comment\nDATABASE_URL=postgres://app:app@localhost:5433/app\n"
            "USERS_OIDC_ISSUER=http://localhost:8081/realms/customers\nPUBLIC_BASE_URL=http://localhost:3000\n"
            "HR_PARTNER_EMAILS=amara@example.test\n", encoding="utf-8")
        realms = self.root / "docker/keycloak/realms"
        realms.mkdir(parents=True)
        (realms / "customers.json").write_text(json.dumps({"realm": "customers", "users": [
            {"username": "amara@example.test", "firstName": "Amara", "lastName": "Shah",
             "credentials": [{"type": "password", "value": "amara"}]},
            {"username": "gone@example.test", "enabled": False, "credentials": [{"type": "password", "value": "x"}]},
            {"username": "nopass@example.test"}]}), encoding="utf-8")
        source = self.root / "apps/web/src"
        source.mkdir(parents=True)
        (source / "flags.ts").write_text("/**\n * a slice writes `flagEnabled('checkout-v2')`\n */\n",
                                         encoding="utf-8")
        (source / "Record.tsx").write_text(
            "const a = flagEnabled('record-withdrawal');\n// flagEnabled('in-a-comment')\n"
            'const b = flagEnabled("record-corrections") && x;\n', encoding="utf-8")
        self.module = self.load()

    def manifest(self, deployables: dict) -> None:
        (self.root / "project.json").write_text(
            json.dumps({"name": "shop", "frontend": "react-vite", "deployables": deployables}), encoding="utf-8")

    def load(self) -> ModuleType:
        spec = importlib.util.spec_from_file_location("try_it_under_test", self.root / "scripts/agents/try_it.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def history(self) -> tuple[str, str]:
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "one")
        first = git(self.root, "rev-parse", "HEAD").strip()
        place = self.root / "specs/001-shop/slices/L18"
        place.mkdir(parents=True)
        (place / "quickstart.md").write_text(QUICKSTART, encoding="utf-8")
        git(self.root, "add", "specs")
        git(self.root, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "L18")
        return first, git(self.root, "rev-parse", "HEAD").strip()


class TryItTest(Project):
    def test_each_app_gets_the_make_target_and_port_variable_the_makefile_gives_it(self) -> None:
        apps = {app["name"]: app for app in self.module.deployables()}
        self.assertNotIn("worker", apps, "a service with no transport has nothing to serve")
        self.assertEqual((apps["service"]["target"], apps["service"]["variable"]), ("dev", "PORT"))
        self.assertEqual((apps["web"]["target"], apps["web"]["variable"]), ("dev-web", "WEB_PORT"))
        self.assertEqual((apps["admin"]["target"], apps["admin"]["variable"]), ("dev-admin", "WEB_PORT_ADMIN"))

    def test_every_published_port_and_every_address_on_it_is_moved_by_the_offset(self) -> None:
        env = self.module.environment(self.root)
        self.assertEqual((env["POSTGRES_PORT"], env["KEYCLOAK_PORT"], env["PORT"], env["WEB_PORT"]),
                         ("6433", "9081", "4000", "6173"))
        self.assertEqual(env["DATABASE_URL"], "postgres://app:app@localhost:6433/app")
        self.assertEqual(env["USERS_OIDC_ISSUER"], "http://localhost:9081/realms/customers")
        self.assertEqual(env["PUBLIC_BASE_URL"], "http://localhost:4000")
        self.assertEqual(env["HR_PARTNER_EMAILS"], "amara@example.test")
        self.assertEqual(env["COMPOSE_PROJECT_NAME"], "shop-try", "its own containers and its own volumes")

    def test_a_local_env_file_wins_over_the_example_and_is_moved_too(self) -> None:
        (self.root / ".env").write_text("HR_PARTNER_EMAILS=joel@example.test\n"
                                        "USERS_OIDC_ISSUER=http://127.0.0.1:8081/realms/app\n", encoding="utf-8")
        env = self.module.environment(self.root)
        self.assertEqual(env["HR_PARTNER_EMAILS"], "joel@example.test")
        self.assertEqual(env["USERS_OIDC_ISSUER"], "http://127.0.0.1:9081/realms/app")

    def test_the_offset_is_the_one_asked_for(self) -> None:
        import os
        os.environ["TRY_IT_PORT_OFFSET"] = "200"
        try:
            self.assertEqual(self.module.environment(self.root)["WEB_PORT"], "5373")
        finally:
            del os.environ["TRY_IT_PORT_OFFSET"]

    def test_every_flag_the_code_reads_is_on_and_none_a_comment_names(self) -> None:
        self.assertEqual(self.module.flag_keys(self.root), ["record-corrections", "record-withdrawal"])
        env = self.module.environment(self.root)
        self.assertEqual((env["VITE_FLAG_RECORD_WITHDRAWAL"], env["FLAG_RECORD_WITHDRAWAL"]), ("on", "on"))
        self.assertNotIn("VITE_FLAG_CHECKOUT_V2", env)

    def test_a_flag_turned_off_on_the_panel_is_handed_off(self) -> None:
        self.module.HOME.mkdir(parents=True)
        self.module.FLAGS.write_text(json.dumps(["record-withdrawal"]), encoding="utf-8")
        env = self.module.environment(self.root)
        self.assertEqual(env["VITE_FLAG_RECORD_WITHDRAWAL"], "off")
        self.assertEqual(self.module.flag_states(self.root),
                         {"record-corrections": "on", "record-withdrawal": "off"})

    def test_a_declared_flag_is_read_from_where_the_target_declares_it(self) -> None:
        declared = self.root / "infra/service"
        declared.mkdir(parents=True)
        (declared / "flags.auto.tfvars").write_text('flag_new_checkout = "off" # hoisted 2026-01-01\n',
                                                     encoding="utf-8")
        self.assertIn("new-checkout", self.module.flag_keys(self.root))

    def test_the_people_are_the_enabled_fixture_users_with_a_password(self) -> None:
        self.assertEqual(self.module.people(self.root), [
            {"name": "Amara Shah", "username": "amara@example.test", "password": "amara", "realm": "customers"}])

    def test_the_sign_in_server_and_its_admin_are_read_off_the_compose_file(self) -> None:
        self.assertEqual(self.module.keycloak(self.root),
                         {"variable": "KEYCLOAK_PORT", "user": "boss", "password": "secret"})
        (self.root / "docker-compose.yml").write_text(COMPOSE.split("  keycloak:")[0], encoding="utf-8")
        self.assertEqual(self.module.keycloak(self.root), {})

    def test_a_quickstart_is_its_title_and_numbered_steps_up_to_the_next_heading(self) -> None:
        _, commit = self.history()
        found = self.module.things_to_try(commit, "specs/001-shop/slices/L18/quickstart.md")
        self.assertEqual(found["title"], "Close the record as withdrawn")
        self.assertEqual(found["slice"], "L18")
        self.assertEqual(found["steps"], [
            "Build with the flag on, then `make dev`.",
            "Sign in as Amara Shah, open James Whitfield's record (E-101392, Warehouse Supervisor).",
            "Press **Close as withdrawn**."])

    def test_whats_new_is_every_slice_the_first_time_and_only_the_changed_ones_after(self) -> None:
        first, second = self.history()
        self.assertEqual([one["slice"] for one in self.module.whats_new(second, "")], ["L18"])
        self.assertEqual([one["slice"] for one in self.module.whats_new(second, first)], ["L18"])
        self.assertEqual(self.module.whats_new(second, second), [one for one in self.module.whats_new(second, "")])
        git(self.root, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "x")
        third = git(self.root, "rev-parse", "HEAD").strip()
        self.assertEqual(self.module.whats_new(third, second), [])

    def test_a_step_is_filled_from_what_earlier_steps_kept(self) -> None:
        kept = {"record": "r-1", "version": 3}
        self.assertEqual(self.module.filled({"path": "/api/records/{record}/withdrawal", "v": "{version}",
                                             "list": ["{record}"], "left": "{unknown}"}, kept),
                         {"path": "/api/records/r-1/withdrawal", "v": 3, "list": ["r-1"], "left": "{unknown}"})
        self.assertEqual(self.module.picked({"a": {"b": [{"c": "deep"}]}}, "a.b.0.c"), "deep")
        self.assertIsNone(self.module.picked({"a": 1}, "a.b"))

    def test_a_ready_app_whose_process_has_gone_is_said_to_have_failed(self) -> None:
        self.module.write_state({"state": "ready", "pids": {"web": 999999}, "commit": ""})
        found = self.module.status()
        self.assertEqual(found["state"], "failed")
        self.assertIn("web stopped", found["error"])


class SeedTest(Project):
    """The example data, through the API: a fake service and sign-in server stand in for the real ones."""

    def test_each_slice_story_runs_in_order_keeps_what_it_is_told_and_links_its_records(self) -> None:
        story = {"as": "amara@example.test",
                 "open": [{"label": "Priya's record", "path": "/records/{record}"}],
                 "steps": [{"say": "open", "method": "POST", "path": "/api/records", "body": {"n": 1},
                            "keep": {"record": "id"}},
                           {"say": "withdraw", "method": "POST", "path": "/api/records/{record}/withdrawal",
                            "body": {"source": "email"}}]}
        place = self.root / "specs/001-shop/slices/L18"
        place.mkdir(parents=True)
        (place / "try-it.json").write_text(json.dumps(story), encoding="utf-8")
        broken = self.root / "specs/001-shop/slices/L02"
        broken.mkdir(parents=True)
        (broken / "try-it.json").write_text(json.dumps({"as": "amara@example.test", "steps": [
            {"say": "refused", "method": "POST", "path": "/api/nope", "body": {}}]}), encoding="utf-8")
        calls: list[tuple] = []

        def request(method, address, body=None, token="", headers=None):
            calls.append((method, address, body, token, sorted(headers or {})))
            if address.endswith("/api/nope"):
                import io
                import urllib.error
                raise urllib.error.HTTPError(address, 422, "no", {}, io.BytesIO(b'{"error":"invalid"}'))
            return {"id": "r-1"} if address.endswith("/api/records") else None

        self.module.request = request
        self.module.token_for = lambda who, env, where: f"token-for-{who}"
        state: dict = {}
        self.module.seed(self.root, {}, state, only_new=False)
        self.assertEqual(state["seeded"], ["001-shop/L18"])
        self.assertEqual(state["seed_failed"], [{"slice": "001-shop/L02", "step": "refused",
                                                 "said": '422 {"error":"invalid"}'}])
        self.assertEqual(state["links"], [{"slice": "001-shop/L18", "label": "Priya's record",
                                           "path": "/records/r-1"}])
        mine = [call for call in calls if "records" in call[1]]
        self.assertEqual(mine[1][1], "http://localhost:4000/api/records/r-1/withdrawal")
        self.assertEqual(mine[0][3], "token-for-amara@example.test")
        self.assertIn("Idempotency-Key", mine[0][4], "a write carries a key of its own")
        calls.clear()
        self.module.seed(self.root, {}, state, only_new=True)
        self.assertEqual([call[1] for call in calls], ["http://localhost:4000/api/nope"],
                         "a story already loaded is not loaded twice")


if __name__ == "__main__":
    unittest.main()
