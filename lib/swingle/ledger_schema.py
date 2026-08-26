from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import re
from typing import Any
from uuid import UUID, uuid4

from .errors import LedgerEventTooLarge, LedgerValidationError

SCHEMA_VERSION = 2
MAX_ENCODED_EVENT_BYTES = 65_536
MAX_GENERAL_TEXT_CODEPOINTS = 4_096
MAX_EVIDENCE_ENTRIES = 16
MAX_EVIDENCE_VALUE_CODEPOINTS = 1_024
EVENTS = (
    "run-started",
    "run-completed",
    "allocated",
    "grounding-observed",
    "grounding-reused",
    "dispatched",
    "provider-session",
    "liveness-warning",
    "attempt-failed",
    "resumed",
    "complete",
)
RUN_EVENTS = {"run-started", "run-completed"}
STATUSES = {"DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"}
REPOSITORY_STATUSES = {"VERIFIED", "INVALID_RESULT", "UNCHANGED", "FAILED_TESTS", "NOT_ATTEMPTED", "NOT_APPLICABLE"}

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class EventDraft:
    event: str
    controller_session_id: str
    run_id: str
    job_id: str | None
    data: dict[str, Any]


def new_uuid() -> str:
    return str(uuid4())


def utc_timestamp(now: datetime | None = None) -> str:
    value = datetime.now(timezone.utc) if now is None else now
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    value = value.replace(microsecond=(value.microsecond // 1_000) * 1_000)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        raise LedgerValidationError("timestamp must be UTC RFC 3339 with millisecond precision")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LedgerValidationError("timestamp is invalid") from exc


def _fail(message: str) -> None:
    raise LedgerValidationError(message)


def _dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{field} must be an object")
    return value


def _keys(value: dict[str, Any], required: set[str], field: str = "data") -> None:
    unknown = set(value) - required
    missing = required - set(value)
    if unknown:
        _fail(f"{field} has unknown fields: {', '.join(sorted(unknown))}")
    if missing:
        _fail(f"{field} is missing fields: {', '.join(sorted(missing))}")


def _text(value: Any, field: str, *, limit: int = MAX_GENERAL_TEXT_CODEPOINTS) -> str:
    if not isinstance(value, str):
        _fail(f"{field} must be a string")
    if not value.strip():
        _fail(f"{field} must not be blank")
    if "\n" in value or "\r" in value:
        _fail(f"{field} must not contain newlines")
    if len(value) > limit:
        _fail(f"{field} exceeds {limit} Unicode code points")
    return value


def _nullable_text(value: Any, field: str, *, limit: int = MAX_GENERAL_TEXT_CODEPOINTS) -> None:
    if value is not None:
        _text(value, field, limit=limit)


def _uuid(value: Any, field: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not _UUID_RE.fullmatch(value):
        _fail(f"{field} must be a canonical lowercase UUID")
    try:
        if str(UUID(value)) != value:
            _fail(f"{field} must be a canonical lowercase UUID")
    except ValueError as exc:
        raise LedgerValidationError(f"{field} must be a canonical lowercase UUID") from exc


def validate_uuid(value: Any, field: str) -> None:
    _uuid(value, field)


def _integer(value: Any, field: str, *, minimum: int = 0, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{field} must be an integer >= {minimum}")


def _number(value: Any, field: str, *, minimum: float = 0, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        _fail(f"{field} must be a finite number >= {minimum}")


def _enum(value: Any, field: str, values: set[str]) -> None:
    if value not in values:
        _fail(f"{field} must be one of {', '.join(sorted(values))}")


def _list(value: Any, field: str, *, maximum: int | None = None) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{field} must be an array")
    if maximum is not None and len(value) > maximum:
        _fail(f"{field} has more than {maximum} entries")
    return value


def _text_list(value: Any, field: str, *, maximum: int | None = None, limit: int = MAX_GENERAL_TEXT_CODEPOINTS) -> None:
    for index, item in enumerate(_list(value, field, maximum=maximum)):
        _text(item, f"{field}[{index}]", limit=limit)


def _validate_evidence(value: Any) -> None:
    entries = _list(value, "evidence", maximum=MAX_EVIDENCE_ENTRIES)
    for index, item in enumerate(entries):
        item = _dict(item, f"evidence[{index}]")
        _keys(item, {"kind", "value"}, f"evidence[{index}]")
        _enum(item["kind"], f"evidence[{index}].kind", {"file", "command", "url", "report", "other"})
        _text(item["value"], f"evidence[{index}].value", limit=MAX_EVIDENCE_VALUE_CODEPOINTS)


def _validate_liveness_policy(value: Any) -> None:
    policy = _dict(value, "data.liveness_policy")
    _keys(policy, {"check_interval_seconds", "startup_grace_seconds", "silence_warning_seconds", "hard_timeout_seconds"}, "data.liveness_policy")
    _integer(policy["check_interval_seconds"], "check_interval_seconds", minimum=1)
    _integer(policy["startup_grace_seconds"], "startup_grace_seconds", minimum=1)
    _integer(policy["silence_warning_seconds"], "silence_warning_seconds", minimum=1)
    _integer(policy["hard_timeout_seconds"], "hard_timeout_seconds", minimum=1, nullable=True)


_GROUNDING_SCOPES = {
    "headless-command", "stdin-closure", "permission-trust", "model-discovery",
    "model-inventory", "model-effort-encoding", "output-report-mode",
    "session-resume-fork", "liveness-signal",
}

def _validate_grounding_observed(data: dict[str, Any]) -> None:
    _keys(data, {"receipt_id", "receipt_revision", "storage", "provider", "cache_path", "grounded_at", "expires_at", "executable", "provider_guidance_sha256", "scopes", "model_count", "evidence_commands"})
    _uuid(data["receipt_id"], "receipt_id", nullable=True)
    _integer(data["receipt_revision"], "receipt_revision", minimum=1, nullable=True)
    _enum(data["storage"], "storage", {"cache", "none"})
    _text(data["provider"], "provider")
    _nullable_text(data["cache_path"], "cache_path")
    parse_timestamp(data["grounded_at"])
    if data["expires_at"] is not None:
        parse_timestamp(data["expires_at"])
    _text(data["executable"], "executable")
    if not isinstance(data["provider_guidance_sha256"], str) or not _HASH_RE.fullmatch(data["provider_guidance_sha256"]):
        _fail("provider_guidance_sha256 must be 64 lowercase hexadecimal characters")
    scopes = data["scopes"]
    _text_list(scopes, "scopes", maximum=16, limit=MAX_EVIDENCE_VALUE_CODEPOINTS)
    if len(scopes) != len(set(scopes)) or any(scope not in _GROUNDING_SCOPES for scope in scopes):
        _fail("scopes must contain unique canonical grounding scopes")
    _integer(data["model_count"], "model_count", minimum=0)
    _text_list(data["evidence_commands"], "evidence_commands", maximum=MAX_EVIDENCE_ENTRIES, limit=MAX_EVIDENCE_VALUE_CODEPOINTS)
    if data["storage"] == "none" and any(data[key] is not None for key in ("receipt_revision", "cache_path", "expires_at")):
        _fail("uncached grounding cannot contain cache receipt fields")
    if data["storage"] == "cache" and (data["receipt_id"] is None or data["receipt_revision"] is None or data["cache_path"] is None or data["expires_at"] is None):
        _fail("cached grounding requires receipt fields")


def _validate_grounding_reused(data: dict[str, Any]) -> None:
    _keys(data, {"receipt_id", "receipt_revision", "storage", "provider", "cache_path", "grounded_at", "expires_at", "age_seconds", "executable", "provider_guidance_sha256", "scopes", "model_count"})
    _uuid(data["receipt_id"], "receipt_id")
    _integer(data["receipt_revision"], "receipt_revision", minimum=1)
    if data["storage"] != "cache":
        _fail("grounding-reused.storage must be cache")
    _text(data["provider"], "provider")
    _text(data["cache_path"], "cache_path")
    parse_timestamp(data["grounded_at"])
    parse_timestamp(data["expires_at"])
    _integer(data["age_seconds"], "age_seconds", minimum=0)
    _text(data["executable"], "executable")
    if not isinstance(data["provider_guidance_sha256"], str) or not _HASH_RE.fullmatch(data["provider_guidance_sha256"]):
        _fail("provider_guidance_sha256 must be 64 lowercase hexadecimal characters")
    scopes = data["scopes"]
    _text_list(scopes, "scopes", maximum=16, limit=MAX_EVIDENCE_VALUE_CODEPOINTS)
    if len(scopes) != len(set(scopes)) or any(scope not in _GROUNDING_SCOPES for scope in scopes):
        _fail("scopes must contain unique canonical grounding scopes")
    _integer(data["model_count"], "model_count", minimum=0)


def _validate_provider_outcome(value: Any) -> None:
    data = _dict(value, "data.provider_outcome")
    _keys(data, {"status", "claim", "exit_code", "model_requested", "model_used", "session_id", "stop_reason", "usage", "cost", "result_artifact"}, "data.provider_outcome")
    _enum(data["status"], "provider_outcome.status", STATUSES)
    _text(data["claim"], "provider_outcome.claim")
    if data["exit_code"] is not None and (isinstance(data["exit_code"], bool) or not isinstance(data["exit_code"], int)):
        _fail("provider_outcome.exit_code must be an integer")
    _text(data["model_requested"], "provider_outcome.model_requested")
    _nullable_text(data["model_used"], "provider_outcome.model_used")
    _nullable_text(data["session_id"], "provider_outcome.session_id")
    _nullable_text(data["stop_reason"], "provider_outcome.stop_reason")
    usage = _dict(data["usage"], "provider_outcome.usage")
    _keys(usage, {"input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens", "cache_write_tokens", "total_tokens"}, "provider_outcome.usage")
    for name, value in usage.items():
        _integer(value, f"provider_outcome.usage.{name}", minimum=0, nullable=True)
    cost = data["cost"]
    if cost is not None:
        cost = _dict(cost, "provider_outcome.cost")
        _keys(cost, {"amount", "currency"}, "provider_outcome.cost")
        _number(cost["amount"], "provider_outcome.cost.amount")
        if not isinstance(cost["currency"], str) or not re.fullmatch(r"[A-Z]{3}", cost["currency"]):
            _fail("provider_outcome.cost.currency must be an ISO currency code")
    if data["status"] in {"DONE", "DONE_WITH_CONCERNS"} and data["exit_code"] is None:
        _fail("successful provider outcomes require a concrete exit_code")
    _text(data["result_artifact"], "provider_outcome.result_artifact")


def _validate_repository_verification(value: Any) -> None:
    data = _dict(value, "data.repository_verification")
    _keys(data, {"required", "status", "changed_path_count", "summary", "verification_artifact"}, "data.repository_verification")
    if not isinstance(data["required"], bool):
        _fail("repository_verification.required must be boolean")
    _enum(data["status"], "repository_verification.status", REPOSITORY_STATUSES)
    _integer(data["changed_path_count"], "repository_verification.changed_path_count", minimum=0, nullable=True)
    _text(data["summary"], "repository_verification.summary")
    _nullable_text(data["verification_artifact"], "repository_verification.verification_artifact")
    required = data["required"]
    status = data["status"]
    count = data["changed_path_count"]
    if not required and (status != "NOT_APPLICABLE" or count is not None):
        _fail("non-mutating repository verification must be NOT_APPLICABLE with null changed_path_count")
    if required and status == "NOT_APPLICABLE":
        _fail("mutating repository verification cannot be NOT_APPLICABLE")
    if status in {"VERIFIED", "INVALID_RESULT", "UNCHANGED", "FAILED_TESTS"} and count is None:
        _fail("repository verification status requires changed_path_count")
    if status == "NOT_ATTEMPTED" and count is not None:
        _fail("NOT_ATTEMPTED requires null changed_path_count")


def derive_complete_status(provider_outcome: dict[str, Any], repository_verification: dict[str, Any]) -> str:
    provider_status = provider_outcome["status"]
    repository_status = repository_verification["status"]
    if not repository_verification["required"] or repository_status == "VERIFIED":
        return provider_status
    if repository_status == "NOT_ATTEMPTED":
        return provider_status
    return "BLOCKED"


def _validate_complete(data: dict[str, Any]) -> None:
    _keys(data, {"status", "outcome", "evidence", "provider_outcome", "repository_verification"})
    _enum(data["status"], "status", STATUSES)
    _text(data["outcome"], "outcome")
    _validate_evidence(data["evidence"])
    _validate_provider_outcome(data["provider_outcome"])
    _validate_repository_verification(data["repository_verification"])
    if data["status"] in {"DONE", "DONE_WITH_CONCERNS"} and not data["evidence"]:
        _fail("DONE and DONE_WITH_CONCERNS require evidence")
    provider = data["provider_outcome"]
    repository = data["repository_verification"]
    if repository["required"] and repository["status"] == "NOT_ATTEMPTED":
        if provider["status"] not in {"NEEDS_CONTEXT", "BLOCKED"} or provider["exit_code"] is not None:
            _fail("NOT_ATTEMPTED requires NEEDS_CONTEXT or BLOCKED provider status and null exit_code")
    elif repository["required"] and provider["exit_code"] is None:
        _fail("mutating repository verification requires a provider exit_code")
    expected = derive_complete_status(provider, repository)
    if data["status"] != expected:
        _fail(f"complete.status must be {expected} for provider and repository outcomes")


def _validate_data(event: str, data: dict[str, Any]) -> None:
    if event == "run-started":
        _keys(data, {"kind"})
        _enum(data["kind"], "kind", {"direct", "batch", "sdd"})
    elif event == "run-completed":
        _keys(data, {"status", "outcome"})
        _enum(data["status"], "status", STATUSES)
        _text(data["outcome"], "outcome")
    elif event == "allocated":
        _keys(data, {"role", "contract", "tier", "task"})
        _text(data["role"], "role")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", data["role"]):
            _fail("role must be a compact role identifier")
        if not isinstance(data["contract"], str) or not re.fullmatch(r"\$PLUGIN_ROOT/contracts/[A-Za-z0-9][A-Za-z0-9_.-]*-contract\.md", data["contract"]):
            _fail("contract must be a canonical $PLUGIN_ROOT/contracts/<role>-contract.md path")
        if data["contract"].rsplit("/", 1)[-1] != f"{data['role']}-contract.md":
            _fail("contract basename must match role")
        _text(data["task"], "task")
        _enum(data["tier"], "tier", {"cheapest", "standard", "most-capable"})
    elif event == "grounding-observed":
        _validate_grounding_observed(data)
    elif event == "grounding-reused":
        _validate_grounding_reused(data)
    elif event == "dispatched":
        _keys(data, {"provider", "model", "effort", "attempt", "liveness_policy", "grounding_receipt_id", "grounding_receipt_revision", "grounding_source"})
        _text(data["provider"], "provider")
        _text(data["model"], "model")
        _text(data["effort"], "effort")
        _integer(data["attempt"], "attempt", minimum=1)
        _validate_liveness_policy(data["liveness_policy"])
        _uuid(data["grounding_receipt_id"], "grounding_receipt_id")
        _integer(data["grounding_receipt_revision"], "grounding_receipt_revision", minimum=1, nullable=True)
        _enum(data["grounding_source"], "grounding_source", {"observed", "reused"})
    elif event == "provider-session":
        _keys(data, {"attempt", "provider_session_id"})
        _integer(data["attempt"], "attempt", minimum=1)
        _text(data["provider_session_id"], "provider_session_id")
    elif event == "liveness-warning":
        _keys(data, {"attempt", "elapsed_seconds", "silence_seconds", "process_state", "action"})
        _integer(data["attempt"], "attempt", minimum=1)
        _number(data["elapsed_seconds"], "elapsed_seconds")
        _number(data["silence_seconds"], "silence_seconds", nullable=True)
        _enum(data["process_state"], "process_state", {"running", "exited", "unknown"})
        _enum(data["action"], "action", {"continue", "diagnose", "terminate"})
    elif event == "attempt-failed":
        _keys(data, {"attempt", "signature", "recovery"})
        _integer(data["attempt"], "attempt", minimum=1)
        _text(data["signature"], "signature")
        _text(data["recovery"], "recovery")
    elif event == "resumed":
        _keys(data, {"attempt", "provider_session_id", "reason"})
        _integer(data["attempt"], "attempt", minimum=1)
        _text(data["provider_session_id"], "provider_session_id")
        _text(data["reason"], "reason")
    elif event == "complete":
        _validate_complete(data)
    else:
        _fail(f"unsupported event {event!r}")


def validate_draft(draft: EventDraft, *, for_append: bool = False) -> EventDraft:
    if not isinstance(draft, EventDraft):
        _fail("append input must be EventDraft")
    if draft.event not in EVENTS:
        _fail(f"unsupported event {draft.event!r}")
    _uuid(draft.controller_session_id, "controller_session_id")
    _uuid(draft.run_id, "run_id")
    if draft.event in RUN_EVENTS:
        if draft.job_id is not None:
            _fail("run-level events require null job_id")
    else:
        if draft.job_id is None:
            _fail("job events require a job_id")
        _uuid(draft.job_id, "job_id")
    data = _dict(draft.data, "data")
    if for_append:
        forbidden = {key for key in ("timestamp", "event_id") if key in data}
        if draft.event == "grounding-reused" and "age_seconds" in data:
            forbidden.add("age_seconds")
        if forbidden:
            _fail(f"append input contains caller-owned fields: {', '.join(sorted(forbidden))}")
        if draft.event == "grounding-reused":
            data = dict(data)
            data["age_seconds"] = 0
    _validate_data(draft.event, data)
    return draft


def build_event(draft: EventDraft, *, timestamp: str, event_id: str) -> dict[str, Any]:
    validate_draft(draft)
    parse_timestamp(timestamp)
    _uuid(event_id, "event_id")
    event = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp,
        "event_id": event_id,
        "controller_session_id": draft.controller_session_id,
        "run_id": draft.run_id,
        "job_id": draft.job_id,
        "event": draft.event,
        "data": deepcopy(draft.data),
    }
    validate_event(event)
    return event


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    event = _dict(event, "event")
    _keys(event, {"schema_version", "timestamp", "event_id", "controller_session_id", "run_id", "job_id", "event", "data"}, "event")
    if event["schema_version"] != SCHEMA_VERSION:
        _fail("unsupported schema_version")
    parse_timestamp(event["timestamp"])
    _uuid(event["event_id"], "event_id")
    _uuid(event["controller_session_id"], "controller_session_id")
    _uuid(event["run_id"], "run_id")
    event_name = event["event"]
    if not isinstance(event_name, str) or event_name not in EVENTS:
        _fail("event must be a supported event name")
    if event_name in RUN_EVENTS:
        if event["job_id"] is not None:
            _fail("run-level events require null job_id")
    else:
        _uuid(event["job_id"], "job_id")
    _validate_data(event_name, _dict(event["data"], "data"))
    return event


def encode_event(event: dict[str, Any]) -> bytes:
    validate_event(event)
    try:
        encoded = json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except (TypeError, UnicodeEncodeError) as exc:
        raise LedgerValidationError("event is not JSON encodable") from exc
    if b"\n" in encoded or b"\r" in encoded:
        _fail("encoded event must be one physical line")
    if len(encoded) > MAX_ENCODED_EVENT_BYTES:
        raise LedgerEventTooLarge("encoded ledger event exceeds 65536 bytes")
    return encoded
