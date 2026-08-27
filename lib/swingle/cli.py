from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .config import (
    init_config,
    load_config,
    resolve_config_path,
    set_config_value,
)
from .grounding_cli import add_grounding_parser, command_grounding
from .dispatch_cli import add_dispatch_parser, command_dispatch
from .errors import SwingleError
from .ledger_cli import (
    command_allocate,
    command_begin_direct,
    command_finalize,
    command_finish_direct,
    command_record,
    command_show,
    command_start,
    command_validate,
)
from .ledger_schema import STATUSES
from .providers import discover_provider_ids


class _ArgumentError(ValueError):
    pass


class _JsonArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        raise _ArgumentError(message)


ARGUMENT_PARSER = _JsonArgumentParser


def _absolute(path: Path | None) -> str | None:
    return str(path.expanduser().resolve()) if path is not None else None


def _provider_ids(root: Path) -> set[str]:
    providers = root / "providers"
    return discover_provider_ids(root) if providers.is_dir() else set()


def _emit(payload: Any, status: int = 0) -> int:
    if isinstance(payload, str):
        print(payload, end="" if payload.endswith("\n") else "\n")
    else:
        if status == 0:
            payload.setdefault("errors", [])
        print(json.dumps(payload, sort_keys=True))
    return status

def _error(error: Exception | str) -> int:
    payload: dict[str, Any] = {"errors": [str(error)]}
    if isinstance(error, SwingleError):
        payload["code"] = error.code
    return _emit(payload, 1)

def _config_init(args: argparse.Namespace) -> int:
    try:
        if args.user:
            path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "swingle" / "config.json"
        elif args.project is not None:
            path = Path(args.project).expanduser() / ".swingle.json"
        else:
            path = Path(args.path).expanduser()
        init_config(path, force=args.force)
        return _emit({"path": _absolute(path), "errors": []})
    except (OSError, ValueError) as error:
        return _error(error)


def _config_show(args: argparse.Namespace) -> int:
    try:
        config_path = Path(args.config).expanduser() if args.config else None
        project_path = Path(args.project).expanduser() if args.project else None
        layer, path = resolve_config_path(config_path, project_path)
        result = load_config(path)
        payload = {
            "layer": layer,
            "path": _absolute(path),
            "config": result.config,
            "warnings": list(result.warnings),
            "errors": list(result.errors),
        }
        return _emit(payload, 1 if result.errors else 0)
    except (OSError, ValueError) as error:
        return _error(error)


def _config_validate(args: argparse.Namespace, default_root: Path) -> int:
    try:
        root = Path(args.root).expanduser() if args.root else default_root
        path = Path(args.path).expanduser()
        result = load_config(path, _provider_ids(root))
        payload = {
            "path": _absolute(path),
            "config": result.config,
            "warnings": list(result.warnings),
            "errors": list(result.errors),
        }
        return _emit(payload, 1 if result.errors else 0)
    except (OSError, ValueError) as error:
        return _error(error)


def _config_set(args: argparse.Namespace, default_root: Path) -> int:
    try:
        root = Path(args.root).expanduser() if args.root else default_root
        path = Path(args.path).expanduser()
        set_config_value(path, args.key, args.json_value, _provider_ids(root))
        return _emit({"path": _absolute(path), "errors": []})
    except (OSError, ValueError) as error:
        return _error(error)


