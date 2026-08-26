from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Sequence
from uuid import uuid4

from .errors import SwingleError
from .ledger_schema import parse_timestamp, utc_timestamp


GROUNDING_SCOPES = (
    "headless-command",
    "stdin-closure",
    "permission-trust",
    "model-discovery",
    "model-inventory",
    "model-effort-encoding",
    "output-report-mode",
    "session-resume-fork",
    "liveness-signal",
)
SCOPE_STATES = ("observed", "not-exposed", "unverifiable")
_RESERVED_OBSERVATION_KEYS = {
    "argv", "argv_template", "command", "shell", "script", "parser", "program",
    "selector", "selectors", "prompt", "response", "raw_output",
}
_MAX_OBSERVATION_BYTES = 32 * 1024
_MAX_COLLECTION_ENTRIES = 64
_MAX_STRING_CODEPOINTS = 4096
_MAX_INVENTORY_ENTRIES = 10_000
_MAX_ALIASES = 32
_MAX_EFFORT_LEVELS = 32
_MAX_ATTRIBUTES = 32
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class GroundingValidationError(SwingleError):
    code = "grounding_invalid"


class GroundingPackError(GroundingValidationError):
    code = "grounding_invalid_provider_pack"

def _fail(message: str) -> None:
    raise GroundingValidationError(message)


def _text(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        _fail(f"{name} must be a non-empty string")
    if len(value) > _MAX_STRING_CODEPOINTS:
        _fail(f"{name} exceeds {_MAX_STRING_CODEPOINTS} code points")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    try:
        return parse_timestamp(value)
    except (SwingleError, TypeError, ValueError) as exc:
        raise GroundingValidationError(f"{name} must be UTC RFC 3339 with millisecond precision") from exc


def _now(value: datetime | None = None) -> datetime:
    current = datetime.now(timezone.utc) if value is None else value
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return utc_timestamp(value)


def _validate_observation(value: Any, *, depth: int = 0) -> None:
    if depth > 4:
        _fail("observation nesting exceeds depth 4")
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str) and len(value) > _MAX_STRING_CODEPOINTS:
            _fail(f"observation string exceeds {_MAX_STRING_CODEPOINTS} code points")
        return
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            _fail("observation numbers must be finite")
        return
    if isinstance(value, dict):
        if len(value) > _MAX_COLLECTION_ENTRIES:
            _fail("observation collection exceeds 64 entries")
        for key, child in value.items():
            if not isinstance(key, str):
                _fail("observation keys must be strings")
            if key in _RESERVED_OBSERVATION_KEYS:
                _fail(f"observation key is reserved: {key}")
            if len(key) > _MAX_STRING_CODEPOINTS:
                _fail("observation key exceeds 4096 code points")
            _validate_observation(child, depth=depth + 1)
        return
    if isinstance(value, list):
        if len(value) > _MAX_COLLECTION_ENTRIES:
            _fail("observation collection exceeds 64 entries")
        for child in value:
            _validate_observation(child, depth=depth + 1)
        return
    _fail("observation values must be JSON scalars, arrays, or objects")


