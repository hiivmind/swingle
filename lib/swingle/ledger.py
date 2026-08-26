from __future__ import annotations

import fcntl
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence
from . import ledger_schema as _schema
from .errors import LedgerLifecycleError, LedgerValidationError
from .ledger_schema import (
    MAX_ENCODED_EVENT_BYTES,
    EventDraft,
    build_event,
    derive_complete_status,
    encode_event,
    parse_timestamp,
    validate_draft,
    validate_event,
)


def new_uuid() -> str:
    return _schema.new_uuid()


def utc_timestamp(now=None) -> str:
    return _schema.utc_timestamp(now)

_SESSION_EVENT_TAIL_BYTES = MAX_ENCODED_EVENT_BYTES + 1
_ARTIFACT_IGNORE = "*\n!.gitignore\n"


def _require_uuid(value: str, field: str) -> None:
    # Reuse the canonical envelope validator without allocating an identity.
    try:
        validate_draft(EventDraft("run-started", value, "00000000-0000-4000-8000-000000000000", None, {"kind": "direct"}))
    except LedgerValidationError as exc:
        raise LedgerValidationError(f"{field} must be a canonical lowercase UUID") from exc


def _session_path(ledger_dir: Path, controller_session_id: str) -> Path:
    ledger_dir = Path(ledger_dir).expanduser()
    if ledger_dir.exists() and not ledger_dir.is_dir():
        raise NotADirectoryError(f"ledger directory is not a directory: {ledger_dir}")
    ledger_dir.mkdir(parents=True, exist_ok=True)
    _require_uuid(controller_session_id, "controller_session_id")
    return ledger_dir / f"{controller_session_id}.ndjson"


def _last_event_from_tail(handle) -> dict[str, Any] | None:
    handle.seek(0, os.SEEK_END)
    size = handle.tell()
    if not size:
        return None
    read_size = min(size, _SESSION_EVENT_TAIL_BYTES)
    handle.seek(size - read_size)
    tail = handle.read(read_size)
    line = tail.rstrip(b"\r\n")
    if b"\n" in line:
        line = line.rsplit(b"\n", 1)[1]
    if not line:
        return None
    try:
        event = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LedgerValidationError("ledger session file has an invalid final event") from exc
    validate_event(event)
    return event


def _open_session(ledger_dir: Path, controller_session_id: str):
    path = _session_path(ledger_dir, controller_session_id)
    handle = path.open("a+b")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return path, handle


