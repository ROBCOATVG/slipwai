"""What every suite in here needs: a way to generate a project, and a way to expect a refusal.

Not a test module — `unittest discover` collects `test_*.py` only — so this file holds the shared base
class and nothing that asserts anything itself.
"""
from __future__ import annotations

import os
import socket
import subprocess
import unittest
from pathlib import Path

from slipwai.assets import ROOT
from slipwai.catalog import CATALOG
from slipwai.scaffold import NO_MAINTENANCE


def backends_under_test() -> list[str]:
    """The backends this run covers: all of them, or the slice `FACTORY_BACKENDS` names, comma-separated.

    CI holds the matrix in parallel jobs — one per language family — while `make verify` on a laptop still
    walks the whole of it. A name the catalog does not know is an error, not a silently empty slice.
    """
    chosen = os.environ.get("FACTORY_BACKENDS")
    if not chosen:
        return list(CATALOG["backends"])
    names = {name.strip() for name in chosen.split(",") if name.strip()}
    unknown = sorted(names - set(CATALOG["backends"]))
    if unknown:
        raise ValueError(f"FACTORY_BACKENDS names backends the catalog does not have: {', '.join(unknown)}")
    return [name for name in CATALOG["backends"] if name in names]


def default_gateways() -> list[str]:
    """The default gateway, which is the Docker host when a container reaches a port published on it.

    Read from /proc/net/route rather than shelled out to `ip`, which plenty of runner images do not carry —
    a fallback that silently finds nothing is worse than no fallback. Empty on anything but Linux, where
    that file does not exist and there is nothing here to ask.
    """
    try:
        table = Path("/proc/net/route").read_text().splitlines()[1:]
    except OSError:
        return []
    gateways = []
    for line in table:
        fields = line.split()
        # Destination 0.0.0.0 with a gateway that is not: the default route. Both are little-endian hex.
        if len(fields) > 2 and fields[1] == "00000000" and fields[2] != "00000000":
            gateways.append(socket.inet_ntoa(int(fields[2], 16).to_bytes(4, "little")))
    return gateways


def commit_all(repo: Path, message: str) -> None:
    """Stage and commit everything, without the detached `git maintenance` a plain commit launches — its
    lock lands in .git/objects/ after the commit returns, which is what tearing the directory down next trips
    over ("Directory not empty")."""
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@local", *NO_MAINTENANCE, "commit", "-q", "-m", message],
        cwd=repo, check=True,
    )


class FactoryTestCase(unittest.TestCase):
    """A test that can scaffold a project the way a caller would: through `./slipwai generate`."""

    def generate(
        self,
        parent: str | Path,
        name: str,
        profile: str = "event-modelling",
        language: str = "typescript",
        frontend: str = "none",
        **axes: str,
    ) -> Path:
        """Generate a project. Axis answers are passed by name — `event_store="postgres"`, `http="fastify"`,
        `auth="keycloak"` — and any axis left unnamed keeps its catalog default. `target="none"` passes the
        production target the same way."""
        arguments = [
            str(ROOT / "slipwai"),
            "generate",
            name,
            "--profile",
            profile,
            "--backend",
            language,
            "--frontend",
            frontend,
            "--output",
            str(parent),
            # The suites are about what is generated, not about the machine running them; the check that
            # a target's tools are present has its own test, which calls `slipwai generate` directly.
            "--skip-checks",
        ]
        for axis, answer in axes.items():
            arguments += [f"--{axis.replace('_', '-')}", answer]
        subprocess.run(arguments, check=True)
        return Path(parent) / name

    @staticmethod
    def settings(text: str, comment: str = "#") -> str:
        """The file with its comment lines removed.

        These files carry long explanations — including of the very keys they deliberately do not set — so
        a plain substring check against the whole text passes on the prose and proves nothing.
        """
        return "\n".join(
            line for line in text.splitlines() if not line.strip().startswith(comment)
        )

    def refuse(self, parent: str | Path, name: str, **options: str) -> str:
        """Generate and expect a refusal, returning what it said."""
        arguments = [str(ROOT / "slipwai"), "generate", name, "--output", str(parent)]
        for key, value in options.items():
            arguments += [f"--{key.replace('_', '-')}", value]
        result = subprocess.run(arguments, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse((Path(parent) / name).exists(), "a refused generation left a directory behind")
        return result.stderr
