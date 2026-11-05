"""A declared person signs in by the name their realm stores, which is the email where the realm says so.

recap's customers realm sets `registrationEmailAsUsername`, so Keycloak stored a person declared as `ines` under
her email: every story signed in as `ines` was refused `invalid_grant`, and the next start looked her up as
`ines`, found nobody, created her again and was refused 409.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

import checkout_packages  # noqa: F401

from slipwai.assets import TOOLKIT_ROOT

SCRIPT = TOOLKIT_ROOT / "scripts/agents/try_it.py"


def load() -> Any:
    spec = importlib.util.spec_from_file_location("try_it_sign_in", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SignInTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.module = load()
        (self.root / "docker/keycloak/realms").mkdir(parents=True)
        (self.root / "specs/001-demo/people").mkdir(parents=True)
        (self.root / "specs/001-demo/people/ines.json").write_text(json.dumps(
            {"username": "ines", "name": "Ines Listener", "password": "p", "realm": "customers",
             "email": "ines@example.invalid"}), encoding="utf-8")

    def realm(self, **settings: object) -> None:
        (self.root / "docker/keycloak/realms/customers.json").write_text(
            json.dumps({"realm": "customers", **settings}), encoding="utf-8")

    def ines(self) -> dict:
        return next(one for one in self.module.people(self.root) if one["username"] == "ines")

    def test_a_realm_that_makes_the_email_the_username_signs_her_in_by_email(self) -> None:
        self.realm(registrationEmailAsUsername=True)
        self.assertEqual(self.ines()["sign_in"], "ines@example.invalid")
        self.assertEqual(self.ines()["username"], "ines", "the story keeps the name it signs in as")

    def test_any_other_realm_signs_her_in_by_her_username(self) -> None:
        self.realm()
        self.assertEqual(self.ines()["sign_in"], "ines")


if __name__ == "__main__":
    unittest.main()