def _append_events_locked(handle, drafts: Sequence[EventDraft], event_ids: Sequence[str], *, last_event: dict[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    last_timestamp = parse_timestamp(last_event["timestamp"]) if last_event is not None else None
    last_timestamp_text = last_event["timestamp"] if last_event is not None else None
    final_events: list[dict[str, Any]] = []
    encoded_events: list[bytes] = []
    for draft, event_id in zip(drafts, event_ids):
        data = deepcopy(draft.data)
        current_text = utc_timestamp()
        current = parse_timestamp(current_text)
        if last_timestamp is not None and current < last_timestamp:
            timestamp = last_timestamp_text
            current = last_timestamp
        else:
            timestamp = current_text
        if draft.event == "grounding-reused":
            grounded_at = parse_timestamp(data["grounded_at"])
            data["age_seconds"] = max(0, int((current - grounded_at).total_seconds()))
        stamped = EventDraft(draft.event, draft.controller_session_id, draft.run_id, draft.job_id, data)
        event = build_event(stamped, timestamp=timestamp, event_id=event_id)
        encoded_events.append(encode_event(event))
        last_timestamp = parse_timestamp(timestamp)
        last_timestamp_text = timestamp
        last_event = event
        final_events.append(event)
    if encoded_events:
        handle.seek(0, os.SEEK_END)
        for encoded in encoded_events:
            handle.write(encoded + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return tuple(final_events)
def append_events(ledger_dir: Path, controller_session_id: str, drafts: Sequence[EventDraft]) -> tuple[Path, tuple[dict[str, Any], ...]]:
    drafts = tuple(drafts)
    validated_drafts: list[EventDraft] = []
    for draft in drafts:
        validated = validate_draft(draft, for_append=True)
        if validated.controller_session_id != controller_session_id:
            raise LedgerValidationError("draft controller_session_id differs from selected session")
        validated_drafts.append(validated)
    drafts = tuple(validated_drafts)
    event_ids = tuple(new_uuid() for _ in drafts)
    path, handle = _open_session(ledger_dir, controller_session_id)
    try:
        last_event = _last_event_from_tail(handle)
        events = _append_events_locked(handle, drafts, event_ids, last_event=last_event)
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    return path, events


def read_events(ledger_dir: Path) -> tuple[dict[str, Any], ...]:
    ledger_dir = Path(ledger_dir).expanduser()
    if not ledger_dir.is_dir():
        if ledger_dir.exists():
            raise NotADirectoryError(f"ledger directory is not a directory: {ledger_dir}")
        return ()
    records: list[tuple[dict[str, Any], int]] = []
    for path in ledger_dir.glob("*.ndjson"):
        offset = 0
        for line in path.read_bytes().splitlines(keepends=True):
            if not line.strip():
                offset += len(line)
                continue
            try:
                event = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LedgerValidationError(f"{path}: invalid JSON") from exc
            validate_event(event)
            records.append((event, offset))
            offset += len(line)
    records.sort(key=lambda item: (item[0]["timestamp"], item[0]["controller_session_id"], item[1]))
    return tuple(event for event, _ in records)


def _artifact_directory(project: Path, run_id: str, job_id: str) -> Path:
    project = Path(project).expanduser().resolve()
    artifact_root = project / ".swingle" / "delegate" / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    ignore = artifact_root / ".gitignore"
    if not ignore.exists():
        ignore.write_text(_ARTIFACT_IGNORE, encoding="utf-8")
    artifact_dir = artifact_root / run_id / job_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _result(path: Path, events: Sequence[dict[str, Any]], *, controller_session_id: str | None = None, run_id: str | None = None, job_id: str | None = None, artifact_dir: Path | None = None) -> dict[str, Any]:
    output: dict[str, Any] = {"ledger_file": path, "ledger_path": path, "path": path, "events": list(events)}
    if controller_session_id is not None:
        output["controller_session_id"] = controller_session_id
    if run_id is not None:
        output["run_id"] = run_id
    if job_id is not None:
        output["job_id"] = job_id
    if artifact_dir is not None:
        output["artifact_dir"] = artifact_dir
    if events:
        output["event"] = events[-1]
    return output

def start_run(ledger_dir: Path, kind: str, controller_session_id: str | None = None) -> dict[str, Any]:
    controller_session_id = controller_session_id or new_uuid()
    run_id = new_uuid()
    path, events = append_events(ledger_dir, controller_session_id, [EventDraft("run-started", controller_session_id, run_id, None, {"kind": kind})])
    return _result(path, events, controller_session_id=controller_session_id, run_id=run_id)


def allocate_job(*, project: Path, ledger_dir: Path, controller_session_id: str, run_id: str, role: str, contract: str, tier: str, task: str) -> dict[str, Any]:
    job_id = new_uuid()
    draft = EventDraft("allocated", controller_session_id, run_id, job_id, {"role": role, "contract": contract, "tier": tier, "task": task})
    validate_draft(draft, for_append=True)
    artifact_dir = _artifact_directory(project, run_id, job_id)
    path, events = append_events(ledger_dir, controller_session_id, [draft])
    return _result(path, events, controller_session_id=controller_session_id, run_id=run_id, job_id=job_id, artifact_dir=artifact_dir)


def record_event(*, ledger_dir: Path, controller_session_id: str, run_id: str, event: str, data: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
    if event == "run-completed":
        raise LedgerValidationError("run-completed is emitted only by finish_direct or finalize_run")
    path, events = append_events(ledger_dir, controller_session_id, [EventDraft(event, controller_session_id, run_id, job_id, data)])
    return _result(path, events, controller_session_id=controller_session_id, run_id=run_id, job_id=job_id)


def _grounding_from_context(dispatch_context: dict[str, Any], provider: str) -> tuple[str, dict[str, Any]]:
    if not isinstance(dispatch_context, dict):
        raise LedgerValidationError("dispatch context must be an object")
    source = dispatch_context.get("grounding_source")
    if source not in {"observed", "reused"}:
        raise LedgerValidationError("dispatch context grounding_source must be observed or reused")
    grounding_event = dispatch_context.get("grounding_event")
    if isinstance(grounding_event, dict):
        grounding = deepcopy(grounding_event.get("data", grounding_event))
        event_name = grounding_event.get("event", "grounding-observed" if source == "observed" else "grounding-reused")
    else:
        grounding = deepcopy(dispatch_context.get("grounding", {}))
        event_name = "grounding-observed" if source == "observed" else "grounding-reused"
    if not grounding:
        raise LedgerValidationError("dispatch context must contain grounding event data")
    grounding.setdefault("provider", provider)
    if source == "observed":
        if grounding.get("storage") == "none":
            if grounding.get("receipt_id") is not None:
                raise LedgerValidationError("uncached grounding receipt_id must be null")
            grounding["receipt_id"] = new_uuid()
        grounding.pop("age_seconds", None)
        event_name = "grounding-observed"
    else:
        grounding.pop("age_seconds", None)
        event_name = "grounding-reused"
    if grounding.get("provider") not in (None, provider):
        raise LedgerValidationError("grounding provider differs from selected provider")
    return event_name, grounding


def begin_direct(*, project: Path, ledger_dir: Path, controller_session_id: str | None = None, run_id: str | None = None, job_id: str | None = None, role: str, contract: str, tier: str, task: str, provider: str, model: str, effort: str, dispatch_context: dict[str, Any]) -> dict[str, Any]:
    controller_session_id = controller_session_id or new_uuid()
    run_id = run_id or new_uuid()
    job_id = job_id or new_uuid()
    grounding_event, grounding_data = _grounding_from_context(dispatch_context, provider)
    receipt_id = grounding_data.get("receipt_id")
    grounding_revision = grounding_data.get("receipt_revision")
    drafts = [
        EventDraft("run-started", controller_session_id, run_id, None, {"kind": "direct"}),
        EventDraft("allocated", controller_session_id, run_id, job_id, {"role": role, "contract": contract, "tier": tier, "task": task}),
        EventDraft(grounding_event, controller_session_id, run_id, job_id, grounding_data),
        EventDraft("dispatched", controller_session_id, run_id, job_id, {"provider": provider, "model": model, "effort": effort, "attempt": 1, "liveness_policy": deepcopy(dispatch_context.get("liveness_policy")), "grounding_receipt_id": receipt_id, "grounding_receipt_revision": grounding_revision, "grounding_source": dispatch_context["grounding_source"]}),
    ]
    for draft in drafts:
        validate_draft(draft, for_append=True)
    artifact_dir = _artifact_directory(project, run_id, job_id)
    event_ids = tuple(new_uuid() for _ in drafts)
    path, handle = _open_session(ledger_dir, controller_session_id)
    try:
        events = _append_events_locked(handle, drafts, event_ids, last_event=_last_event_from_tail(handle))
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    output = _result(path, events, controller_session_id=controller_session_id, run_id=run_id, job_id=job_id, artifact_dir=artifact_dir)
    output["receipt_id"] = receipt_id
    return output

def finish_direct(*, ledger_dir: Path, controller_session_id: str, run_id: str, job_id: str, provider_outcome: dict[str, Any], repository_verification: dict[str, Any], outcome: str, evidence: Sequence[dict[str, Any]], status: str | None = None, provider_session_id: str | None = None) -> dict[str, Any]:
    _schema._validate_provider_outcome(provider_outcome)
    _schema._validate_repository_verification(repository_verification)
    derived_status = derive_complete_status(provider_outcome, repository_verification)
    if status is not None and status != derived_status:
        raise LedgerValidationError(f"status must be {derived_status} for provider and repository outcomes")
    complete_data = {"status": derived_status, "outcome": outcome, "evidence": list(evidence), "provider_outcome": deepcopy(provider_outcome), "repository_verification": deepcopy(repository_verification)}
    drafts: list[EventDraft] = []
    if provider_session_id is not None:
        drafts.append(EventDraft("provider-session", controller_session_id, run_id, job_id, {"attempt": 1, "provider_session_id": provider_session_id}))
    drafts.extend([
        EventDraft("complete", controller_session_id, run_id, job_id, complete_data),
        EventDraft("run-completed", controller_session_id, run_id, None, {"status": derived_status, "outcome": f"jobs=1 done={int(derived_status == 'DONE')} done_with_concerns={int(derived_status == 'DONE_WITH_CONCERNS')} needs_context={int(derived_status == 'NEEDS_CONTEXT')} blocked={int(derived_status == 'BLOCKED')}"}),
    ])
    for draft in drafts:
        validate_draft(draft, for_append=True)
    event_ids = tuple(new_uuid() for _ in drafts)
    path, handle = _open_session(ledger_dir, controller_session_id)
    try:
        events = _append_events_locked(handle, drafts, event_ids, last_event=_last_event_from_tail(handle))
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    return _result(path, events, controller_session_id=controller_session_id, run_id=run_id, job_id=job_id)

def _all_events(handle) -> list[dict[str, Any]]:
    handle.seek(0)
    raw = handle.read()
    if not raw:
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line:
            continue
        try:
            event = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LedgerLifecycleError(f"invalid JSON at ledger line {line_number}") from exc
        validate_event(event)
        events.append(event)
    return events


def finalize_run(ledger_dir: Path, controller_session_id: str, run_id: str) -> tuple[Path, dict[str, Any]]:
    # Allocate the final identity before opening the selected file or acquiring its lock.
    event_id = new_uuid()
    path = _session_path(ledger_dir, controller_session_id)
    if not path.exists():
        raise LedgerLifecycleError("run session file does not exist")
    handle = path.open("a+b")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    try:
        events = _all_events(handle)
        matching = [event for event in events if event["run_id"] == run_id]
        starts = [event for event in matching if event["event"] == "run-started"]
        if len(starts) != 1:
            raise LedgerLifecycleError("run must contain exactly one run-started event")
        if any(event["event"] == "run-completed" for event in matching):
            raise LedgerLifecycleError("run already has run-completed")
        allocation_events = [event for event in matching if event["event"] == "allocated"]
        allocation_ids = [event["job_id"] for event in allocation_events]
        if len(allocation_ids) != len(set(allocation_ids)):
            raise LedgerLifecycleError("run has duplicate allocated job IDs")
        allocations = set(allocation_ids)
        completions: dict[str, list[dict[str, Any]]] = {job_id: [] for job_id in allocations}
        for event in matching:
            if event["event"] == "complete":
                if event["job_id"] not in allocations:
                    raise LedgerLifecycleError("complete has no matching allocation")
                completions[event["job_id"]].append(event)
        if any(len(items) != 1 for items in completions.values()):
            raise LedgerLifecycleError("every allocated job must have exactly one complete event")
        for job_id, items in completions.items():
            complete_index = matching.index(items[0])
            if any(event["job_id"] == job_id for event in matching[complete_index + 1:]):
                raise LedgerLifecycleError("complete must be the terminal event for each allocated job")
        counts = {status: 0 for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED")}
        for items in completions.values():
            counts[items[0]["data"]["status"]] += 1
        if counts["BLOCKED"]:
            status = "BLOCKED"
        elif counts["NEEDS_CONTEXT"]:
            status = "NEEDS_CONTEXT"
        elif counts["DONE_WITH_CONCERNS"]:
            status = "DONE_WITH_CONCERNS"
        else:
            status = "DONE"
        outcome = f"jobs={len(allocations)} done={counts['DONE']} done_with_concerns={counts['DONE_WITH_CONCERNS']} needs_context={counts['NEEDS_CONTEXT']} blocked={counts['BLOCKED']}"
        draft = EventDraft("run-completed", controller_session_id, run_id, None, {"status": status, "outcome": outcome})
        validate_draft(draft, for_append=True)
        last_event = events[-1] if events else None
        final = _append_events_locked(handle, [draft], [event_id], last_event=last_event)[0]
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    return path, final
