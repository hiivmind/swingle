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
from .ledger import append_event, init_ledger, read_ledger
from .providers import discover_provider_ids


class _ArgumentError(ValueError):
    pass


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentError(message)


ARGUMENT_PARSER = _JsonArgumentParser


def _absolute(path: Path | None) -> str | None:
    return str(path.expanduser().resolve()) if path is not None else None


def _provider_ids(root: Path) -> set[str]:
    providers = root / "providers"
    return discover_provider_ids(root) if providers.is_dir() else set()


def _emit(payload: dict[str, Any], status: int = 0) -> int:
    print(json.dumps(payload, sort_keys=True))
    return status


def _error(error: Exception | str) -> int:
    return _emit({"errors": [str(error)]}, 1)


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


def _ledger_init(args: argparse.Namespace) -> int:
    try:
        path = Path(args.path).expanduser()
        init_ledger(path)
        return _emit({"path": _absolute(path), "errors": []})
    except (OSError, ValueError) as error:
        return _error(error)


def _ledger_append(args: argparse.Namespace) -> int:
    try:
        path = Path(args.path).expanduser()
        append_event(path, args.event)
        return _emit({"path": _absolute(path), "errors": []})
    except (OSError, ValueError) as error:
        return _error(error)


def _ledger_show(args: argparse.Namespace) -> int:
    try:
        path = Path(args.path).expanduser()
        return _emit({"path": _absolute(path), "events": read_ledger(path), "errors": []})
    except (OSError, ValueError) as error:
        return _error(error)


def _parser() -> argparse.ArgumentParser:
    parser = ARGUMENT_PARSER(prog="swingle")
    commands = parser.add_subparsers(
        dest="command", required=True, parser_class=ARGUMENT_PARSER
    )

    config = commands.add_parser("config")
    config_commands = config.add_subparsers(
        dest="config_command", required=True, parser_class=ARGUMENT_PARSER
    )

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
    ledger_commands = ledger.add_subparsers(
        dest="ledger_command", required=True, parser_class=ARGUMENT_PARSER
    )

    ledger_init = ledger_commands.add_parser("init")
    ledger_init.add_argument("--path", required=True)

    ledger_append = ledger_commands.add_parser("append")
    ledger_append.add_argument("--path", required=True)
    ledger_append.add_argument("event")

    ledger_show = ledger_commands.add_parser("show")
    ledger_show.add_argument("--path", required=True)

    return parser

def main(
    argv: list[str] | None = None,
    *,
    default_root: Path | None = None,
) -> int:
    root = Path(default_root or Path.cwd()).expanduser().resolve()
    try:
        args = _parser().parse_args(argv)
    except _ArgumentError as error:
        return _error(error)
    if args.command == "config":
        if args.config_command == "init":
            return _config_init(args)
        if args.config_command == "show":
            return _config_show(args)
        if args.config_command == "validate":
            return _config_validate(args, root)
        return _config_set(args, root)
    if args.ledger_command == "init":
        return _ledger_init(args)
    if args.ledger_command == "append":
        return _ledger_append(args)
    return _ledger_show(args)
