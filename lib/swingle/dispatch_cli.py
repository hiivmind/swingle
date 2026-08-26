from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from .dispatch import build_dispatch_context


def _read_json_source(path: str) -> dict[str, Any] | None:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("liveness policy must be a JSON object")
    return value


def add_dispatch_parser(commands, parser_class):
    dispatch = commands.add_parser("dispatch")
    dispatch_commands = dispatch.add_subparsers(dest="dispatch_command", required=True, parser_class=parser_class)
    context = dispatch_commands.add_parser("context")
    context.add_argument("--project", required=True)
    context.add_argument("--role", required=True)
    context.add_argument("--tier", required=True)
    context.add_argument("--provider")
    context.add_argument("--model")
    context.add_argument("--effort")
    context.add_argument("--report-mode", choices=("captured-output", "report-file"))
    context.add_argument("--resume", action="store_true")
    context.add_argument("--liveness-policy-file")


def command_dispatch(args, plugin_root: Path) -> dict[str, Any]:
    explicit_liveness = None
    if args.liveness_policy_file is not None:
        explicit_liveness = _read_json_source(args.liveness_policy_file)
    return build_dispatch_context(
        plugin_root=plugin_root,
        project=Path(args.project),
        role=args.role,
        tier=args.tier,
        provider=args.provider,
        model=args.model,
        effort=args.effort,
        report_mode=args.report_mode,
        resume=args.resume,
        explicit_liveness=explicit_liveness,
    )
