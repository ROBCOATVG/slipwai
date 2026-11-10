#!/usr/bin/env python3
"""Exercise a frozen keel independently of the factory checkout or installed languages."""
from __future__ import annotations

import argparse
import json
import plistlib
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from smoke_distribution import smoke

ROOT = Path(__file__).resolve().parents[1]


def app_binary(app: Path) -> Path:
    """The program inside `Slipwai.app`, or the app itself where it is one file (`slipwai-board.exe`)."""
    return app / "Contents/MacOS/slipwai" if app.suffix == ".app" else app


def wears_icon(app: Path) -> None:
    """The app carries the mark, not PyInstaller's Python icon. On macOS the bundle names `slipwai.icns`
    and carries it; on Windows every picture in `slipwai.ico` is in the executable's icon resources, which
    hold them byte for byte."""
    brand = ROOT / "assets/brand"
    if app.suffix == ".app":
        named = plistlib.loads((app / "Contents/Info.plist").read_bytes()).get("CFBundleIconFile", "")
        carried = app / "Contents/Resources" / named
        wanted = (brand / "slipwai.icns").read_bytes()
        if not named or not carried.is_file() or carried.read_bytes() != wanted:
            raise RuntimeError(f"{app} does not carry assets/brand/slipwai.icns as its icon")
    else:
        icon = (brand / "slipwai.ico").read_bytes()
        executable = app.read_bytes()
        for index in range(struct.unpack_from("<H", icon, 4)[0]):
            size, offset = struct.unpack_from("<II", icon, 6 + 16 * index + 8)
            if icon[offset:offset + size] not in executable:
                raise RuntimeError(f"{app} does not carry assets/brand/slipwai.ico as its icon")
    print(f"app smoke: {app.name} wears the slipwai mark")


def serves(app: Path) -> None:
    """The app, started the way its login service starts it, answers `/board.json`. Not opened with no
    arguments: that is a first launch, which asks to move itself and opens a browser."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryDirectory() as root:
        child = subprocess.Popen([str(app_binary(app)), "bridge", "--serve", "--root", root, "--port", str(port)],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(120):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/board.json", timeout=2) as answer:
                        json.loads(answer.read())
                        print(f"app smoke: {app.name} serves the board")
                        return
                except OSError:
                    time.sleep(0.5)
            raise RuntimeError(f"{app} did not serve the board within a minute")
        finally:
            child.terminate()
            child.wait(timeout=30)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--app", type=Path, help="the app built beside it: Slipwai.app or slipwai-board.exe")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    smoke([str(args.executable.resolve())], version)
    if args.app:
        smoke([str(app_binary(args.app.resolve()))], version)
        wears_icon(args.app.resolve())
        serves(args.app.resolve())


if __name__ == "__main__":
    main()
