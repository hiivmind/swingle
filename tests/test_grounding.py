from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import multiprocessing
from pathlib import Path
import uuid

import pytest

from swingle.errors import SwingleError
from swingle.grounding import (
    GROUNDING_SCOPES,
    SCOPE_STATES,
    dispatch_guidance_sha256,
    evaluate_grounding,
    invalidate_grounding,
    record_grounding,
    refresh_grounding,
)


STAMP = "2026-08-24T04:15:30.123Z"
LATER = "2026-08-24T04:16:30.123Z"
HASH = "a" * 64


def _stamp(value: str = STAMP) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _pack(tmp_path: Path, body: str, name: str = "pack.md") -> Path:
    path = tmp_path / name
    path.write_bytes(body.encode())
    return path


def _scope(name: str, *, observed_at: str = STAMP, observation=None, state="observed"):
    return {
        "state": state,
        "observation": {} if observation is None else observation,
        "applicability": "direct dispatch",
        "evidence_command": "provider --help",
        "observed_at": observed_at,
    }


def _payload(*, scopes=None, complete=True, ttl=604800, models=None, executable="/usr/bin/provider", guidance=HASH):
    selected = {name: _scope(name) for name in GROUNDING_SCOPES} if scopes is None else scopes
    return {
        "complete_profile_observed_at": STAMP if complete and set(selected) == set(GROUNDING_SCOPES) else None,
        "ttl_seconds": ttl,
        "executable": executable,
        "provider_guidance_sha256": guidance,
        "scopes": selected,
        "models": {"discovery_command": "provider models", "observed_at": STAMP, "entries": []} if models is None else models,
    }


def _record_worker(project: str, observed_at: str, queue) -> None:
    scopes = {name: _scope(name, observed_at=observed_at) for name in GROUNDING_SCOPES}
    payload = _payload(scopes=scopes)
    queue.put(record_grounding(Path(project), "codex", payload))


def test_fingerprint_normalizes_line_endings_and_adds_one_final_lf(tmp_path):
    lf = _pack(tmp_path, "# Pack\n\n## Dispatch guidance\nline\n", "lf.md")
    crlf = _pack(tmp_path, "# Pack\r\n\r\n## Dispatch guidance\r\nline\r\n", "crlf.md")
    assert dispatch_guidance_sha256(lf) == dispatch_guidance_sha256(crlf)


def test_fingerprint_ignores_gotcha_and_typical_model_edits(tmp_path):
    first = _pack(tmp_path, "# Pack\n## Gotchas\nold\n## Dispatch guidance\nkeep\n## Typical models\none\n", "first.md")
    second = _pack(tmp_path, "# Pack\n## Gotchas\nnew\n## Dispatch guidance\nkeep\n## Typical models\ntwo\n", "second.md")
    assert dispatch_guidance_sha256(first) == dispatch_guidance_sha256(second)


def test_fingerprint_changes_for_dispatch_guidance_edits(tmp_path):
    first = _pack(tmp_path, "# Pack\n## Dispatch guidance\nkeep\n", "first.md")
    second = _pack(tmp_path, "# Pack\n## Dispatch guidance\nchanged\n", "second.md")
    assert dispatch_guidance_sha256(first) != dispatch_guidance_sha256(second)


def test_fingerprint_rejects_missing_duplicate_and_accepts_empty_heading(tmp_path):
    with pytest.raises(SwingleError):
        dispatch_guidance_sha256(_pack(tmp_path, "# Pack\n## Gotchas\nno\n"))
    with pytest.raises(SwingleError):
        dispatch_guidance_sha256(_pack(tmp_path, "## Dispatch guidance\na\n## Dispatch guidance\nb\n"))
    assert dispatch_guidance_sha256(_pack(tmp_path, "# Pack\n## Dispatch guidance\n## Typical models\n"))