def _validate_observation_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("observation must be an object")
    _validate_observation(value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GroundingValidationError("observation must be JSON encodable") from exc
    if len(encoded) > _MAX_OBSERVATION_BYTES:
        _fail("observation exceeds 32768 encoded UTF-8 bytes")
    return deepcopy(value)


def _validate_scalar(value: Any, name: str) -> Any:
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str):
            _text(value, name, allow_empty=True)
        return deepcopy(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            _fail(f"{name} must be finite")
        return value
    _fail(f"{name} must be a JSON scalar")


def _validate_models(value: Any, fallback_observed_at: str | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        _fail("models must be an object")
    allowed = {"discovery_command", "observed_at", "entries"}
    unknown = set(value) - allowed
    if unknown:
        _fail(f"models contains unknown fields: {', '.join(sorted(unknown))}")
    result: dict[str, Any] = {}
    if "discovery_command" in value:
        result["discovery_command"] = _text(value["discovery_command"], "models.discovery_command", allow_empty=True)
    if "observed_at" in value and value["observed_at"] is not None:
        _timestamp(value["observed_at"], "models.observed_at")
        result["observed_at"] = value["observed_at"]
    elif fallback_observed_at is not None:
        result["observed_at"] = fallback_observed_at
    entries = value.get("entries", [])
    if not isinstance(entries, list):
        _fail("models.entries must be an array")
    if len(entries) > _MAX_INVENTORY_ENTRIES:
        _fail("models.entries exceeds 10000 entries")
    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        prefix = f"models.entries[{index}]"
        if not isinstance(entry, dict):
            _fail(f"{prefix} must be an object")
        unknown_entry_fields = set(entry) - {"id", "display_name", "aliases", "effort_levels", "input_price", "output_price", "currency", "attributes"}
        if unknown_entry_fields:
            _fail(f"{prefix} contains unknown fields: {', '.join(sorted(unknown_entry_fields))}")
        if not isinstance(entry.get("id"), str) or not entry["id"]:
            _fail(f"{prefix}.id is required")
        item: dict[str, Any] = {"id": _text(entry["id"], f"{prefix}.id")}
        if "display_name" in entry:
            item["display_name"] = _text(entry["display_name"], f"{prefix}.display_name", allow_empty=True)
        aliases = entry.get("aliases", [])
        if not isinstance(aliases, list) or len(aliases) > _MAX_ALIASES:
            _fail(f"{prefix}.aliases must contain at most 32 entries")
        item["aliases"] = [_text(alias, f"{prefix}.aliases") for alias in aliases]
        efforts = entry.get("effort_levels", [])
        if not isinstance(efforts, list) or len(efforts) > _MAX_EFFORT_LEVELS:
            _fail(f"{prefix}.effort_levels must contain at most 32 entries")
        item["effort_levels"] = [_text(effort, f"{prefix}.effort_levels") for effort in efforts]
        for field in ("input_price", "output_price", "currency"):
            if field in entry:
                item[field] = _validate_scalar(entry[field], f"{prefix}.{field}")
            else:
                item[field] = None
        attributes = entry.get("attributes", {})
        if not isinstance(attributes, dict) or len(attributes) > _MAX_ATTRIBUTES:
            _fail(f"{prefix}.attributes must contain at most 32 entries")
        item["attributes"] = {
            _text(key, f"{prefix}.attributes key"): _validate_scalar(attribute, f"{prefix}.attributes.{key}")
            for key, attribute in attributes.items()
        }
        normalized.append(item)
    result["entries"] = normalized
    if "entries" not in value:
        result["entries"] = []
    return result


def _validate_provider(provider: str) -> str:
    if not isinstance(provider, str) or not _PROVIDER_RE.fullmatch(provider):
        _fail("provider must be a safe provider identifier")
    return provider


def _paths(project: Path, provider: str) -> tuple[Path, Path, Path, Path]:
    _validate_provider(provider)
    root = Path(project).expanduser().resolve()
    swingle_dir = root / ".swingle"
    grounding_dir = swingle_dir / "grounding"
    cache_path = grounding_dir / f"{provider}.json"
    lock_path = grounding_dir / f"{provider}.lock"
    return root, swingle_dir, cache_path, lock_path


def dispatch_guidance_sha256(pack_path: Path) -> str:
    try:
        text = Path(pack_path).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise GroundingPackError(f"cannot read provider pack: {pack_path}") from exc
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    headings = [index for index, line in enumerate(lines) if line.strip() == "## Dispatch guidance"]
    if len(headings) != 1:
        raise GroundingPackError("provider pack must contain exactly one Dispatch guidance heading")
    start = headings[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("## "):
            end = index
            break
    section = "\n".join(lines[start:end]).rstrip("\n") + "\n"
    return hashlib.sha256(section.encode("utf-8")).hexdigest()


def _validate_payload(payload: dict[str, Any], *, provider: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        _fail("grounding payload must be an object")
    unknown = set(payload) - {"complete_profile_observed_at", "ttl_seconds", "executable", "provider_guidance_sha256", "scopes", "models"}
    if unknown:
        _fail(f"grounding payload contains unknown fields: {', '.join(sorted(unknown))}")
    ttl = payload.get("ttl_seconds")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 0:
        _fail("ttl_seconds must be a non-negative integer")
    executable = _text(payload.get("executable"), "executable")
    guidance = payload.get("provider_guidance_sha256")
    if not isinstance(guidance, str) or not _HASH_RE.fullmatch(guidance):
        _fail("provider_guidance_sha256 must be 64 lowercase hexadecimal characters")
    scopes = payload.get("scopes", {})
    if not isinstance(scopes, dict):
        _fail("scopes must be an object")
    if any(scope not in GROUNDING_SCOPES for scope in scopes):
        _fail("scopes contains an unknown scope")
    normalized_scopes: dict[str, dict[str, Any]] = {}
    for scope, raw in scopes.items():
        if not isinstance(raw, dict):
            _fail(f"scope {scope} must be an object")
        unknown_scope_fields = set(raw) - {"state", "observation", "applicability", "evidence_command", "observed_at"}
        if unknown_scope_fields:
            _fail(f"scope {scope} contains unknown fields: {', '.join(sorted(unknown_scope_fields))}")
        state = raw.get("state")
        if state not in SCOPE_STATES:
            _fail(f"scope {scope}.state is invalid")
        observation = _validate_observation_object(raw.get("observation", {}))
        applicability = _text(raw.get("applicability", ""), f"scope {scope}.applicability", allow_empty=True)
        evidence = _text(raw.get("evidence_command", ""), f"scope {scope}.evidence_command", allow_empty=True)
        observed_at = raw.get("observed_at")
        _timestamp(observed_at, f"scope {scope}.observed_at")
        normalized_scopes[scope] = {
            "state": state,
            "observation": observation,
            "applicability": applicability,
            "evidence_command": evidence,
            "observed_at": observed_at,
        }
    complete_at = payload.get("complete_profile_observed_at")
    if complete_at is not None:
        _timestamp(complete_at, "complete_profile_observed_at")
        if set(normalized_scopes) != set(GROUNDING_SCOPES):
            _fail("complete_profile_observed_at requires all nine grounding scopes")
    fallback = complete_at or (max((scope["observed_at"] for scope in normalized_scopes.values()), default=None))
    models = _validate_models(payload.get("models"), fallback)
    return {
        "ttl_seconds": ttl,
        "executable": executable,
        "provider_guidance_sha256": guidance,
        "scopes": normalized_scopes,
        "complete_profile_observed_at": complete_at,
        "models": models,
    }


def _compact_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _read_record(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        value = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GroundingValidationError("grounding cache is not valid JSON") from exc
    if not isinstance(value, dict):
        _fail("grounding cache must be an object")
    return value


def _validate_record(record: Any, root: Path, swingle_dir: Path, provider: str) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        _fail("unsupported grounding cache schema")
    unknown = set(record) - {"schema_version", "provider", "project_root", "swingle_dir", "receipt", "invalid_scopes"}
    if unknown:
        _fail(f"grounding cache contains unknown fields: {', '.join(sorted(unknown))}")
    if record.get("provider") != provider or record.get("project_root") != str(root) or record.get("swingle_dir") != str(swingle_dir):
        _fail("grounding cache path or provider does not match")
    receipt = record.get("receipt")
    if not isinstance(receipt, dict):
        _fail("grounding cache receipt is missing")
    unknown_receipt_fields = set(receipt) - {"receipt_id", "revision", "grounded_at", "expires_at", "executable", "provider_guidance_sha256", "mechanics", "models"}
    if unknown_receipt_fields:
        _fail(f"grounding cache receipt contains unknown fields: {', '.join(sorted(unknown_receipt_fields))}")
    rid = receipt.get("receipt_id")
    try:
        uuid = __import__("uuid").UUID(str(rid))
        if str(uuid) != rid:
            raise ValueError
    except (ValueError, AttributeError, TypeError) as exc:
        raise GroundingValidationError("receipt_id must be a UUID") from exc
    revision = receipt.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        _fail("receipt revision must be a positive integer")
    grounded = receipt.get("grounded_at")
    expires = receipt.get("expires_at")
    grounded_at = _timestamp(grounded, "receipt.grounded_at")
    expires_at = _timestamp(expires, "receipt.expires_at")
    if expires_at < grounded_at:
        _fail("receipt.expires_at must not precede grounded_at")
    _text(receipt.get("executable"), "receipt.executable")
    guidance = receipt.get("provider_guidance_sha256")
    if not isinstance(guidance, str) or not _HASH_RE.fullmatch(guidance):
        _fail("receipt.provider_guidance_sha256 is invalid")
    mechanics = receipt.get("mechanics", {})
    if not isinstance(mechanics, dict):
        _fail("receipt.mechanics must be an object")
    for scope, value in mechanics.items():
        if scope not in GROUNDING_SCOPES:
            _fail("receipt.mechanics contains an unknown scope")
        if not isinstance(value, dict):
            _fail(f"receipt.mechanics.{scope} must be an object")
        unknown_mechanic_fields = set(value) - {"state", "observation", "applicability", "evidence_command", "observed_at"}
        if unknown_mechanic_fields:
            _fail(f"receipt.mechanics.{scope} contains unknown fields: {', '.join(sorted(unknown_mechanic_fields))}")
        if value.get("state") not in SCOPE_STATES:
            _fail(f"receipt.mechanics.{scope}.state is invalid")
        _validate_observation_object(value.get("observation", {}))
        _text(value.get("applicability", ""), f"receipt.mechanics.{scope}.applicability", allow_empty=True)
        _text(value.get("evidence_command", ""), f"receipt.mechanics.{scope}.evidence_command", allow_empty=True)
        _timestamp(value.get("observed_at"), f"receipt.mechanics.{scope}.observed_at")
    _validate_models(receipt.get("models", {}), None)
    invalid = record.get("invalid_scopes", {})
    if not isinstance(invalid, dict):
        _fail("invalid_scopes must be an object")
    for scope, value in invalid.items():
        if scope not in GROUNDING_SCOPES:
            _fail("invalid_scopes contains an unknown scope")
        if not isinstance(value, dict):
            _fail(f"invalid_scopes.{scope} must be an object")
        _text(value.get("reason"), f"invalid_scopes.{scope}.reason")
        _timestamp(value.get("invalidated_at"), f"invalid_scopes.{scope}.invalidated_at")
    return record


def _public_receipt(record: dict[str, Any], cache_path: Path) -> dict[str, Any]:
    receipt = deepcopy(record["receipt"])
    receipt["cache_path"] = str(cache_path)
    return receipt


def _result_from_record(record: dict[str, Any], cache_path: Path, *, status: str, required_scopes: Sequence[str], reason: str | None = None) -> dict[str, Any]:
    receipt = _public_receipt(record, cache_path)
    mechanics = deepcopy(receipt.get("mechanics", {}))
    invalid = record.get("invalid_scopes", {})
    usable = all(scope in mechanics and scope not in invalid for scope in required_scopes)
    result: dict[str, Any] = {
        "project_root": record["project_root"],
        "swingle_dir": record["swingle_dir"],
        "cache_path": str(cache_path),
        "status": status,
        "receipt": receipt,
        "mechanics": mechanics,
        "models": deepcopy(receipt.get("models", {})),
        "required_scopes": list(required_scopes),
        "next_action": "dispatch" if status == "usable" and usable else "ground_and_record",
    }
    if reason is not None:
        result["reason"] = reason
    return result


def evaluate_grounding(
    project: Path,
    provider: str,
    *,
    provider_guidance_sha256: str,
    required_scopes: Sequence[str],
    ttl_seconds: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    root, swingle_dir, cache_path, _ = _paths(project, provider)
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds < 0:
        _fail("ttl_seconds must be a non-negative integer")
    if not isinstance(provider_guidance_sha256, str) or not _HASH_RE.fullmatch(provider_guidance_sha256):
        _fail("provider_guidance_sha256 must be 64 lowercase hexadecimal characters")
    required = list(required_scopes)
    if any(scope not in GROUNDING_SCOPES for scope in required) or len(set(required)) != len(required):
        _fail("required_scopes contains an unknown or duplicate scope")
    base = {
        "project_root": str(root), "swingle_dir": str(swingle_dir), "cache_path": str(cache_path),
        "ttl_seconds": ttl_seconds, "required_scopes": required,
    }
    if ttl_seconds == 0:
        base.update({"status": "bypass", "receipt": None, "mechanics": {}, "models": {}, "next_action": "ground_and_record", "storage": "none"})
        return base
    try:
        record = _read_record(cache_path)
        if record is None:
            base.update({"status": "missing", "receipt": None, "mechanics": {}, "models": {}, "next_action": "ground_and_record", "storage": "cache"})
            return base
        _validate_record(record, root, swingle_dir, provider)
    except GroundingValidationError as exc:
        base.update({"status": "invalid", "receipt": None, "mechanics": {}, "models": {}, "next_action": "ground_and_record", "storage": "cache", "reason": str(exc)})
        return base
    receipt = record["receipt"]
    if receipt["provider_guidance_sha256"] != provider_guidance_sha256:
        base.update({"status": "stale", "receipt": _public_receipt(record, cache_path), "mechanics": deepcopy(receipt.get("mechanics", {})), "models": deepcopy(receipt.get("models", {})), "next_action": "ground_and_record", "storage": "cache", "reason": "provider guidance changed"})
        return base
    current = _now(now)
    try:
        expiry = _timestamp(receipt["expires_at"], "receipt.expires_at")
    except GroundingValidationError:
        expiry = current
    if current >= expiry:
        base.update({"status": "stale", "receipt": _public_receipt(record, cache_path), "mechanics": deepcopy(receipt.get("mechanics", {})), "models": deepcopy(receipt.get("models", {})), "next_action": "ground_and_record", "storage": "cache", "reason": "receipt expired"})
        return base
    usable_scopes = [scope for scope in required if scope in receipt.get("mechanics", {}) and scope not in record.get("invalid_scopes", {})]
    if len(usable_scopes) == len(required):
        status = "usable"
    elif set(record.get("invalid_scopes", {})) >= set(GROUNDING_SCOPES):
        status = "invalid"
    else:
        status = "partial"
    result = _result_from_record(record, cache_path, status=status, required_scopes=required)
    result["ttl_seconds"] = ttl_seconds
    result["storage"] = "cache"
    return result


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    encoded = _compact_json(data)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = handle.name
            handle.write(encoded)
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(path.parent)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _ensure_ignore(grounding_dir: Path) -> None:
    path = grounding_dir / ".gitignore"
    if path.exists():
        return
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=grounding_dir, prefix=".gitignore.", delete=False) as handle:
            temporary = handle.name
            handle.write("*\n!.gitignore\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(grounding_dir)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _lock(lock_path: Path):
    handle = lock_path.open("a+")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return handle


def _new_record(root: Path, swingle_dir: Path, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    complete_at = payload["complete_profile_observed_at"]
    if complete_at is not None:
        grounded = _timestamp(complete_at, "complete_profile_observed_at")
    else:
        observed = [_timestamp(value["observed_at"], "scope.observed_at") for value in payload["scopes"].values()]
        grounded = min(observed) if observed else _now()
    grounded_text = _stamp(grounded)
    expires_text = _stamp(grounded + timedelta(seconds=payload["ttl_seconds"]))
    return {
        "schema_version": 1,
        "provider": provider,
        "project_root": str(root),
        "swingle_dir": str(swingle_dir),
        "receipt": {
            "receipt_id": str(uuid4()),
            "revision": 1,
            "grounded_at": grounded_text,
            "expires_at": expires_text,
            "executable": payload["executable"],
            "provider_guidance_sha256": payload["provider_guidance_sha256"],
            "mechanics": deepcopy(payload["scopes"]),
            "models": deepcopy(payload["models"]),
        },
        "invalid_scopes": {},
    }


def _record_event(record: dict[str, Any], cache_path: Path) -> dict[str, Any]:
    receipt = record["receipt"]
    mechanics = receipt["mechanics"]
    return {
        "event": "grounding-observed",
        "data": {
            "receipt_id": receipt["receipt_id"],
            "receipt_revision": receipt["revision"],
            "storage": "cache",
            "provider": record["provider"],
            "cache_path": str(cache_path),
            "grounded_at": receipt["grounded_at"],
            "expires_at": receipt["expires_at"],
            "executable": receipt["executable"],
            "provider_guidance_sha256": receipt["provider_guidance_sha256"],
            "scopes": sorted(mechanics),
            "model_count": len(receipt.get("models", {}).get("entries", [])),
            "evidence_commands": sorted({value.get("evidence_command", "") for value in mechanics.values() if value.get("evidence_command", "")}),
        },
    }


def record_grounding(project: Path, provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    root, swingle_dir, cache_path, lock_path = _paths(project, provider)
    normalized = _validate_payload(payload, provider=provider)
    # TTL zero is deliberately handled before every cache-path operation.
    if normalized["ttl_seconds"] == 0:
        observed_times = [
            value["observed_at"]
            for value in normalized["scopes"].values()
        ]
        if normalized["models"].get("observed_at") is not None:
            observed_times.append(normalized["models"]["observed_at"])
        if not observed_times:
            _fail("TTL-zero grounding requires an observation timestamp")
        grounded_at = max(observed_times)
        evidence_commands = sorted({
            value["evidence_command"]
            for value in normalized["scopes"].values()
            if value["evidence_command"]
        })
        return {
            "status": "recorded",
            "accepted_scopes": sorted(normalized["scopes"]),
            "superseded_scopes": [],
            "receipt": {
                "receipt_id": None,
                "revision": None,
                "storage": "none",
                "cache_path": None,
                "grounded_at": grounded_at,
                "expires_at": None,
                "executable": normalized["executable"],
                "provider_guidance_sha256": normalized["provider_guidance_sha256"],
                "mechanics": deepcopy(normalized["scopes"]),
                "models": deepcopy(normalized["models"]),
            },
            "ledger_event": {
                "event": "grounding-observed",
                "data": {
                    "receipt_id": None,
                    "receipt_revision": None,
                    "storage": "none",
                    "provider": provider,
                    "cache_path": None,
                    "grounded_at": grounded_at,
                    "expires_at": None,
                    "executable": normalized["executable"],
                    "provider_guidance_sha256": normalized["provider_guidance_sha256"],
                    "scopes": sorted(normalized["scopes"]),
                    "model_count": len(normalized["models"].get("entries", [])),
                    "evidence_commands": evidence_commands,
                },
            },
            "next_action": "refresh_context",
            "storage": "none",
        }
    grounding_dir = cache_path.parent
    grounding_dir.mkdir(parents=True, exist_ok=True)
    lock_handle = _lock(lock_path)
    accepted: list[str] = []
    superseded: list[str] = []
    try:
        existing = _read_record(cache_path)
        valid_existing: dict[str, Any] | None = None
        if existing is not None:
            try:
                valid_existing = _validate_record(existing, root, swingle_dir, provider)
            except GroundingValidationError:
                valid_existing = None
        full = normalized["complete_profile_observed_at"] is not None
        stale = False
        if valid_existing is not None:
            try:
                stale = _now() >= _timestamp(valid_existing["receipt"]["expires_at"], "receipt.expires_at")
            except GroundingValidationError:
                stale = True
        replace_full = False
        if valid_existing is not None and full:
            incoming_times = [_timestamp(normalized["complete_profile_observed_at"], "complete_profile_observed_at")]
            incoming_times.extend(_timestamp(observation["observed_at"], "scope.observed_at") for observation in normalized["scopes"].values())
            existing_times = [_timestamp(valid_existing["receipt"]["grounded_at"], "receipt.grounded_at")]
            existing_times.extend(_timestamp(observation["observed_at"], "receipt.scope.observed_at") for observation in valid_existing["receipt"]["mechanics"].values())
            replace_full = max(incoming_times) > max(existing_times)
        if valid_existing is None or (full and replace_full) or (stale and full):
            record = _new_record(root, swingle_dir, provider, normalized)
            accepted = sorted(normalized["scopes"])
            if normalized["models"]:
                accepted = sorted(set(accepted) | {"model-inventory"})
        elif not full:
            record = deepcopy(valid_existing)
            receipt = record["receipt"]
            invalid = record.setdefault("invalid_scopes", {})
            for scope, observation in normalized["scopes"].items():
                old = receipt["mechanics"].get(scope)
                old_time = _timestamp(old["observed_at"], f"receipt.mechanics.{scope}.observed_at") if old else None
                new_time = _timestamp(observation["observed_at"], f"scope {scope}.observed_at")
                invalidation = invalid.get(scope)
                invalid_time = _timestamp(invalidation["invalidated_at"], f"invalid_scopes.{scope}.invalidated_at") if invalidation else None
                if invalid_time is not None and new_time <= invalid_time:
                    superseded.append(scope)
                elif old_time is None or new_time > old_time:
                    receipt["mechanics"][scope] = deepcopy(observation)
                    invalid.pop(scope, None)
                    accepted.append(scope)
                else:
                    superseded.append(scope)
            incoming_models = normalized["models"]
            if incoming_models:
                old_models = receipt.get("models", {})
                old_time = _timestamp(old_models["observed_at"], "receipt.models.observed_at") if old_models.get("observed_at") else None
                new_time = _timestamp(incoming_models["observed_at"], "models.observed_at") if incoming_models.get("observed_at") else None
                if new_time is not None and (old_time is None or new_time > old_time):
                    receipt["models"] = deepcopy(incoming_models)
                    if "model-inventory" not in accepted:
                        accepted.append("model-inventory")
                elif incoming_models:
                    if "model-inventory" not in superseded:
                        superseded.append("model-inventory")
            if accepted:
                receipt["revision"] += 1
        else:
            record = deepcopy(valid_existing)
            superseded = sorted(set(normalized["scopes"]) | ({"model-inventory"} if normalized["models"] else set()))
        _validate_record(record, root, swingle_dir, provider)
        _atomic_write(cache_path, record)
        _ensure_ignore(grounding_dir)
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
    return {
        "status": "recorded",
        "accepted_scopes": sorted(set(accepted)),
        "superseded_scopes": sorted(set(superseded)),
        "receipt": _public_receipt(record, cache_path),
        "ledger_event": _record_event(record, cache_path),
        "next_action": "refresh_context",
        "storage": "cache",
    }


def invalidate_grounding(project: Path, provider: str, scopes: Sequence[str] | None, reason: str) -> dict[str, Any]:
    root, swingle_dir, cache_path, lock_path = _paths(project, provider)
    reason_text = _text(reason, "reason")
    selected = list(GROUNDING_SCOPES if scopes is None else scopes)
    if not selected or any(scope not in GROUNDING_SCOPES for scope in selected) or len(set(selected)) != len(selected):
        _fail("invalid grounding invalidation scopes")
    grounding_dir = cache_path.parent
    if not cache_path.exists():
        return {"status": "missing", "scopes": selected, "reason": reason_text, "next_action": "refresh_context", "cache_path": str(cache_path)}
    lock_handle = _lock(lock_path)
    try:
        raw = _read_record(cache_path)
        if raw is None:
            return {"status": "missing", "scopes": selected, "reason": reason_text, "next_action": "refresh_context", "cache_path": str(cache_path)}
        try:
            record = _validate_record(raw, root, swingle_dir, provider)
        except GroundingValidationError:
            record = raw
        lower_reason = reason_text.casefold()
        non_mechanical = ("permission denied", "quota", "credit", "entitlement", "usage limit", "usage-limit")
        if any(fragment in lower_reason for fragment in non_mechanical):
            return {
                "status": "preserved",
                "scopes": [],
                "reason": reason_text,
                "receipt": _public_receipt(record, cache_path) if isinstance(record, dict) and isinstance(record.get("receipt"), dict) else None,
                "next_action": "refresh_context",
                "cache_path": str(cache_path),
            }
        invalid = record.setdefault("invalid_scopes", {})
        at = _stamp(_now())
        for scope in selected:
            invalid[scope] = {"reason": reason_text, "invalidated_at": at}
        _atomic_write(cache_path, record)
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
    return {"status": "invalidated", "scopes": selected, "reason": reason_text, "receipt": _public_receipt(record, cache_path), "next_action": "refresh_context", "cache_path": str(cache_path)}


def refresh_grounding(project: Path, provider: str, scopes: Sequence[str] | None, reason: str) -> dict[str, Any]:
    result = invalidate_grounding(project, provider, scopes, reason)
    selected = list(GROUNDING_SCOPES if scopes is None else scopes)
    result["scopes"] = selected
    result["next_action"] = "ground_and_record"
    return result
