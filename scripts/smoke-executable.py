#!/usr/bin/env python3
"""Exercise a frozen keel independently of the factory checkout or installed languages."""
from __future__ import annotations

import argparse
import json
import socket
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
        serves(args.app.resolve())


if __name__ == "__main__":
    main()
