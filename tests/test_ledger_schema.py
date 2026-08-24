from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from swingle.errors import LedgerEventTooLarge, LedgerValidationError
from swingle.ledger_schema import (
    EVENTS,
    EventDraft,
    build_event,
    encode_event,
    new_uuid,
    utc_timestamp,
    validate_event,
)


SESSION = "11111111-1111-4111-8111-111111111111"
RUN = "22222222-2222-4222-8222-222222222222"
JOB = "33333333-3333-4333-8333-333333333333"
RECEIPT = "44444444-4444-4444-8444-444444444444"
STAMP = "2026-08-24T04:15:30.123Z"


def _provider_outcome(status="DONE", *, exit_code=0):
    return {
        "status": status,
        "claim": "WRITE_OK",
        "exit_code": exit_code,
        "model_requested": "provider-default",
        "model_used": None,
        "session_id": None,
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "cache_read_tokens": None,
            "cache_write_tokens": None,
            "total_tokens": None,
        },
        "cost": {"amount": 0.0, "currency": "USD"},
        "result_artifact": "$REPO_ROOT/.swingle/delegate/artifacts/run/job/result.json",
    }


def _repository(*, required=True, status="VERIFIED", count=1):
    return {
        "required": required,
        "status": status,
        "changed_path_count": count if required else None,
        "summary": "target.txt was verified",
        "verification_artifact": "$REPO_ROOT/.swingle/delegate/artifacts/run/job/verification.txt",
    }


def valid_data(event):
    if event == "run-started":
        return {"kind": "direct"}
    if event == "run-completed":
        return {"status": "DONE", "outcome": "jobs=1 done=1 done_with_concerns=0 needs_context=0 blocked=0"}
    if event == "allocated":
        return {"role": "reader", "contract": "$PLUGIN_ROOT/contracts/reader-contract.md", "tier": "standard", "task": "read the target"}
    if event == "grounding-observed":
        return {
            "receipt_id": RECEIPT,
            "receipt_revision": None,
            "storage": "none",
            "provider": "codex",
            "cache_path": None,
            "grounded_at": STAMP,
            "expires_at": None,
            "executable": "/usr/local/bin/codex",
            "provider_guidance_sha256": "0" * 64,
            "scopes": ["headless-command"],
            "model_count": 0,
            "evidence_commands": ["codex --help"],
        }
    if event == "grounding-reused":
        return {
            "receipt_id": RECEIPT,
            "receipt_revision": 1,
            "storage": "cache",
            "provider": "codex",
            "cache_path": "/project/.swingle/grounding/codex.json",
            "grounded_at": STAMP,
            "expires_at": "2026-08-31T04:15:30.123Z",
            "age_seconds": 0,
            "executable": "/usr/local/bin/codex",
            "provider_guidance_sha256": "0" * 64,
            "scopes": ["headless-command"],
            "model_count": 0,
        }
    if event == "dispatched":
        return {
            "provider": "codex",
            "model": "provider-default",
            "effort": "provider-default",
            "attempt": 1,
            "liveness_policy": {
                "check_interval_seconds": 60,
                "startup_grace_seconds": 300,
                "silence_warning_seconds": 300,
                "hard_timeout_seconds": None,
            },
            "grounding_receipt_id": RECEIPT,
            "grounding_receipt_revision": None,
            "grounding_source": "observed",
        }
    if event == "provider-session":
        return {"attempt": 1, "provider_session_id": "provider-session-1"}
    if event == "liveness-warning":
        return {"attempt": 1, "elapsed_seconds": 301.5, "silence_seconds": None, "process_state": "running", "action": "diagnose"}
    if event == "attempt-failed":
        return {"attempt": 1, "signature": "provider exited", "recovery": "retry"}
    if event == "resumed":
        return {"attempt": 2, "provider_session_id": "provider-session-2", "reason": "transient failure"}
    if event == "complete":
        return {
            "status": "DONE",
            "outcome": "answer returned",
            "evidence": [{"kind": "report", "value": "result.json"}],
            "provider_outcome": _provider_outcome(),
            "repository_verification": _repository(),
        }
    raise AssertionError(event)


def _draft(event, *, job_id=None, data=None):
    return EventDraft(event, SESSION, RUN, job_id, valid_data(event) if data is None else data)


def test_every_event_has_valid_fixture():
    assert set(EVENTS) == {
        "run-started", "run-completed", "allocated", "grounding-observed", "grounding-reused",
        "dispatched", "provider-session", "liveness-warning", "attempt-failed", "resumed", "complete",
    }
    for event in EVENTS:
        job_id = None if event in {"run-started", "run-completed"} else JOB
        built = build_event(_draft(event, job_id=job_id), timestamp=STAMP, event_id=new_uuid())
        assert validate_event(built) == built


