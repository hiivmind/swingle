from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import pytest

from swingle.errors import LedgerEventTooLarge, LedgerValidationError
from swingle.ledger import (
    HEADER,
    allocate_job,
    append_event,
    append_events,
    begin_direct,
    finalize_run,
    finish_direct,
    init_ledger,
    read_ledger,
    record_event,
)
from swingle.ledger_schema import EventDraft, build_event, encode_event, new_uuid

SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RECEIPT = "44444444-4444-4444-8444-444444444444"
RUN = "22222222-2222-4222-8222-222222222222"
JOB = "33333333-3333-4333-8333-333333333333"
STAMP = "2026-08-24T04:15:30.123Z"


def draft(event="run-started", *, session=SESSION, run=RUN, job=None, data=None):
    return EventDraft(event, session, run, job, {"kind": "direct"} if data is None else data)


def _worker(path: str, session: str, number: int) -> None:
    append_events(Path(path), session, [draft("provider-session", session=session, job=JOB, data={"attempt": number + 1, "provider_session_id": f"session-{number}"})])


def _valid_opening(session=SESSION, run=RUN, job=JOB):
    return [
        draft("run-started", session=session, run=run, data={"kind": "batch"}),
        draft("allocated", session=session, run=run, job=job, data={"role": "reader", "contract": "$PLUGIN_ROOT/contracts/reader-contract.md", "tier": "standard", "task": "read target"}),
    ]


def _provider(status="DONE", exit_code=0):
    return {"status": status, "claim": "WRITE_OK", "exit_code": exit_code, "model_requested": "provider-default", "model_used": None, "session_id": None, "stop_reason": "end_turn", "usage": {"input_tokens": None, "output_tokens": None, "reasoning_tokens": None, "cache_read_tokens": None, "cache_write_tokens": None, "total_tokens": None}, "cost": None, "result_artifact": "$REPO_ROOT/.swingle/delegate/artifacts/run/job/result.json"}


def _repo(required=True, status="VERIFIED", count=1):
    count = count if required and status != "NOT_ATTEMPTED" else None
    return {"required": required, "status": status, "changed_path_count": count, "summary": "verified", "verification_artifact": "$REPO_ROOT/.swingle/delegate/artifacts/run/job/verification.txt"}


def _complete(session=SESSION, run=RUN, job=JOB, status="DONE", provider_status="DONE", repo_status="VERIFIED", required=True, exit_code=0):
    return draft("complete", session=session, run=run, job=job, data={"status": status, "outcome": "result", "evidence": [{"kind": "report", "value": "result.json"}], "provider_outcome": _provider(provider_status, exit_code), "repository_verification": _repo(required, repo_status)})


def test_session_id_selects_one_lowercase_uuid_filename(tmp_path):
    path, events = append_events(tmp_path, SESSION, [draft()])
    assert path == tmp_path / f"{SESSION}.ndjson"
    assert path.exists() and events[0]["controller_session_id"] == SESSION


def test_append_does_not_read_another_session_file(tmp_path):
    (tmp_path / f"{OTHER_SESSION}.ndjson").write_bytes(b"not json\n")
    path, _ = append_events(tmp_path, SESSION, [draft()])
    assert path.name == f"{SESSION}.ndjson"


def test_concurrent_sessions_create_distinct_files(tmp_path):
    append_events(tmp_path, SESSION, [draft()])
    append_events(tmp_path, OTHER_SESSION, [draft(session=OTHER_SESSION)])
    assert sorted(p.name for p in tmp_path.glob("*.ndjson")) == sorted([f"{SESSION}.ndjson", f"{OTHER_SESSION}.ndjson"])


