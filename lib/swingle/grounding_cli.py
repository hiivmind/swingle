from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .grounding import (
    GROUNDING_SCOPES,
    dispatch_guidance_sha256,
    evaluate_grounding,
    invalidate_grounding,
    record_grounding,
    refresh_grounding,
)
from .liveness import resolve_grounding_ttl


def add_grounding_parser(commands: Any, parser_class: Any) -> None:
    grounding = commands.add_parser("grounding")
    grounding_commands = grounding.add_subparsers(dest="grounding_command", required=True, parser_class=parser_class)
    show = grounding_commands.add_parser("show")
    show.add_argument("--project", required=True)
    show.add_argument("--provider", required=True)
    record = grounding_commands.add_parser("record")
    record.add_argument("--project", required=True)
    record.add_argument("--provider", required=True)
    record.add_argument("--payload-file", required=True)
    invalidate = grounding_commands.add_parser("invalidate")
    invalidate.add_argument("--project", required=True)
    invalidate.add_argument("--provider", required=True)
    invalidate_scopes = invalidate.add_mutually_exclusive_group()
    invalidate_scopes.add_argument("--scope", action="append")
    invalidate_scopes.add_argument("--all", action="store_true")
    invalidate.add_argument("--reason", required=True)
    refresh = grounding_commands.add_parser("refresh")
    refresh.add_argument("--project", required=True)
    refresh.add_argument("--provider", required=True)
    refresh.add_argument("--scope", action="append")
    refresh.add_argument("--reason", required=True)


def _pack_path(provider: str) -> Path:
    return Path(__file__).resolve().parents[2] / "providers" / provider / "pack.md"


def _guidance(provider: str) -> str:
    path = _pack_path(provider)
    if path.exists():
        return dispatch_guidance_sha256(path)
    return "0" * 64


def _project_ttl(project: Path, provider: str) -> int:
    config = load_config(project / ".swingle.json").config
    return resolve_grounding_ttl(config, provider)


def _read_payload(path_value: str) -> dict[str, Any]:
    if path_value == "-":
        import sys
        text = sys.stdin.read()
    else:
        text = Path(path_value).expanduser().read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("grounding payload must be a JSON object")
    return payload


def _show(args: Any) -> dict[str, Any]:
    project = Path(args.project).expanduser()
    result = evaluate_grounding(
        project,
        args.provider,
        provider_guidance_sha256=_guidance(args.provider),
        required_scopes=GROUNDING_SCOPES,
        ttl_seconds=_project_ttl(project, args.provider),
    )
    result["action"] = result["next_action"]
    return result


def command_grounding(args: Any, default_root: Path | None = None) -> dict[str, Any]:
    if args.grounding_command == "show":
        return _show(args)
    if args.grounding_command == "record":
        payload = _read_payload(args.payload_file)
        return record_grounding(Path(args.project).expanduser(), args.provider, payload)
    scopes = None if getattr(args, "all", False) or not args.scope else list(args.scope)
    if args.grounding_command == "invalidate":
        return invalidate_grounding(Path(args.project).expanduser(), args.provider, scopes, args.reason)
    return refresh_grounding(Path(args.project).expanduser(), args.provider, scopes, args.reason)
