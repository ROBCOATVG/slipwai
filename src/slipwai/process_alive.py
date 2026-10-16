"""Whether a process named by a pid file is still running, asked without touching it.

**`os.kill(pid, 0)` is not a question on Windows.** Signal 0 there is `CTRL_C_EVENT`, which is delivered to
every process sharing the console — the board asking whether a captain was alive interrupted the board, and
the test suite that started it, with a `KeyboardInterrupt`. Windows is asked through the process handle
instead, as the toolkit's `fleet.py` already does.
"""
from __future__ import annotations

import os
import sys


def alive(pid: int) -> bool:
    """Whether that process is still running. A process that exited 259 reads as running on Windows, because
    that is `STILL_ACTIVE` and the API cannot tell them apart; nothing here exits 259."""
    if pid <= 0:
        return False
    if sys.platform == "win32":  # pragma: no cover — read on the platform it is for
        import ctypes

        query_limited_information, still_active = 0x1000, 259
        kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel.OpenProcess(query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == still_active
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
