"""The certificate roots a built keel carries, added to the ones the machine has.

Python verifies an HTTPS answer against the roots it is handed, and a keel built into an executable is
handed what the machine it runs on happens to hold. On Windows that is the system store, and a new Windows
holds almost none of it: the rest are fetched one at a time, the first time a Windows program meets a
certificate that needs one — and Python never asks. So on a machine nobody has browsed on yet, every fetch
the board makes — the language index, Node, Git, an agent's archive — failed with `CERTIFICATE_VERIFY_FAILED:
unable to get local issuer certificate`, and with Node not fetched no agent could be launched either.

The executable therefore carries Mozilla's roots, as the `certifi` package publishes them, and `install`
adds them to every HTTPS request this process makes. Added, not put in place of: the machine's own store is
read first, as before, so a root an organisation installed for its proxy still counts, and `SSL_CERT_FILE`
still names one more. Nothing is set in the environment, so no child of the board is given a bundle it did
not ask for.

`certifi` is in the build's pins and not in the keel's dependencies. A keel installed with pip runs on a
Python somebody installed, with whatever roots that Python has, and imports nothing new: where `certifi` is
not there, `install` does nothing.
"""
from __future__ import annotations

import contextlib
import importlib
import ssl
from pathlib import Path


def carried() -> Path | None:
    """The bundle of roots this keel carries, or None where it carries none."""
    try:
        # By name: it is in the executable's build and nowhere else, so its absence is not a fault.
        certifi = importlib.import_module("certifi")
    except ImportError:
        return None
    bundle = Path(certifi.where())
    return bundle if bundle.is_file() else None


def context(bundle: Path) -> ssl.SSLContext:
    """A verifying context holding the machine's roots and, beside them, the ones in `bundle`. A bundle that
    cannot be read leaves the machine's roots alone, which is what there was before."""
    made = ssl.create_default_context()
    with contextlib.suppress(OSError, ssl.SSLError):
        made.load_verify_locations(cafile=str(bundle))
    return made


def install() -> bool:
    """Have every HTTPS request this process makes without a context of its own verify against the carried
    roots as well. True where there were roots to carry.

    `ssl._create_default_https_context` is the name `http.client` asks for a context by, and the one PEP 476
    gives for changing what a whole process trusts. Every fetch in the keel goes through it — `urlopen` and
    `build_opener` alike — so this is said once, at the door, and no fetch has to remember to say it.
    """
    bundle = carried()
    if bundle is None:
        return False

    def carrying() -> ssl.SSLContext:
        return context(bundle)

    ssl._create_default_https_context = carrying  # type: ignore[assignment]  # noqa: SLF001 — PEP 476's own hook
    return True