def _parser() -> argparse.ArgumentParser:
    parser = ARGUMENT_PARSER(prog="swingle")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=ARGUMENT_PARSER)

    config = commands.add_parser("config")
    config_commands = config.add_subparsers(dest="config_command", required=True, parser_class=ARGUMENT_PARSER)
    config_init = config_commands.add_parser("init")
    init_targets = config_init.add_mutually_exclusive_group(required=True)
    init_targets.add_argument("--user", action="store_true")
    init_targets.add_argument("--project")
    init_targets.add_argument("--path")
    config_init.add_argument("--force", action="store_true")
    config_show = config_commands.add_parser("show")
    config_show.add_argument("--config")
    config_show.add_argument("--project")
    config_validate = config_commands.add_parser("validate")
    config_validate.add_argument("path")
    config_validate.add_argument("--root")
    config_set = config_commands.add_parser("set")
    config_set.add_argument("--path", required=True)
    config_set.add_argument("key")
    config_set.add_argument("json_value")
    config_set.add_argument("--root")

    ledger = commands.add_parser("ledger")
    ledger_commands = ledger.add_subparsers(dest="ledger_command", required=True, parser_class=ARGUMENT_PARSER)
    start = ledger_commands.add_parser("start")
    start.add_argument("--dir", required=True)
    start.add_argument("--kind", required=True, choices=("direct", "batch", "sdd"))
    start.add_argument("--controller-session-id")
    begin = ledger_commands.add_parser("begin-direct")
    begin.add_argument("--project", required=True)
    begin.add_argument("--dir", required=True)
    begin.add_argument("--controller-session-id")
    begin.add_argument("--role", required=True)
    begin.add_argument("--contract", required=True)
    begin.add_argument("--tier", required=True)
    begin.add_argument("--task", required=True)
    begin.add_argument("--dispatch-context-file", required=True)
    begin.add_argument("--provider", required=True)
    begin.add_argument("--model", required=True)
    begin.add_argument("--effort", required=True)
    allocate = ledger_commands.add_parser("allocate")
    for name in ("project", "dir", "controller-session-id", "run-id", "role", "contract", "tier", "task"):
        allocate.add_argument("--" + name, required=True)
    record = ledger_commands.add_parser("record")
    record_commands = record.add_subparsers(dest="event_type", required=True, parser_class=ARGUMENT_PARSER)

    def record_parser(event: str) -> argparse.ArgumentParser:
        sub = record_commands.add_parser(event)
        for name in ("dir", "controller-session-id", "run-id", "job-id"):
            sub.add_argument("--" + name, required=True)
        return sub

    grounding_observed = record_parser("grounding-observed")
    grounding_reused = record_parser("grounding-reused")
    for sub in (grounding_observed, grounding_reused):
        for name in ("receipt-id", "receipt-revision", "storage", "provider", "cache-path", "grounded-at", "expires-at", "executable", "provider-guidance-sha256", "scopes-file"):
            sub.add_argument("--" + name, required=True)
        sub.add_argument("--model-count", type=int, required=True)
    grounding_observed.add_argument("--evidence-commands-file", required=True)

    dispatched = record_parser("dispatched")
    for name in ("provider", "model", "effort", "liveness-policy-file", "grounding-receipt-id", "grounding-receipt-revision", "grounding-source"):
        dispatched.add_argument("--" + name, required=True)
    dispatched.add_argument("--attempt", type=int, required=True)

    provider_session = record_parser("provider-session")
    provider_session.add_argument("--attempt", type=int, required=True)
    provider_session.add_argument("--provider-session-id", required=True)

    liveness_warning = record_parser("liveness-warning")
    for name in ("process-state", "action"):
        liveness_warning.add_argument("--" + name, required=True)
    liveness_warning.add_argument("--attempt", type=int, required=True)
    liveness_warning.add_argument("--elapsed-seconds", type=float, required=True)
    liveness_warning.add_argument("--silence-seconds", required=True)

    attempt_failed = record_parser("attempt-failed")
    for name in ("signature", "recovery"):
        attempt_failed.add_argument("--" + name, required=True)
    attempt_failed.add_argument("--attempt", type=int, required=True)

    resumed = record_parser("resumed")
    for name in ("provider-session-id", "reason"):
        resumed.add_argument("--" + name, required=True)
    resumed.add_argument("--attempt", type=int, required=True)

    complete = record_parser("complete")
    complete.add_argument("--project", required=True)
    for name in ("status", "outcome", "evidence-file", "completion-file"):
        complete.add_argument("--" + name, required=True)
    record_parser("run-started")
    record_parser("run-completed")
    record_parser("allocated")
    finalize = ledger_commands.add_parser("finalize-run")
    for name in ("project", "dir", "controller-session-id", "run-id"):
        finalize.add_argument("--" + name, required=True)
    finish = ledger_commands.add_parser("finish-direct")
    for name in ("project", "dir", "controller-session-id", "run-id", "job-id", "status", "outcome", "evidence-file", "completion-file"):
        finish.add_argument("--" + name, required=True)
    finish.add_argument("--provider-session-id")
    show = ledger_commands.add_parser("show")
    source = show.add_mutually_exclusive_group(required=True)
    source.add_argument("--dir")
    source.add_argument("--legacy-path")
    show.add_argument("--controller-session-id")
    show.add_argument("--run-id")
    show.add_argument("--job-id")
    show.add_argument("--event")
    show.add_argument("--status", choices=tuple(sorted(STATUSES)))
    show.add_argument("--since")
    show.add_argument("--until")
    show.add_argument("--limit", type=int)
    show.add_argument("--format", choices=("json", "text"), default="json")
    validate = ledger_commands.add_parser("validate")
    validate.add_argument("--dir", required=True)
    validate.add_argument("--controller-session-id")
    add_grounding_parser(commands, ARGUMENT_PARSER)
    add_dispatch_parser(commands, ARGUMENT_PARSER)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    default_root: Path | None = None,
) -> int:
    root = Path(default_root or Path.cwd()).expanduser().resolve()
    try:
        args = _parser().parse_args(argv)
        if args.command == "config":
            if args.config_command == "init":
                return _config_init(args)
            if args.config_command == "show":
                return _config_show(args)
            if args.config_command == "validate":
                return _config_validate(args, root)
            return _config_set(args, root)
        if args.command == "dispatch":
            return _emit(command_dispatch(args, root))
        if args.command == "grounding":
            return _emit(command_grounding(args, root))
        handlers = {
            "start": command_start,
            "begin-direct": command_begin_direct,
            "allocate": command_allocate,
            "record": command_record,
            "finalize-run": command_finalize,
            "finish-direct": command_finish_direct,
            "show": command_show,
            "validate": command_validate,
        }
        return _emit(handlers[args.ledger_command](args))
    except (OSError, ValueError, SwingleError) as error:
        return _error(error)