def test_concurrent_writers_in_one_session_lose_no_events(tmp_path):
    ctx = multiprocessing.get_context("spawn")
    processes = [ctx.Process(target=_worker, args=(str(tmp_path), SESSION, n)) for n in range(8)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    lines = (tmp_path / f"{SESSION}.ndjson").read_text().splitlines()
    assert len(lines) == 8
    assert {json.loads(line)["data"]["provider_session_id"] for line in lines} == {f"session-{n}" for n in range(8)}


def test_multi_event_append_keeps_one_lock_and_order(tmp_path):
    _, events = append_events(tmp_path, SESSION, _valid_opening())
    assert [event["event"] for event in events] == ["run-started", "allocated"]
    assert [json.loads(line)["event"] for line in (tmp_path / f"{SESSION}.ndjson").read_text().splitlines()] == ["run-started", "allocated"]


def test_two_writer_inversion_keeps_per_file_timestamps_monotonic(tmp_path, monkeypatch):
    import swingle.ledger as ledger
    clock = iter(["2026-08-24T04:15:31.000Z", "2026-08-24T04:15:30.000Z"])
    monkeypatch.setattr(ledger, "utc_timestamp", lambda: next(clock))
    append_events(tmp_path, SESSION, [draft()])
    append_events(tmp_path, SESSION, [draft("provider-session", job=JOB, data={"attempt": 1, "provider_session_id": "x"})])
    stamps = [json.loads(line)["timestamp"] for line in (tmp_path / f"{SESSION}.ndjson").read_text().splitlines()]
    assert stamps == ["2026-08-24T04:15:31.000Z", "2026-08-24T04:15:31.000Z"]


def test_equal_clock_timestamps_are_ordered_by_file_offset(tmp_path, monkeypatch):
    import swingle.ledger as ledger
    monkeypatch.setattr(ledger, "utc_timestamp", lambda: STAMP)
    _, events = append_events(tmp_path, SESSION, [draft(), draft("run-completed", data={"status": "DONE", "outcome": "done"})])
    assert events[0]["timestamp"] == events[1]["timestamp"]
    assert [json.loads(line)["event"] for line in (tmp_path / f"{SESSION}.ndjson").read_text().splitlines()] == ["run-started", "run-completed"]


def test_clock_rollback_reuses_last_timestamp(tmp_path, monkeypatch):
    import swingle.ledger as ledger
    clocks = iter(["2026-08-24T04:15:32.000Z", "2026-08-24T04:15:31.000Z"])
    monkeypatch.setattr(ledger, "utc_timestamp", lambda: next(clocks))
    append_events(tmp_path, SESSION, [draft()])
    _, events = append_events(tmp_path, SESSION, [draft("provider-session", job=JOB, data={"attempt": 1, "provider_session_id": "x"})])
    assert events[0]["timestamp"] == "2026-08-24T04:15:32.000Z"


def test_aggregate_order_matches_full_sort_oracle(tmp_path):
    from swingle.ledger import read_events
    append_events(tmp_path, SESSION, _valid_opening())
    append_events(tmp_path, OTHER_SESSION, [draft(session=OTHER_SESSION)])
    observed = list(read_events(tmp_path))
    records = []
    for path in sorted(tmp_path.glob("*.ndjson")):
        offset = 0
        for line in path.read_bytes().splitlines(keepends=True):
            event = json.loads(line)
            records.append((event, offset))
            offset += len(line)
    oracle = [event for event, _ in sorted(records, key=lambda item: (item[0]["timestamp"], item[0]["controller_session_id"], item[1]))]
    assert observed == oracle


def test_append_rejects_caller_timestamp_and_event_id(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [draft(data={"kind": "direct", "timestamp": STAMP})])
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [draft(data={"kind": "direct", "event_id": new_uuid()})])


def test_append_rejects_draft_for_another_controller_before_identity_allocation(tmp_path, monkeypatch):
    import swingle.ledger as ledger
    allocated = []
    monkeypatch.setattr(ledger, "new_uuid", lambda: allocated.append(True) or new_uuid())
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [draft(session=OTHER_SESSION)])
    assert allocated == []
    assert not list(tmp_path.glob("*.ndjson"))


def test_append_rejects_non_event_draft_with_ledger_error(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [object()])
    assert not list(tmp_path.glob("*.ndjson"))


def test_append_rejects_invalid_job_id_before_file_open(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [draft("provider-session", job="not-a-uuid", data={"attempt": 1, "provider_session_id": "p"})])
    assert not list(tmp_path.glob("*.ndjson"))


def test_v2_write_rejects_a_file_as_ledger_directory(tmp_path):
    ledger_file = tmp_path / "ledger"
    ledger_file.write_text("untouched")
    with pytest.raises((NotADirectoryError, ValueError, OSError)):
        append_events(ledger_file, SESSION, [draft()])
    assert ledger_file.read_text() == "untouched"


def test_legacy_exports_remain_importable(tmp_path):
    path = tmp_path / "ledger.md"
    init_ledger(path)
    append_event(path, "legacy event")
    assert path.read_text().startswith(HEADER)
    assert read_ledger(path) == ["legacy event"]


