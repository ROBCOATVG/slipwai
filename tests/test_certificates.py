"""The roots a built keel carries: added to the machine's, and nothing at all where there are none to add.

A new Windows holds too few roots to verify the language index, Node or GitHub, and Python does not have
Windows fetch the rest, so the executable carries Mozilla's (`slipwai/certificates.py`). What is held here
is the part that can go wrong quietly: that the carried roots are added rather than put in place of the
machine's, that a context still verifies, and that a keel without them is the keel there was before.
"""
from __future__ import annotations

import ssl
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from slipwai import certificates

#: A root made for this test and trusted by nothing: `openssl req -x509`, CN "slipwai test root".
ROOT = """-----BEGIN CERTIFICATE-----
MIIBbjCCARSgAwIBAgIUD4ik5ka2MToR/p8jFOlNY6FsLIYwCgYIKoZIzj0EAwIw
HDEaMBgGA1UEAwwRc2xpcHdhaSB0ZXN0IHJvb3QwIBcNMjYxMTEwMjEyMDQ1WhgP
MjEyNjEwMTcyMTIwNDVaMBwxGjAYBgNVBAMMEXNsaXB3YWkgdGVzdCByb290MFkw
EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAESQ80qjThrNyJSw49Vd7UvWDzzbkek/D+
i9/hMuWfXMwnisL+Jft1dVNXFxLYAKwiXz4dp8lzUArDuUba5l8lE6MyMDAwHQYD
VR0OBBYEFO3uHmiKU1bkqOJ9TOM5/J0y2U0VMA8GA1UdEwEB/wQFMAMBAf8wCgYI
KoZIzj0EAwIDSAAwRQIgBuIsSlAkx1ZhWNw5fpPcFRabX90wRztKGOC/n7IJzikC
IQD+IR+e+fGdUnIOH+KatZ0KrgBXP3n6RbtqrwR/qKRpIA==
-----END CERTIFICATE-----
"""


def names(context: ssl.SSLContext) -> set[str]:
    """The common name of every root a context holds."""
    return {value for held in context.get_ca_certs() for part in held["subject"] for key, value in part
            if key == "commonName"}


class CertificatesTest(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.bundle = Path(folder.name) / "cacert.pem"
        self.bundle.write_text(ROOT, encoding="ascii")
        # `install` changes what the whole process trusts; whatever a test does, the next one starts as it was.
        self.addCleanup(setattr, ssl, "_create_default_https_context", ssl._create_default_https_context)

    def carrying(self, where: Path) -> mock._patch_dict:
        """The keel as the executable is: with a `certifi` whose bundle is at `where`."""
        return mock.patch.dict(sys.modules, {"certifi": types.SimpleNamespace(where=lambda: str(where))})

    def test_a_keel_without_the_package_carries_nothing(self) -> None:
        """A keel installed with pip: `certifi` is the build's, and its absence is not a fault."""
        with mock.patch.dict(sys.modules, {"certifi": None}):
            self.assertIsNone(certificates.carried())

    def test_a_bundle_that_is_not_there_is_not_carried(self) -> None:
        with self.carrying(self.bundle.with_name("gone.pem")):
            self.assertIsNone(certificates.carried())

    def test_the_bundle_the_package_names_is_the_one_carried(self) -> None:
        with self.carrying(self.bundle):
            self.assertEqual(certificates.carried(), self.bundle)

    def test_the_carried_roots_are_added(self) -> None:
        self.assertIn("slipwai test root", names(certificates.context(self.bundle)))

    def test_the_machines_own_roots_are_still_asked_for(self) -> None:
        """Added, not put in place of: a root an organisation installed for its proxy still counts."""
        with mock.patch.object(ssl.SSLContext, "load_default_certs") as asked:
            certificates.context(self.bundle)
        asked.assert_called_once()

    def test_a_context_still_verifies(self) -> None:
        made = certificates.context(self.bundle)
        self.assertEqual(made.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(made.check_hostname)

    def test_a_bundle_that_cannot_be_read_leaves_the_machines_roots(self) -> None:
        self.bundle.write_text("not a certificate\n", encoding="ascii")
        made = certificates.context(self.bundle)
        self.assertEqual(made.verify_mode, ssl.CERT_REQUIRED)
        self.assertNotIn("slipwai test root", names(made))

    def test_installed_every_request_is_given_the_carried_roots(self) -> None:
        with self.carrying(self.bundle):
            self.assertTrue(certificates.install())
        self.assertIn("slipwai test root", names(ssl._create_default_https_context()))

    def test_with_nothing_carried_the_process_is_left_as_it_was(self) -> None:
        before = ssl._create_default_https_context
        with mock.patch.dict(sys.modules, {"certifi": None}):
            self.assertFalse(certificates.install())
        self.assertIs(ssl._create_default_https_context, before)


if __name__ == "__main__":
    unittest.main()
