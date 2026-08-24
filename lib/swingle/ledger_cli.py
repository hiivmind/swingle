from __future__ import annotations

import heapq
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

from .errors import LedgerLifecycleError, LedgerValidationError
from .ledger import (
    allocate_job,
    begin_direct,
    finalize_run,
    finish_direct,
    record_event,
    start_run,
)
_UUID_FILENAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.ndjson$")
_LEGACY_HEADER = "# Swingle delegation ledger\n\n"
from .ledger_schema import EVENTS, STATUSES, validate_event


def _path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _json_value(path: str | Path) -> Any:
    if str(path) == "-":
        text = sys.stdin.read()
    else:
        text = _path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerValidationError(f"invalid JSON input: {path}") from exc


def _json_file(path: str | Path, expected: type | tuple[type, ...] | None = None) -> Any:
    value = _json_value(path)
    if expected is not None and not isinstance(value, expected):
        raise LedgerValidationError(f"JSON input {path} has the wrong container type")
    return value


def _required(args: Any, *names: str) -> None:
    missing = [name for name in names if getattr(args, name, None) is None]
    if missing:
        raise LedgerValidationError(f"missing required flags: {', '.join('--' + name.replace('_', '-') for name in missing)}")


def _nullable(value: str | None) -> Any:
    if value is None or value == "null":
        return None
    return value


def _nullable_int(value: str | None) -> int | None:
    if value is None or value == "null":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise LedgerValidationError(f"invalid integer: {value}") from exc


def _result(path: Path, events: Iterable[dict[str, Any]], **ids: str | Path | None) -> dict[str, Any]:
    output: dict[str, Any] = {"ledger_file": str(path.resolve()), "ledger_path": str(path.resolve()), "path": str(path.resolve()), "events": list(events)}
    for key, value in ids.items():
        if value is not None:
            output[key] = str(value)
    if output["events"]:
        output["event"] = output["events"][-1]
    return output


def command_start(args: Any) -> dict[str, Any]:
    _required(args, "dir", "kind")
    result = start_run(_path(args.dir), args.kind, args.controller_session_id)
    return _json_paths(result)


def command_allocate(args: Any) -> dict[str, Any]:
    _required(args, "project", "dir", "controller_session_id", "run_id", "role", "contract", "tier", "task")
    return _json_paths(allocate_job(project=_path(args.project), ledger_dir=_path(args.dir), controller_session_id=args.controller_session_id, run_id=args.run_id, role=args.role, contract=args.contract, tier=args.tier, task=args.task))


def _grounding_data(args: Any, event: str) -> dict[str, Any]:
    _required(args, "receipt_id", "receipt_revision", "storage", "provider", "cache_path", "grounded_at", "expires_at", "executable", "provider_guidance_sha256", "scopes_file", "model_count")
    data: dict[str, Any] = {
        "receipt_id": _nullable(args.receipt_id),
        "receipt_revision": _nullable_int(args.receipt_revision),
        "storage": args.storage,
        "provider": args.provider,
        "cache_path": _nullable(args.cache_path),
        "grounded_at": args.grounded_at,
        "expires_at": _nullable(args.expires_at),
        "executable": args.executable,
        "provider_guidance_sha256": args.provider_guidance_sha256,
        "scopes": _json_file(args.scopes_file, list),
        "model_count": args.model_count,
    }
    if event == "grounding-observed":
        _required(args, "evidence_commands_file")
        data["evidence_commands"] = _json_file(args.evidence_commands_file, list)
    return data


def _completion(args: Any) -> dict[str, Any]:
    _required(args, "completion_file")
    value = _json_file(args.completion_file, dict)
    provider = value.get("provider_outcome", value.get("provider"))
    repository = value.get("repository_verification", value.get("repository"))
    if not isinstance(provider, dict) or not isinstance(repository, dict):
        raise LedgerValidationError("completion JSON must contain provider_outcome and repository_verification")
    return {"provider_outcome": provider, "repository_verification": repository}

def _evidence(args: Any) -> list[dict[str, Any]]:
    _required(args, "evidence_file")
    return _json_file(args.evidence_file, list)


def command_begin_direct(args: Any) -> dict[str, Any]:
    _required(args, "project", "dir", "role", "contract", "tier", "task", "dispatch_context_file", "provider", "model", "effort")
    context = _json_file(args.dispatch_context_file, dict)
    result = begin_direct(project=_path(args.project), ledger_dir=_path(args.dir), controller_session_id=args.controller_session_id, role=args.role, contract=args.contract, tier=args.tier, task=args.task, provider=args.provider, model=args.model, effort=args.effort, dispatch_context=context)
    return _json_paths(result)