def _context(source="observed", receipt_id=None):
    grounding = {"receipt_id": receipt_id, "receipt_revision": None if source == "observed" else 2, "storage": "none" if source == "observed" else "cache", "provider": "codex", "cache_path": None if source == "observed" else "/p/cache", "grounded_at": STAMP, "expires_at": None if source == "observed" else "2026-08-31T04:15:30.123Z", "executable": "/usr/bin/codex", "provider_guidance_sha256": "0" * 64, "scopes": ["headless-command"], "model_count": 0, "evidence_commands": ["codex --help"]}
    if source != "observed":
        grounding.pop("evidence_commands")
    return {"grounding_source": source, "grounding_event": {"event": "grounding-observed" if source == "observed" else "grounding-reused", "data": grounding}, "liveness_policy": {"check_interval_seconds": 60, "startup_grace_seconds": 300, "silence_warning_seconds": 300, "hard_timeout_seconds": None}}


def _begin(tmp_path, source="observed", receipt_id=None):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    return begin_direct(project=project, ledger_dir=tmp_path / "ledger", controller_session_id=SESSION, role="reader", contract="$PLUGIN_ROOT/contracts/reader-contract.md", tier="standard", task="read", provider="codex", model="provider-default", effort="none", dispatch_context=_context(source, receipt_id))


def test_begin_direct_returns_artifact_directory_and_installs_local_ignore(tmp_path):
    result = _begin(tmp_path)
    artifact = Path(result["artifact_dir"])
    assert artifact == tmp_path.joinpath("project/.swingle/delegate/artifacts", result["run_id"], result["job_id"])
    assert (artifact.parent.parent / ".gitignore").read_text() == "*\n!.gitignore\n"
    assert [json.loads(line)["event"] for line in (tmp_path / "ledger" / f"{SESSION}.ndjson").read_text().splitlines()] == ["run-started", "allocated", "grounding-observed", "dispatched"]


def test_begin_direct_ttl_zero_replaces_null_receipt_sentinel(tmp_path):
    result = _begin(tmp_path)
    event = json.loads((tmp_path / "ledger" / f"{SESSION}.ndjson").read_text().splitlines()[2])
    assert event["data"]["receipt_id"] and result["receipt_id"] == event["data"]["receipt_id"]


def test_cached_receipt_ids_are_python_generated(tmp_path):
    result = _begin(tmp_path, "reused", RECEIPT)
    event = json.loads((tmp_path / "ledger" / f"{SESSION}.ndjson").read_text().splitlines()[2])
    assert event["data"]["receipt_id"] == RECEIPT and result["receipt_id"] == RECEIPT


def test_grounding_reused_age_uses_append_timestamp_after_clock_advance(tmp_path, monkeypatch):
    import swingle.ledger as ledger
    monkeypatch.setattr(ledger, "utc_timestamp", lambda: "2026-08-24T04:16:31.123Z")
    data = {"receipt_id": RECEIPT, "receipt_revision": 1, "storage": "cache", "provider": "codex", "cache_path": "/cache", "grounded_at": STAMP, "expires_at": "2026-08-31T04:15:30.123Z", "executable": "/bin/codex", "provider_guidance_sha256": "0" * 64, "scopes": [], "model_count": 0}
    _, events = append_events(tmp_path, SESSION, [draft("grounding-reused", job=JOB, data=data)])
    assert events[0]["data"]["age_seconds"] == 61


def test_begin_direct_rejects_caller_supplied_observed_receipt(tmp_path):
    with pytest.raises(LedgerValidationError):
        _begin(tmp_path, "observed", RECEIPT)
    assert not list((tmp_path / "ledger").glob("*.ndjson")) if (tmp_path / "ledger").exists() else True


def test_finish_direct_clean_emits_one_lock_final_sequence(tmp_path):
    started = _begin(tmp_path)
    result = finish_direct(ledger_dir=tmp_path / "ledger", controller_session_id=SESSION, run_id=started["run_id"], job_id=started["job_id"], provider_outcome=_provider(), repository_verification=_repo(), outcome="result", evidence=[{"kind": "report", "value": "result.json"}], provider_session_id="provider-1")
    events = result["events"]
    assert [event["event"] for event in events] == ["provider-session", "complete", "run-completed"]
    assert events[0]["data"]["attempt"] == 1
    assert events[1]["data"]["status"] == "DONE"
    assert events[2]["data"] == {"status": "DONE", "outcome": "jobs=1 done=1 done_with_concerns=0 needs_context=0 blocked=0"}


