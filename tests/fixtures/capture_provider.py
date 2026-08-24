#!/usr/bin/env python3
"""Capture one provider prompt transport without changing its bytes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("stdin", "prompt-file", "positional"),
        required=True,
    )
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("prompt", nargs="?")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.mode == "stdin":
        if args.prompt_file is not None or args.prompt is not None:
            raise SystemExit("stdin transport accepts no prompt argument")
        payload = sys.stdin.buffer.read()
    elif args.mode == "prompt-file":
        if args.prompt_file is None or args.prompt is not None:
            raise SystemExit("prompt-file transport requires exactly --prompt-file")
        payload = args.prompt_file.read_bytes()
    else:
        if args.prompt_file is not None or args.prompt is None:
            raise SystemExit("positional transport requires exactly one prompt value")
        payload = args.prompt.encode("utf-8")

    args.capture.parent.mkdir(parents=True, exist_ok=True)
    args.capture.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
