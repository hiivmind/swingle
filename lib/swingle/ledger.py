from __future__ import annotations

import fcntl
import os
from pathlib import Path

HEADER = "# Swingle delegation ledger\n\n"


def _locked_file(path: Path, mode: str, lock: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open(mode, encoding="utf-8")
    fcntl.flock(handle.fileno(), lock)
    return handle


def init_ledger(path: Path) -> None:
    handle = _locked_file(path, "a+", fcntl.LOCK_EX)
    try:
        handle.seek(0)
        content = handle.read()
        if not content:
            handle.write(HEADER)
            handle.flush()
            os.fsync(handle.fileno())
        elif not content.startswith(HEADER):
            raise ValueError(f"{path}: invalid Swingle ledger header")
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def append_event(path: Path, event: str) -> None:
    if not event or "\n" in event or "\r" in event:
        raise ValueError("ledger event must be one line and non-empty")
    init_ledger(path)
    handle = _locked_file(path, "a", fcntl.LOCK_EX)
    try:
        handle.write(event + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def read_ledger(path: Path) -> list[str]:
    init_ledger(path)
    handle = _locked_file(path, "r", fcntl.LOCK_SH)
    try:
        lines = handle.read().splitlines()
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    return [line for line in lines[2:] if line]