def test_finish_direct_retry_omits_existing_provider_session(tmp_path):
    started = _begin(tmp_path)
    ledger_dir = tmp_path / "ledger"
    record_event(ledger_dir=ledger_dir, controller_session_id=SESSION, run_id=started["run_id"], job_id=started["job_id"], event="attempt-failed", data={"attempt": 1, "signature": "transient", "recovery": "retry"})
    record_event(ledger_dir=ledger_dir, controller_session_id=SESSION, run_id=started["run_id"], job_id=started["job_id"], event="resumed", data={"attempt": 2, "provider_session_id": "provider-2", "reason": "retry"})
    record_event(ledger_dir=ledger_dir, controller_session_id=SESSION, run_id=started["run_id"], job_id=started["job_id"], event="provider-session", data={"attempt": 2, "provider_session_id": "provider-2"})
    result = finish_direct(ledger_dir=ledger_dir, controller_session_id=SESSION, run_id=started["run_id"], job_id=started["job_id"], provider_outcome=_provider(), repository_verification=_repo(), outcome="result", evidence=[{"kind": "report", "value": "result.json"}])
    assert [event["event"] for event in result["events"]] == ["complete", "run-completed"]
    assert result["events"][0]["data"]["status"] == "DONE"
    assert result["events"][1]["data"]["outcome"] == "jobs=1 done=1 done_with_concerns=0 needs_context=0 blocked=0"


def test_controller_supplied_age_seconds_is_rejected(tmp_path):
    data = {"receipt_id": RECEIPT, "receipt_revision": 1, "storage": "cache", "provider": "codex", "cache_path": "/cache", "grounded_at": STAMP, "expires_at": "2026-08-31T04:15:30.123Z", "executable": "/bin/codex", "provider_guidance_sha256": "0" * 64, "scopes": [], "model_count": 0, "age_seconds": 5}
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [draft("grounding-reused", job=JOB, data=data)])


def test_complete_provider_and_repository_outcomes_round_trip(tmp_path):
    _, events = append_events(tmp_path, SESSION, [_complete()])
    loaded = json.loads((tmp_path / f"{SESSION}.ndjson").read_text().splitlines()[0])
    assert loaded["data"]["provider_outcome"] == events[0]["data"]["provider_outcome"]


@pytest.mark.parametrize("repo_status", ["INVALID_RESULT", "UNCHANGED", "FAILED_TESTS"])
def test_mutating_success_rejects_invalid_unchanged_and_failed_tests(tmp_path, repo_status):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [_complete(repo_status=repo_status)])


def test_non_mutating_requires_not_applicable(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [_complete(required=False, repo_status="VERIFIED")])


def test_mutating_rejects_not_applicable(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [_complete(repo_status="NOT_APPLICABLE")])


def test_not_attempted_accepts_only_needs_context_or_blocked(tmp_path):
    for status in ("NEEDS_CONTEXT", "BLOCKED"):
        append_events(tmp_path / status, SESSION, [_complete(status=status, provider_status=status, repo_status="NOT_ATTEMPTED", exit_code=None)])


def test_not_attempted_rejects_non_null_exit_code_after_process_start(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [_complete(status="NEEDS_CONTEXT", provider_status="NEEDS_CONTEXT", repo_status="NOT_ATTEMPTED", exit_code=1)])


def test_every_provider_repository_reconciliation_row(tmp_path):
    for provider_status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
        for repo_status in ("VERIFIED", "INVALID_RESULT", "UNCHANGED", "FAILED_TESTS"):
            target = tmp_path / f"{provider_status}-{repo_status}"
            expected = provider_status if repo_status == "VERIFIED" else "BLOCKED"
            append_events(target, SESSION, [_complete(status=expected, provider_status=provider_status, repo_status=repo_status)])


def test_top_level_status_mismatch_is_rejected(tmp_path):
    with pytest.raises(LedgerValidationError):
        append_events(tmp_path, SESSION, [_complete(status="DONE", provider_status="DONE", repo_status="FAILED_TESTS")])


def test_raw_streams_and_full_path_lists_never_enter_event_data(tmp_path):
    _, events = append_events(tmp_path, SESSION, [_complete()])
    encoded = json.dumps(events[0])
    assert "stdout" not in encoded and "changed_paths" not in encoded


def test_max_size_event_allows_following_append(tmp_path):
    _, events = append_events(tmp_path, SESSION, [draft()])
    assert len(encode_event(events[0])) < 65536
    append_events(tmp_path, SESSION, [draft("run-completed", data={"status": "DONE", "outcome": "done"})])
    assert len((tmp_path / f"{SESSION}.ndjson").read_text().splitlines()) == 2