def command_record(args: Any) -> dict[str, Any]:
    event = args.event_type
    if event == "run-completed":
        raise LedgerLifecycleError("run-completed is emitted only by ledger finalize-run")
    if event not in EVENTS or event == "run-started" or event == "allocated":
        raise LedgerValidationError(f"unsupported record event {event!r}")
    _required(args, "dir", "controller_session_id", "run_id", "job_id")
    data: dict[str, Any]
    if event in {"grounding-observed", "grounding-reused"}:
        data = _grounding_data(args, event)
    elif event == "dispatched":
        _required(args, "provider", "model", "effort", "attempt", "liveness_policy_file", "grounding_receipt_id", "grounding_receipt_revision", "grounding_source")
        data = {"provider": args.provider, "model": args.model, "effort": args.effort, "attempt": args.attempt, "liveness_policy": _json_file(args.liveness_policy_file, dict), "grounding_receipt_id": args.grounding_receipt_id, "grounding_receipt_revision": _nullable_int(args.grounding_receipt_revision), "grounding_source": args.grounding_source}
    elif event == "provider-session":
        _required(args, "attempt", "provider_session_id")
        data = {"attempt": args.attempt, "provider_session_id": args.provider_session_id}
    elif event == "liveness-warning":
        _required(args, "attempt", "elapsed_seconds", "silence_seconds", "process_state", "action")
        data = {"attempt": args.attempt, "elapsed_seconds": args.elapsed_seconds, "silence_seconds": _nullable_float(args.silence_seconds), "process_state": args.process_state, "action": args.action}
    elif event == "attempt-failed":
        _required(args, "attempt", "signature", "recovery")
        data = {"attempt": args.attempt, "signature": args.signature, "recovery": args.recovery}
    elif event == "resumed":
        _required(args, "attempt", "provider_session_id", "reason")
        data = {"attempt": args.attempt, "provider_session_id": args.provider_session_id, "reason": args.reason}
    elif event == "complete":
        _required(args, "status", "outcome", "evidence_file", "completion_file")
        completion = _completion(args)
        data = {"status": args.status, "outcome": args.outcome, "evidence": _evidence(args), **completion}
    else:
        raise LedgerValidationError(f"unsupported record event {event!r}")
    return _json_paths(record_event(ledger_dir=_path(args.dir), controller_session_id=args.controller_session_id, run_id=args.run_id, event=event, data=data, job_id=args.job_id))


def _nullable_float(value: str | None) -> float | None:
    if value is None or value == "null":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise LedgerValidationError(f"invalid number: {value}") from exc


def command_finish_direct(args: Any) -> dict[str, Any]:
    _required(args, "dir", "controller_session_id", "run_id", "job_id", "status", "outcome", "evidence_file", "completion_file")
    completion = _completion(args)
    result = finish_direct(ledger_dir=_path(args.dir), controller_session_id=args.controller_session_id, run_id=args.run_id, job_id=args.job_id, provider_outcome=completion["provider_outcome"], repository_verification=completion["repository_verification"], outcome=args.outcome, evidence=_evidence(args), provider_session_id=args.provider_session_id)
    return _json_paths(result)


def command_finalize(args: Any) -> dict[str, Any]:
    _required(args, "dir", "controller_session_id", "run_id")
    path, event = finalize_run(_path(args.dir), args.controller_session_id, args.run_id)
    return _json_paths(_result(path, [event], controller_session_id=args.controller_session_id, run_id=args.run_id))