def test_uuid_and_timestamp_are_canonical():
    value = new_uuid()
    assert value == value.lower()
    assert utc_timestamp(datetime(2026, 8, 24, 4, 15, 30, 123456, tzinfo=timezone.utc)) == STAMP
    assert utc_timestamp(datetime(2026, 8, 24, 4, 15, 30, 123456)) == STAMP


@pytest.mark.parametrize("event", EVENTS)
def test_event_rejects_missing_and_unknown_fields(event):
    job_id = None if event in {"run-started", "run-completed"} else JOB
    data = valid_data(event)
    missing = next(iter(data))
    with pytest.raises(LedgerValidationError):
        build_event(_draft(event, job_id=job_id, data={k: v for k, v in data.items() if k != missing}), timestamp=STAMP, event_id=new_uuid())
    with pytest.raises(LedgerValidationError):
        build_event(_draft(event, job_id=job_id, data={**data, "unknown": True}), timestamp=STAMP, event_id=new_uuid())


def test_null_job_id_is_only_for_run_events():
    with pytest.raises(LedgerValidationError):
        build_event(_draft("allocated", job_id=None), timestamp=STAMP, event_id=new_uuid())
    with pytest.raises(LedgerValidationError):
        build_event(_draft("run-started", job_id=JOB), timestamp=STAMP, event_id=new_uuid())


def test_envelope_rejects_unknown_version_newline_and_blank():
    event = build_event(_draft("run-started", job_id=None), timestamp=STAMP, event_id=new_uuid())
    for bad in (
        {**event, "schema_version": 1},
        {**event, "unknown": 1},
        {**event, "event": "run-started\n"},
        {**event, "controller_session_id": " "},
    ):
        with pytest.raises(LedgerValidationError):
            validate_event(bad)


def test_complete_requires_done_evidence():
    data = valid_data("complete")
    data["evidence"] = []
    with pytest.raises(LedgerValidationError):
        build_event(_draft("complete", job_id=JOB, data=data), timestamp=STAMP, event_id=new_uuid())


def test_provider_and_repository_reconciliation_boundaries():
    complete = valid_data("complete")
    complete["repository_verification"] = _repository(required=False, status="NOT_APPLICABLE")
    complete["status"] = "DONE"
    build_event(_draft("complete", job_id=JOB, data=complete), timestamp=STAMP, event_id=new_uuid())
    for status in ("INVALID_RESULT", "UNCHANGED", "FAILED_TESTS"):
        bad = valid_data("complete")
        bad["repository_verification"] = _repository(status=status)
        bad["status"] = "DONE"
        with pytest.raises(LedgerValidationError):
            build_event(_draft("complete", job_id=JOB, data=bad), timestamp=STAMP, event_id=new_uuid())


def test_not_attempted_requires_context_or_blocked_and_no_exit_code():
    for status in ("NEEDS_CONTEXT", "BLOCKED"):
        data = valid_data("complete")
        data["repository_verification"] = _repository(status="NOT_ATTEMPTED", count=None)
        data["provider_outcome"] = _provider_outcome(status=status, exit_code=None)
        data["status"] = status
        build_event(_draft("complete", job_id=JOB, data=data), timestamp=STAMP, event_id=new_uuid())
    data = valid_data("complete")
    data["repository_verification"] = _repository(status="NOT_ATTEMPTED", count=None)
    data["provider_outcome"] = _provider_outcome(status="NEEDS_CONTEXT", exit_code=1)
    data["status"] = "NEEDS_CONTEXT"
    with pytest.raises(LedgerValidationError):
        build_event(_draft("complete", job_id=JOB, data=data), timestamp=STAMP, event_id=new_uuid())


def test_receipt_ids_and_age_are_validated_without_secret_scanning():
    data = valid_data("grounding-reused")
    data["receipt_id"] = "not-a-uuid"
    with pytest.raises(LedgerValidationError):
        build_event(_draft("grounding-reused", job_id=JOB, data=data), timestamp=STAMP, event_id=new_uuid())
    data = valid_data("complete")
    data["outcome"] = "contains token-like words but is controller-owned text"
    build_event(_draft("complete", job_id=JOB, data=data), timestamp=STAMP, event_id=new_uuid())

def test_encoded_event_limit_raises_typed_error(monkeypatch):
    data = valid_data("complete")
    event = build_event(_draft("complete", job_id=JOB, data=data), timestamp=STAMP, event_id=new_uuid())
    encoded_length = len(encode_event(event))
    monkeypatch.setattr("swingle.ledger_schema.MAX_ENCODED_EVENT_BYTES", encoded_length - 1)
    with pytest.raises(LedgerEventTooLarge):
        encode_event(event)
