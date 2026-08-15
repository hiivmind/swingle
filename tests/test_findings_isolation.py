"""Cross-entrypoint findings isolation.

As importable modules the shared report.findings persists across calls in one
interpreter — a state that never existed when each script was a fresh process. Every
owning entrypoint must report.reset() first, so a prior failed validation cannot poison
a later call. Asserts on the cleared list, not merely the return code.
"""

import sys

import pytest

from swingle.cli import validate_packs_main
from swingle import models, report
from test_cli_contract import build_multi_region, GOOD, ROOT


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "no-such-xdg"))
    monkeypatch.delenv("SWINGLE_CONFIG", raising=False)
    monkeypatch.delenv("SWINGLE_MODELS", raising=False)


def _run_validate(monkeypatch, root):
    monkeypatch.setattr(sys, "argv", ["validate-packs", "--root", str(root)])
    return validate_packs_main()


def _run_models_which(monkeypatch, root):
    monkeypatch.setattr(sys, "argv", ["swingle-models", "which"])
    return models.main(default_root=root)


def test_failed_validate_does_not_poison_models(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "multi"
    build_multi_region(bad)
    assert _run_validate(monkeypatch, bad) == 1
    assert report.findings  # left populated
    capsys.readouterr()

    rc = _run_models_which(monkeypatch, GOOD)
    out = capsys.readouterr()
    assert rc == 0, out.err
    assert report.findings == []  # models.main reset at entry
    # models output carries only provider layer lines, none of the validate findings
    assert "version mismatch" not in out.out and "purity violation" not in out.out
    assert out.out.strip().splitlines() == [
        "alpha: layer=default path="
        + str((GOOD / "providers/alpha/models.yaml").resolve())
    ]


def test_clean_models_then_validate_reports_only_its_own(monkeypatch, tmp_path, capsys):
    assert _run_models_which(monkeypatch, GOOD) == 0
    capsys.readouterr()
    bad = tmp_path / "multi"
    build_multi_region(bad)
    assert _run_validate(monkeypatch, bad) == 1
    out = capsys.readouterr()
    # exactly the six bad-multi-region findings, no leakage from the prior models run
    assert len(out.out.strip().splitlines()) == 6


def test_repeated_validate_is_reentrant(monkeypatch, tmp_path):
    bad = tmp_path / "multi"
    build_multi_region(bad)
    assert _run_validate(monkeypatch, bad) == 1
    assert _run_validate(monkeypatch, ROOT) == 0
    assert report.findings == []
