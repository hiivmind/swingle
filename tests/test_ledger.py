from multiprocessing import get_context
from pathlib import Path

import pytest

from swingle.ledger import HEADER, append_event, init_ledger, read_ledger


def _append_worker(path: str, number: int) -> None:
    append_event(Path(path), f"{number:03d} complete: status=DONE outcome=ok")


def test_init_is_idempotent(tmp_path):
    path = tmp_path / "ledger.md"
    init_ledger(path)
    init_ledger(path)
    assert path.read_text() == HEADER


def test_append_preserves_order_and_prior_content(tmp_path):
    path = tmp_path / "ledger.md"
    append_event(path, "001 allocated: role=reader task=a contract=reader tier=standard")
    append_event(path, "001 complete: status=DONE outcome=answer-returned")

    assert read_ledger(path) == [
        "001 allocated: role=reader task=a contract=reader tier=standard",
        "001 complete: status=DONE outcome=answer-returned",
    ]


def test_append_rejects_multiline_events(tmp_path):
    with pytest.raises(ValueError, match="one line"):
        append_event(tmp_path / "ledger.md", "001 allocated\ncorrupt")


def test_concurrent_process_appends_lose_no_events(tmp_path):
    path = tmp_path / "ledger.md"
    processes = [
        get_context("spawn").Process(target=_append_worker, args=(str(path), number))
        for number in range(12)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0

    events = read_ledger(path)
    assert sorted(events) == [
        f"{number:03d} complete: status=DONE outcome=ok"
        for number in range(12)
    ]
