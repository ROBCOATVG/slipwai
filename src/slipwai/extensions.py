"""What an extension is: an optional dev-tooling hook `./init --extension <key>` can run.

Unlike an axis, an extension is not a product-architecture choice — it never changes the generated
skeleton's code, so it carries none of an axis's per-backend or per-target matrix. It is answered later than
generation too: at `./init` time, the same moment a Spec Kit agent integration is chosen, rather than baked
into `apps`/`Selection` at `slipwai generate` time. A second extension is a `catalog.json` entry plus an
`assets/toolkit/scripts/extensions/<key>/init.sh` — see `docs/extensions.md` for the contract `init.sh`
must meet.
"""
from __future__ import annotations

REQUIRED = ("name", "description")
OPTIONAL_STRINGS = ("ignore",)


def validate_extensions(catalog: dict) -> None:
    """Every extension declares a name and a description; `ignore`, if present, is gitignore text."""
    extensions = catalog.get("extensions", {})
    if not isinstance(extensions, dict):
        raise ValueError("catalog extensions must be an object")
    for key, spec in extensions.items():
        if not isinstance(spec, dict):
            raise ValueError(f"extensions/{key} must be an object")
        for field in REQUIRED:
            if not isinstance(spec.get(field), str) or not spec[field]:
                raise ValueError(f"extensions/{key} must declare a non-empty {field}")
        for field in OPTIONAL_STRINGS:
            if field in spec and not isinstance(spec[field], str):
                raise ValueError(f"extensions/{key}.{field} must be a string")
        unknown = set(spec) - set(REQUIRED) - set(OPTIONAL_STRINGS)
        if unknown:
            raise ValueError(f"extensions/{key} declares unknown field(s): {', '.join(sorted(unknown))}")


def known_extensions(catalog: dict) -> dict:
    """The catalog's `extensions`, keyed the way `init_script.py`/`gitignore.py` read them."""
    return catalog.get("extensions", {})