def _json_paths(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value.resolve())
    if isinstance(value, dict):
        return {key: _json_paths(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_paths(item) for item in value]
    return value


def _event_matches(event: dict[str, Any], filters: dict[str, Any]) -> bool:
    for name in ("controller_session_id", "run_id", "job_id", "event"):
        value = filters.get(name)
        if value is not None and event.get(name) != value:
            return False
    status = filters.get("status")
    if status is not None and event.get("data", {}).get("status") != status:
        return False
    if filters.get("since") is not None and event["timestamp"] < filters["since"]:
        return False
    if filters.get("until") is not None and event["timestamp"] > filters["until"]:
        return False
    return True


def _stream_file(path: Path) -> Iterator[tuple[dict[str, Any], int]]:
    offset = 0
    with path.open("rb") as handle:
        for line in handle:
            current = offset
            offset += len(line)
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LedgerValidationError(f"{path}: invalid JSON") from exc
            validate_event(event)
            yield event, current


def stream_events(ledger_dir: Path, *, controller_session_id: str | None = None, limit: int | None = None, **filters: Any) -> Iterator[dict[str, Any]]:
    directory = _path(ledger_dir)
    if not directory.exists():
        return
    if not directory.is_dir():
        raise NotADirectoryError(f"ledger directory is not a directory: {directory}")
    paths = [directory / f"{controller_session_id}.ndjson"] if controller_session_id else sorted(directory.glob("*.ndjson"))
    heap: list[tuple[str, str, int, int, dict[str, Any], Iterator[tuple[dict[str, Any], int]]]] = []
    streams: list[Iterator[tuple[dict[str, Any], int]]] = []
    for index, path in enumerate(paths):
        if not path.exists():
            continue
        iterator = _stream_file(path)
        streams.append(iterator)
        try:
            event, offset = next(iterator)
        except StopIteration:
            continue
        heapq.heappush(heap, (event["timestamp"], event["controller_session_id"], offset, index, event, iterator))
    emitted = 0
    while heap and (limit is None or emitted < limit):
        _, _, _, index, event, iterator = heapq.heappop(heap)
        if _event_matches(event, filters):
            yield event
            emitted += 1
        try:
            next_event, offset = next(iterator)
        except StopIteration:
            continue
        heapq.heappush(heap, (next_event["timestamp"], next_event["controller_session_id"], offset, index, next_event, iterator))


def show_ledger(ledger_dir: Path, *, format: str = "json", controller_session_id: str | None = None, run_id: str | None = None, job_id: str | None = None, event: str | None = None, status: str | None = None, since: str | None = None, until: str | None = None, limit: int | None = None) -> dict[str, Any] | str:
    events = list(stream_events(ledger_dir, controller_session_id=controller_session_id, run_id=run_id, job_id=job_id, event=event, status=status, since=since, until=until, limit=limit))
    if format == "text":
        return render_text(events)
    return {"ledger_dir": str(_path(ledger_dir)), "events": events, "warnings": [], "errors": []}


def render_text(events: Iterable[dict[str, Any]]) -> str:
    lines: list[str] = []
    for event in events:
        session = event["controller_session_id"][:8]
        run = event["run_id"][:8]
        job = (event["job_id"] or "-")[:8]
        data = event["data"]
        outcome = data.get("outcome", "")
        provider = data.get("provider_outcome", {}).get("status", "") if isinstance(data.get("provider_outcome"), dict) else ""
        repository = data.get("repository_verification", {}).get("status", "") if isinstance(data.get("repository_verification"), dict) else ""
        lines.append(f"{session} {run} {job} {event['event']} {provider} {repository} {outcome}".rstrip())
    return "\n".join(lines) + ("\n" if lines else "")


def read_legacy(path: Path) -> dict[str, Any]:
    path = _path(path)
    content = path.read_text(encoding="utf-8")
    if not content.startswith(_LEGACY_HEADER):
        raise LedgerValidationError("legacy ledger has invalid header")
    lines = [line for line in content[len(_LEGACY_HEADER):].splitlines() if line]
    return {"path": str(path), "events": [{"schema_version": 1, "raw": line} for line in lines], "warnings": ["legacy v1 ledger format is read-only"], "errors": []}


def validate_ledger(ledger_dir: Path, controller_session_id: str | None = None) -> dict[str, Any]:
    directory = _path(ledger_dir)
    errors: list[str] = []
    warnings: list[str] = []
    all_events: list[dict[str, Any]] = []
    seen_event_ids: dict[str, Path] = {}
    seen_runs: dict[str, Path] = {}
    seen_jobs: dict[str, Path] = {}
    try:
        paths = [directory / f"{controller_session_id}.ndjson"] if controller_session_id else sorted(directory.glob("*.ndjson"))
        for path in paths:
            if not path.exists():
                errors.append(f"{path}: session file does not exist")
                continue
            if not _UUID_FILENAME.fullmatch(path.name):
                errors.append(f"{path}: invalid session filename")
                continue
            session_events: list[dict[str, Any]] = []
            try:
                for event, _ in _stream_file(path):
                    event_id = event["event_id"]
                    if event_id in seen_event_ids:
                        errors.append(f"{path}: duplicate event ID {event_id} (first in {seen_event_ids[event_id]})")
                    else:
                        seen_event_ids[event_id] = path
                    run_id = event["run_id"]
                    if run_id in seen_runs and seen_runs[run_id] != path:
                        errors.append(f"{path}: cross-file UUID collision for run_id {run_id}")
                    else:
                        seen_runs[run_id] = path
                    if event["job_id"] is not None:
                        job_id = event["job_id"]
                        if job_id in seen_jobs and seen_jobs[job_id] != path:
                            errors.append(f"{path}: cross-file UUID collision for job_id {job_id}")
                        else:
                            seen_jobs[job_id] = path
                    if event["controller_session_id"] != path.stem:
                        errors.append(f"{path}: envelope session mismatch")
                    session_events.append(event)
                    all_events.append(event)
            except LedgerValidationError as exc:
                errors.append(str(exc))
                continue
            _validate_lifecycle(session_events, errors, warnings, path)
    except OSError as exc:
        errors.append(str(exc))
    return {"ledger_dir": str(directory), "valid": not errors, "errors": errors, "warnings": warnings, "event_count": len(all_events)}


def _validate_lifecycle(events: list[dict[str, Any]], errors: list[str], warnings: list[str], path: Path) -> None:
    runs: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        runs.setdefault(event["run_id"], []).append(event)
    for run_id, items in runs.items():
        starts = [item for item in items if item["event"] == "run-started"]
        completed = [item for item in items if item["event"] == "run-completed"]
        if not starts:
            errors.append(f"{path}: run has no run-started event {run_id}")
        if len(starts) > 1:
            errors.append(f"{path}: duplicate run start {run_id}")
        if len(completed) > 1:
            errors.append(f"{path}: duplicate run completed {run_id}")
        allocations = [item for item in items if item["event"] == "allocated"]
        allocation_ids = [item["job_id"] for item in allocations]
        if len(allocation_ids) != len(set(allocation_ids)):
            errors.append(f"{path}: duplicate job allocation {run_id}")
        allocated = set(allocation_ids)
        completed_jobs: set[str] = set()
        dispatched_jobs: set[str] = set()
        for index, item in enumerate(items):
            job_id = item["job_id"]
            if item["event"] == "allocated":
                continue
            if item["event"] == "dispatched":
                if job_id not in allocated:
                    errors.append(f"{path}: job event without allocation dispatched")
                dispatched_jobs.add(job_id)
                continue
            if item["event"] in {"grounding-observed", "grounding-reused"}:
                if job_id not in allocated:
                    errors.append(f"{path}: job event without allocation {item['event']}")
                continue
            if item["event"] in {"provider-session", "liveness-warning", "attempt-failed", "resumed", "complete"}:
                if job_id not in allocated:
                    errors.append(f"{path}: job event without allocation {item['event']}")
                if job_id not in dispatched_jobs:
                    errors.append(f"{path}: attempt without dispatch {item['event']}")
            if job_id in completed_jobs:
                errors.append(f"{path}: event after job completion {job_id}")
            if item["event"] == "complete":
                if job_id in completed_jobs:
                    errors.append(f"{path}: duplicate complete {job_id}")
                completed_jobs.add(job_id)
        if completed:
            complete_index = items.index(completed[-1])
            if complete_index != len(items) - 1:
                errors.append(f"{path}: event after completion")
            if completed_jobs != allocated:
                errors.append(f"{path}: run completed before every job")
        elif starts and completed_jobs == allocated and allocated:
            errors.append(f"{path}: absent run completed after terminalization")
        elif starts:
            warnings.append(f"{path}: incomplete run {run_id}")
        for job_id in allocated:
            if job_id not in completed_jobs:
                warnings.append(f"{path}: incomplete job {job_id}")

def command_show(args: Any) -> dict[str, Any] | str:
    if args.legacy_path:
        if args.format == "text":
            payload = read_legacy(_path(args.legacy_path))
            return "\n".join(item["raw"] for item in payload["events"]) + "\n"
        return read_legacy(_path(args.legacy_path))
    _required(args, "dir")
    return show_ledger(_path(args.dir), format=args.format, controller_session_id=args.controller_session_id, run_id=args.run_id, job_id=args.job_id, event=args.event, status=args.status, since=args.since, until=args.until, limit=args.limit)


def command_validate(args: Any) -> dict[str, Any]:
    _required(args, "dir")
    return validate_ledger(_path(args.dir), args.controller_session_id)
