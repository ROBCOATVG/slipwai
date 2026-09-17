#!/usr/bin/env python3
"""Create a platform-labelled release archive and SHA-256 checksum."""

from __future__ import annotations

import argparse
import hashlib
import platform
import tarfile
import zipfile
from pathlib import Path


def platform_label() -> tuple[str, str]:
    system = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    if system is None:
        raise RuntimeError(f"unsupported release platform: {platform.system()}")
    machine = platform.machine().lower()
    architecture = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine)
    if architecture is None:
        raise RuntimeError(f"unsupported release architecture: {machine}")
    return system, architecture


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path, default=Path("release"))
    args = parser.parse_args()
    executable = args.executable.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    system, architecture = platform_label()
    stem = f"slipwai-{system}-{architecture}"

    if system == "windows":
        archive = args.output / f"{stem}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(executable, arcname=executable.name)
    else:
        archive = args.output / f"{stem}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(executable, arcname="slipwai")

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{digest}  {archive.name}\n")
    print(archive)
    print(checksum)


if __name__ == "__main__":
    main()
