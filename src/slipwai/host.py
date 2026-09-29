"""Which machine this is, and how a missing tool gets onto it.

The implementation is the project's own `scripts/install-tools.py` (`assets/toolkit/scripts/install-tools.py`),
loaded rather than reimplemented — the same arrangement as the backing-service pruner in `assets.py`. A
generated or adopted project needs to detect the machine and install tools too, on every clone and in every
`./init`, and two copies of the recipes would drift. This module is the factory's name for that file.

`ensure` installs: through the package manager the machine has (`sudo` included, where that manager needs it),
or the publisher's user-level download where no manager is current enough. `install_command` and
`install_hint` only describe, for the refusals that still have to name a line — a region, say, is not a tool.
"""
from __future__ import annotations

import importlib.util
import sys
from types import ModuleType

from .assets import TOOLKIT_ROOT

SOURCE = TOOLKIT_ROOT / "scripts/install-tools.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("delivery_install_tools", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the tool installer from {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    # Registered before it runs: its dataclass looks its own module up by name while being defined.
    sys.modules[spec.name] = module
    # The source sits inside the canonical toolkit, which is read file by file as text; no bytecode beside it.
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


TOOLS = _load()

Host = TOOLS.Host
MANAGERS = TOOLS.MANAGERS
INSTALL = TOOLS.INSTALL
PACKAGES = TOOLS.PACKAGES
FALLBACK = TOOLS.FALLBACK
NAMES = TOOLS.NAMES
system = TOOLS.system
detect = TOOLS.detect
install_command = TOOLS.install_command
install_hint = TOOLS.install_hint
uv_by_uname = TOOLS.uv_by_uname
ensure = TOOLS.ensure
disabled = TOOLS.disabled

# What each language a project builds in needs on the machine, by `backends.py`'s family names and the
# survey's language names, for `generate` and `adopt` to put there before anything tries to build.
TOOLCHAINS: dict[str, tuple[str, ...]] = {
    "typescript": ("node",),
    "javascript": ("node",),
    "python": ("uv",),
    "go": ("go",),
    "java": ("java",),
    "kotlin": ("java",),
}
