#!/usr/bin/env python3
"""Re-project elected extension guidance without rerunning extension setup."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True
from guidance import ROOT, adopted_extensions, canonical_block, installed_block

HERE = Path(__file__).resolve().parent


def extension_module(key: str) -> ModuleType:
    script = HERE / key / "init.py"
    if not script.is_file():
        raise ValueError(f"{key}: elected extension has no {script.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(f"slipwai_extension_{key.replace('-', '_')}", script)
    if spec is None or spec.loader is None:
        raise ValueError(f"{key}: cannot load {script.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project(check: bool) -> list[str]:
    findings: list[str] = []
    try:
        adopted = adopted_extensions(persist_legacy=not check)
    except (OSError, ValueError) as error:
        return [str(error)]
    for key in adopted:
        try:
            module = extension_module(key)
            canonical = canonical_block(key, module.GUIDANCE)
            if check:
                if installed_block(key) != canonical:
                    findings.append(
                        f"AGENTS.md: the {key} extension block has drifted; run `make agents` "
                        "or `slipwai migrate`"
                    )
            else:
                module.project_guidance()
        except (AttributeError, OSError, ValueError) as error:
            findings.append(str(error))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    findings = project(arguments.check)
    if findings:
        print("\n".join(f"check-extensions: {finding}" for finding in findings), file=sys.stderr)
        return 1
    adopted = adopted_extensions(persist_legacy=False)
    if not adopted:
        print("check-extensions: no extension elected; nothing to project")
    elif arguments.check:
        print(f"check-extensions: {len(adopted)} elected extension block(s) match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