def test_cache_isolated_by_canonical_swingle_directory_and_provider(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    payload = _payload()
    first = record_grounding(project / ".", "codex", payload)
    second = record_grounding(project, "claude", payload)
    assert Path(first["receipt"]["cache_path"]).parent == project / ".swingle" / "grounding"
    assert Path(second["receipt"]["cache_path"]).name == "claude.json"
    assert len(list((project / ".swingle" / "grounding").glob("*.json"))) == 2


def test_fixed_expiry_does_not_change_after_config_change(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    first = record_grounding(project, "codex", _payload(ttl=100))
    second = record_grounding(project, "codex", _payload(scopes={"headless-command": _scope("headless-command", observed_at=LATER)}, complete=False, ttl=999))
    assert second["receipt"]["expires_at"] == first["receipt"]["expires_at"]


def test_partial_merge_does_not_extend_receipt_expiry(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    first = record_grounding(project, "codex", _payload(ttl=100))
    partial = _payload(scopes={"headless-command": _scope("headless-command", observed_at=LATER)}, complete=False, ttl=999)
    second = record_grounding(project, "codex", partial)
    assert second["receipt"]["expires_at"] == first["receipt"]["expires_at"]


def test_ttl_zero_does_not_read_or_write_cache(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    cache = project / ".swingle" / "grounding"
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cache opened")))
    result = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=GROUNDING_SCOPES, ttl_seconds=0)
    assert result["status"] == "bypass"
    assert not cache.exists()
    record_grounding(project, "codex", _payload(ttl=0))
    assert not cache.exists()


def test_complete_profile_requires_all_nine_scopes(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    payload = _payload(scopes={"headless-command": _scope("headless-command")}, complete=True)
    payload["complete_profile_observed_at"] = STAMP
    with pytest.raises(SwingleError):
        record_grounding(project, "codex", payload)
    assert not (project / ".swingle").exists()


def test_inventory_limits_and_scalar_attributes(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    too_many = [{"id": str(i)} for i in range(10001)]
    with pytest.raises(SwingleError):
        record_grounding(project, "codex", _payload(models={"discovery_command": "provider models", "observed_at": STAMP, "entries": too_many}))
    with pytest.raises(SwingleError):
        record_grounding(project, "codex", _payload(models={"discovery_command": "provider models", "observed_at": STAMP, "entries": [{"id": "x", "attributes": {"nested": {"bad": True}}}]}))


def test_missing_executable_creates_no_negative_record(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    payload = _payload(executable="")
    with pytest.raises(SwingleError):
        record_grounding(project, "codex", payload)
    assert not (project / ".swingle").exists()


def test_output_shape_hints_round_trip_without_raw_events(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    payload = _payload(scopes={"output-report-mode": _scope("output-report-mode", observation={"format": "jsonl", "completion": "turn.completed"})}, complete=False)
    result = record_grounding(project, "codex", payload)
    shown = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["output-report-mode"], ttl_seconds=604800)
    assert shown["mechanics"]["output-report-mode"]["observation"]["format"] == "jsonl"
    assert "raw_output" not in json.dumps(shown)


def test_permission_tool_class_notes_round_trip(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    payload = _payload(scopes={"permission-trust": _scope("permission-trust", observation={"tool_class_notes": "edit allowed"})}, complete=False)
    record_grounding(project, "codex", payload)
    shown = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["permission-trust"], ttl_seconds=604800)
    assert shown["mechanics"]["permission-trust"]["observation"]["tool_class_notes"] == "edit allowed"


def test_provider_default_and_auto_remain_first_class_candidates(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    models = {"discovery_command": "provider models", "observed_at": STAMP, "entries": [{"id": "provider-default"}, {"id": "auto"}]}
    record_grounding(project, "codex", _payload(models=models))
    shown = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=[], ttl_seconds=604800)
    assert [entry["id"] for entry in shown["models"]["entries"]] == ["provider-default", "auto"]


def test_observation_bounds_and_reserved_keys_are_deterministic(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    for observation in ({"command": "no"}, {"deep": {"a": {"b": {"c": {"d": 1}}}}}, {"long": "x" * 4097}, {"many": list(range(65))}):
        with pytest.raises(SwingleError):
            record_grounding(project, "codex", _payload(scopes={"headless-command": _scope("headless-command", observation=observation)}, complete=False))


def test_provenance_command_fields_remain_permitted_and_inert(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    result = record_grounding(project, "codex", _payload())
    assert result["receipt"]["executable"] == "/usr/bin/provider"
    assert result["receipt"]["mechanics"]["headless-command"]["evidence_command"] == "provider --help"
    assert result["receipt"]["models"]["discovery_command"] == "provider models"


def test_concurrent_disjoint_scope_merges_both_survive(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    q = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=_record_worker, args=(str(project), STAMP, q))
    p2 = multiprocessing.Process(target=_record_worker, args=(str(project), LATER, q))
    p1.start(); p2.start(); p1.join(); p2.join()
    evaluate = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=GROUNDING_SCOPES, ttl_seconds=604800)
    assert set(evaluate["mechanics"]) == set(GROUNDING_SCOPES)


def test_newer_observation_wins_same_scope(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload(scopes={"headless-command": _scope("headless-command", observed_at=LATER)}, complete=False))
    record_grounding(project, "codex", _payload(scopes={"headless-command": _scope("headless-command", observed_at=STAMP, observation={"old": True})}, complete=False))
    result = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["headless-command"], ttl_seconds=604800)
    assert result["mechanics"]["headless-command"]["observed_at"] == LATER


def test_later_invalidation_rejects_older_observation(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    invalidate_grounding(project, "codex", ["headless-command"], "contradiction")
    record_grounding(project, "codex", _payload(scopes={"headless-command": _scope("headless-command", observed_at=STAMP)}, complete=False))
    result = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["headless-command"], ttl_seconds=604800)
    assert result["status"] == "partial"


def test_concurrent_full_profiles_keep_later_observation(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    q = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=_record_worker, args=(str(project), STAMP, q))
    p2 = multiprocessing.Process(target=_record_worker, args=(str(project), LATER, q))
    p1.start(); p2.start(); p1.join(); p2.join()
    result = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["headless-command"], ttl_seconds=604800)
    assert result["mechanics"]["headless-command"]["observed_at"] == LATER


def test_complete_invalidation_preserves_audit_reason(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    result = invalidate_grounding(project, "codex", None, "project moved")
    assert result["reason"] == "project moved"
    raw = json.loads((project / ".swingle" / "grounding" / "codex.json").read_text())
    assert all(item["reason"] == "project moved" for item in raw["invalid_scopes"].values())


def test_scope_invalidation_preserves_other_scopes(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    invalidate_grounding(project, "codex", ["headless-command"], "bad flag")
    result = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=GROUNDING_SCOPES, ttl_seconds=604800)
    assert result["status"] == "partial"
    assert "stdin-closure" in result["mechanics"]


_NON_MECHANICAL_REASONS = ("permission denied", "quota", "credit", "entitlement", "usage-limit")


def _assert_non_mechanical_invalidation(project: Path, reason: str) -> None:
    cache = project / ".swingle" / "grounding" / "codex.json"
    before_bytes = cache.read_bytes()
    before = json.loads(before_bytes)
    result = invalidate_grounding(project, "codex", list(GROUNDING_SCOPES), reason)
    after_bytes = cache.read_bytes()
    after = json.loads(after_bytes)
    assert result["next_action"] == "refresh_context"
    assert after_bytes == before_bytes
    assert after["invalid_scopes"] == before["invalid_scopes"] == {}
    assert after["receipt"] == before["receipt"]
    shown = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=GROUNDING_SCOPES, ttl_seconds=604800)
    assert shown["status"] == "usable"
    assert shown["receipt"] == result["receipt"]


@pytest.mark.parametrize("reason", _NON_MECHANICAL_REASONS)
def test_permission_denial_preserves_mechanics(tmp_path, reason):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    _assert_non_mechanical_invalidation(project, reason)


def test_quota_credit_entitlement_and_usage_limit_preserve_mechanics(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    _assert_non_mechanical_invalidation(project, "quota")


def test_unknown_explicit_model_preserves_inventory_when_cache_never_claimed_it(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    models = {"discovery_command": "provider models", "observed_at": STAMP, "entries": [{"id": "known"}]}
    record_grounding(project, "codex", _payload(models=models))
    result = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["model-inventory"], ttl_seconds=604800)
    assert result["status"] == "usable"
    assert result["models"]["entries"][0]["id"] == "known"


def test_rejected_cached_command_shape_invalidates_only_affected_scope(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    result = invalidate_grounding(project, "codex", ["headless-command"], "rejected command shape")
    assert result["scopes"] == ["headless-command"]
    shown = evaluate_grounding(project, "codex", provider_guidance_sha256=HASH, required_scopes=["headless-command", "stdin-closure"], ttl_seconds=604800)
    assert shown["status"] == "partial"
    assert shown["mechanics"]["stdin-closure"]["state"] == "observed"


def test_executable_failure_and_refresh_are_non_execution_paths(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    record_grounding(project, "codex", _payload())
    assert invalidate_grounding(project, "codex", None, "reported executable launch failure")["next_action"] == "refresh_context"
    assert refresh_grounding(project, "codex", ["headless-command"], "user-request")["next_action"] == "ground_and_record"