def _exact_size_complete(target):
    data = _complete().data
    heavy = "💣" * 3500
    provider = data["provider_outcome"]
    for field in ("claim", "model_requested", "model_used"):
        provider[field] = heavy
    data["evidence"] = [{"kind": "report", "value": "x" * 1024} for _ in range(16)]
    for count in range(4096):
        for suffix in range(4):
            if 1 + count + suffix > 4096:
                continue
            data["outcome"] = "x" + "💣" * count + "a" * suffix
            event = build_event(EventDraft("complete", SESSION, RUN, JOB, data), timestamp=STAMP, event_id=new_uuid())
            if len(encode_event(event)) == target:
                return event
    raise AssertionError(f"unable to construct {target}-byte event")

def test_exact_encoded_cap_and_following_append(tmp_path):
    event = _exact_size_complete(65536)
    assert len(encode_event(event)) == 65536
    append_events(tmp_path, SESSION, [EventDraft("complete", SESSION, RUN, JOB, event["data"])])
    assert (tmp_path / f"{SESSION}.ndjson").stat().st_size >= 65537
    append_events(tmp_path, SESSION, [draft("provider-session", job=JOB, data={"attempt": 1, "provider_session_id": "next"})])
    assert len((tmp_path / f"{SESSION}.ndjson").read_bytes().splitlines()) == 2
    oversized = _exact_size_complete(65536)
    oversized["data"]["outcome"] += "a"
    oversized_length = len(json.dumps(oversized, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode())
    assert oversized_length == 65537
    with pytest.raises(LedgerEventTooLarge):
        encode_event(oversized)


def test_run_finalization_one_job_exact_aggregate(tmp_path):
    append_events(tmp_path, SESSION, _valid_opening() + [_complete()])
    _, event = finalize_run(tmp_path, SESSION, RUN)
    assert event["data"] == {"status": "DONE", "outcome": "jobs=1 done=1 done_with_concerns=0 needs_context=0 blocked=0"}


def test_run_finalization_varied_order_mixed_result(tmp_path):
    job2 = "55555555-5555-4555-8555-555555555555"
    append_events(tmp_path, SESSION, [draft("run-started", data={"kind": "batch"}), draft("allocated", job=JOB, data={"role": "reader", "contract": "$PLUGIN_ROOT/contracts/reader-contract.md", "tier": "standard", "task": "one"}), draft("allocated", job=job2, data={"role": "reader", "contract": "$PLUGIN_ROOT/contracts/reader-contract.md", "tier": "standard", "task": "two"}), _complete(job=job2, status="DONE_WITH_CONCERNS", provider_status="DONE_WITH_CONCERNS"), _complete(job=JOB, status="NEEDS_CONTEXT", provider_status="NEEDS_CONTEXT", repo_status="NOT_ATTEMPTED", exit_code=None)])
    _, event = finalize_run(tmp_path, SESSION, RUN)
    assert event["data"]["status"] == "NEEDS_CONTEXT" and event["data"]["outcome"] == "jobs=2 done=0 done_with_concerns=1 needs_context=1 blocked=0"


@pytest.mark.parametrize("case", ["incomplete", "duplicate_start", "existing_completion"])
def test_finalize_run_rejects_incomplete_duplicate_start_or_existing_completion(tmp_path, case):
    opening = _valid_opening()
    if case == "incomplete":
        append_events(tmp_path, SESSION, opening)
    elif case == "duplicate_start":
        append_events(tmp_path, SESSION, opening + [draft("run-started", data={"kind": "batch"}), _complete()])
    else:
        append_events(tmp_path, SESSION, opening + [_complete(), draft("run-completed", data={"status": "DONE", "outcome": "done"})])
    with pytest.raises(LedgerValidationError):
        finalize_run(tmp_path, SESSION, RUN)


def test_stopping_path_terminalizes_then_finalizes(tmp_path):
    append_events(tmp_path, SESSION, _valid_opening() + [_complete(status="BLOCKED", provider_status="BLOCKED", repo_status="NOT_ATTEMPTED", exit_code=None)])
    _, event = finalize_run(tmp_path, SESSION, RUN)
    assert event["data"]["status"] == "BLOCKED"


def test_exactly_one_final_event_valid_ledger_and_no_warnings(tmp_path):
    append_events(tmp_path, SESSION, _valid_opening() + [_complete()])
    finalize_run(tmp_path, SESSION, RUN)
    events = [json.loads(line) for line in (tmp_path / f"{SESSION}.ndjson").read_text().splitlines()]
    assert [event["event"] for event in events].count("run-completed") == 1 and events[-1]["event"] == "run-completed"
