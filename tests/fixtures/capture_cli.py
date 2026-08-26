#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


provider = Path(sys.argv[0]).name
arguments = sys.argv[1:]


def option_value(*names: str) -> str:
    for name in names:
        if name in arguments:
            index = arguments.index(name)
            if index + 1 < len(arguments):
                return arguments[index + 1]
    raise SystemExit(f"{provider}: missing prompt option")


if provider == "agy":
    prompt = option_value("--print", "-p")
elif provider == "copilot":
    prompt = option_value("--prompt", "-p")
elif provider in {"cursor-agent", "opencode"}:
    if not arguments:
        raise SystemExit(f"{provider}: missing positional prompt")
    prompt = arguments[-1]
else:
    raise SystemExit(f"unsupported fake provider: {provider}")

sys.stdout.buffer.write(prompt.encode("utf-8"))
