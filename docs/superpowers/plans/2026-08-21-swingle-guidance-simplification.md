# Swingle Guidance Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace provider certification with live CLI guidance while retaining contracts, advisory preferences, and a durable delegation ledger.

**Architecture:** Swingle remains a SKILLS plugin. The Python CLI manages only Swingle configuration, ledgers, provider-note structure, and repository integrity. The LLM controls provider commands and uses current CLI help.

**Tech Stack:** Python 3 standard library, pytest, Markdown skills, JSON configuration, POSIX file locking.

**Spec:** `docs/specs/2026-08-21-swingle-guidance-simplification-design.md`

## Global Constraints

- The LLM is the controller.
- The live provider CLI is the authority for provider operation.
- Python code must not run provider or controller binaries.
- Provider notes contain only real, non-obvious failure guidance.
- Preferences never define provider or model availability.
- Keep all four role contracts and the Markdown ledger.
- Keep `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, and `BLOCKED`.
- Remove Swingle worktree, superpowers, controller-adapter, version, readiness, and model-certification policy.
- Do not add compatibility readers for removed provider registries or model tables.
- Do not change plugin versions. The release branch owns the version change.
- Create the implementation branch from `develop` only after the user confirms the branch seed.
- Open the implementation pull request against `develop`.

## Target File Structure

```text
lib/swingle/
  __init__.py
  cli.py          # argparse entry point for Swingle-owned commands
  config.py       # configuration precedence, normalization, and writes
  ledger.py       # Markdown ledger initialization, locking, append, and read
  providers.py    # provider-note parser and structural checks
  check.py        # repository-owned integrity checks
scripts/
  swingle         # one Python shim
skills/
  delegate/SKILL.md
  swingle-setup/SKILL.md
  sdd/SKILL.md
contracts/
  implementer-contract.md
  reader-contract.md
  task-reviewer-contract.md
  design-reviewer-contract.md
providers/<id>/pack.md
```

Remove the old runtime modules, controller adapters, certification data, and provider catalogs.

---

### Task 1: Advisory Configuration Core

**Files:**
- Replace: `lib/swingle/config.py`
- Create: `tests/test_config.py`
- Remove later in Task 4: old configuration fixtures under `tests/fixtures/`

**Interfaces:**
- Consumes: provider IDs as a `set[str]`. It does not use provider runtime.
- Produces: `ConfigResult`, `resolve_config_path()`, `load_config()`, `init_config()`, and `set_config_value()`.

- [ ] **Step 1: Write configuration tests**

Create `tests/test_config.py` with these tests:

```python
import json
from pathlib import Path

from swingle.config import (
    DEFAULT_CONFIG,
    init_config,
    load_config,
    resolve_config_path,
    set_config_value,
)

PROVIDERS = {"codex", "grok"}


def test_whole_file_precedence_env_project_user(tmp_path, monkeypatch):
    user = tmp_path / "xdg" / "swingle" / "config.json"
    project = tmp_path / "project"
    project.mkdir()
    project_file = project / ".swingle.json"
    env_file = tmp_path / "env.json"
    for path, provider in ((user, "codex"), (project_file, "grok"), (env_file, "codex")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"default_provider": provider}))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("SWINGLE_CONFIG", str(env_file))

    layer, path = resolve_config_path(project=project)

    assert layer == "env"
    assert path == env_file


def test_model_preferences_are_ordered_hints(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "model_preferences": {
            "codex": {"standard": ["future-model", "current-model"]}
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["model_preferences"]["codex"]["standard"] == [
        "future-model", "current-model"
    ]
    assert result.errors == ()


def test_bad_optional_preference_warns_and_drops_only_that_row(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "default_provider": "codex",
        "model_preferences": {
            "codex": {
                "standard": "not-a-list",
                "cheapest": ["small-model"]
            }
        }
    }))

    result = load_config(path, PROVIDERS)

    assert result.config["default_provider"] == "codex"
    assert result.config["model_preferences"]["codex"] == {
        "cheapest": ["small-model"]
    }
    assert any("standard" in warning for warning in result.warnings)
    assert result.errors == ()


def test_removed_keys_warn_and_have_no_effect(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "require-verified-version": True,
        "superpowers": {"codex": {"installed": False}}
    }))

    result = load_config(path, PROVIDERS)

    assert result.config == DEFAULT_CONFIG
    assert {warning.split(":", 1)[0] for warning in result.warnings} == {
        "require-verified-version", "superpowers"
    }
    assert result.errors == ()


def test_malformed_json_returns_defaults_and_error(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bad json")

    result = load_config(path, PROVIDERS)

    assert result.config == DEFAULT_CONFIG
    assert result.errors


def test_init_and_set_configuration(tmp_path):
    path = tmp_path / "config.json"
    init_config(path)
    set_config_value(
        path,
        "model_preferences.codex.standard",
        '["preferred", "fallback"]',
        PROVIDERS,
    )

    result = load_config(path, PROVIDERS)

    assert result.config["model_preferences"]["codex"]["standard"] == [
        "preferred", "fallback"
    ]
```

- [ ] **Step 2: Run the tests and observe the expected failure**

Run:

```bash
uv run --with pytest pytest tests/test_config.py -q
```

Expected: import errors for the new configuration interfaces.

- [ ] **Step 3: Replace the configuration implementation**

Implement this public shape in `lib/swingle/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

LANES = ("implement", "review")
TIERS = ("cheapest", "standard", "most-capable")
DEFAULT_CONFIG = {
    "disable": [],
    "providers_by_lane": {},
    "model_preferences": {},
}
KNOWN_KEYS = {
    "disable", "default_provider", "providers_by_lane", "model_preferences"
}
REMOVED_KEYS = {"require-verified-version", "superpowers", "note"}


@dataclass(frozen=True)
class ConfigResult:
    config: dict[str, Any]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def resolve_config_path(
    explicit: str | Path | None = None,
    project: str | Path | None = None,
) -> tuple[str, Path | None]:
    candidate = Path(explicit) if explicit else None
    if candidate is None and os.environ.get("SWINGLE_CONFIG"):
        candidate = Path(os.environ["SWINGLE_CONFIG"])
    if candidate is not None:
        return "env", candidate
    if project is not None:
        project_path = Path(project) / ".swingle.json"
        if project_path.is_file():
            return "project", project_path
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    user_path = xdg / "swingle" / "config.json"
    if user_path.is_file():
        return "user", user_path
    return "none", None
```

Complete `load_config()` with these rules:

- Return a new copy of `DEFAULT_CONFIG` when no file exists.
- Return defaults plus one error for unreadable JSON or a non-object root.
- Treat removed and unknown keys as warnings. Remove those keys.
- Treat malformed `disable`, `default_provider`, and `providers_by_lane` as errors.
- Treat malformed `model_preferences` rows as warnings. Remove only those rows.
- Keep model preference order.
- Validate provider names only against `provider_ids`.
- Never inspect a provider executable.

Implement `init_config(path, force=False)` as an idempotent neutral-file writer.

Implement `set_config_value(path, dotted_key, json_value, provider_ids)` as a validated nested update.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
uv run --with pytest pytest tests/test_config.py -q
```

Expected: all configuration tests pass.

- [ ] **Step 5: Commit the configuration core**

```bash
git add lib/swingle/config.py tests/test_config.py
git commit -m "refactor(config): make model selection advisory"
```

---

### Task 2: Atomic Markdown Ledger

**Files:**
- Create: `lib/swingle/ledger.py`
- Create: `tests/test_ledger.py`

**Interfaces:**
- Consumes: a ledger path and one complete event line.
- Produces: `init_ledger()`, `append_event()`, and `read_ledger()`.

- [ ] **Step 1: Write ledger tests**

Create `tests/test_ledger.py`:

```python
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
    append_event(path, "001 allocated: role=reader task=a contract=reader")
    append_event(path, "001 complete: status=DONE outcome=answer-returned")

    assert read_ledger(path) == [
        "001 allocated: role=reader task=a contract=reader",
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
```

- [ ] **Step 2: Run the tests and observe the expected failure**

Run:

```bash
uv run --with pytest pytest tests/test_ledger.py -q
```

Expected: `ModuleNotFoundError` for `swingle.ledger`.

- [ ] **Step 3: Implement the ledger**

Create `lib/swingle/ledger.py` with this structure:

```python
from __future__ import annotations

import fcntl
import os
from pathlib import Path

HEADER = "# Swingle delegation ledger\n\n"


def _locked_file(path: Path, mode: str, lock: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open(mode, encoding="utf-8")
    fcntl.flock(handle.fileno(), lock)
    return handle


def init_ledger(path: Path) -> None:
    handle = _locked_file(path, "a+", fcntl.LOCK_EX)
    try:
        handle.seek(0)
        content = handle.read()
        if not content:
            handle.write(HEADER)
            handle.flush()
            os.fsync(handle.fileno())
        elif not content.startswith(HEADER):
            raise ValueError(f"{path}: invalid Swingle ledger header")
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def append_event(path: Path, event: str) -> None:
    if not event or "\n" in event or "\r" in event:
        raise ValueError("ledger event must be one non-empty line")
    init_ledger(path)
    handle = _locked_file(path, "a", fcntl.LOCK_EX)
    try:
        handle.write(event + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def read_ledger(path: Path) -> list[str]:
    init_ledger(path)
    handle = _locked_file(path, "r", fcntl.LOCK_SH)
    try:
        lines = handle.read().splitlines()
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
    return [line for line in lines[2:] if line]
```

Do not add provider fields to this module. The event string is the stable universal boundary.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
uv run --with pytest pytest tests/test_ledger.py -q
```

Expected: all ledger tests pass.

- [ ] **Step 5: Commit the ledger**

```bash
git add lib/swingle/ledger.py tests/test_ledger.py
git commit -m "feat(ledger): add atomic delegation audit log"
```

---

### Task 3: Provider Gotcha Notes and Structural Checks

**Files:**
- Create: `lib/swingle/providers.py`
- Create: `lib/swingle/check.py`
- Create: `tests/test_providers.py`
- Replace: `providers/*/pack.md`
- Remove: `providers/*/versions/`
- Remove: `providers/*/log/`
- Remove: `providers/*/verification-log.md`
- Remove: `providers/*/models.yaml`
- Remove: `providers/*/models.md`

**Interfaces:**
- Consumes: Markdown provider notes.
- Produces: `ProviderNote`, `load_provider_note()`, `load_provider_notes()`, and `check_repository()`.

- [ ] **Step 1: Write provider-note tests**

Create `tests/test_providers.py`:

```python
from pathlib import Path

from swingle.check import check_repository
from swingle.providers import load_provider_note


def write_note(root: Path, body: str) -> Path:
    path = root / "providers" / "alpha" / "pack.md"
    path.parent.mkdir(parents=True)
    path.write_text(body)
    return path


def test_parse_provider_note(tmp_path):
    path = write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| exits 0 with no file | requested write is missing | inspect current permission help and retry | issue #1 |
""")

    note = load_provider_note(path)

    assert note.provider_id == "alpha"
    assert note.cli == "alpha"
    assert note.gotchas[0].signature == "exits 0 with no file"


def test_empty_gotcha_table_is_valid(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
""")

    assert check_repository(tmp_path) == []


def test_note_rejects_wrong_columns(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Command | Models |
| --- | --- |
""")

    findings = check_repository(tmp_path)

    assert any("gotcha-table columns" in finding for finding in findings)


def test_note_rejects_missing_evidence(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| silent success | requested file is missing | inspect current help and retry | |
""")

    findings = check_repository(tmp_path)

    assert any("invalid gotcha row" in finding for finding in findings)


def test_provider_directory_rejects_certification_assets(tmp_path):
    write_note(tmp_path, """# Alpha gotchas

CLI: `alpha`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
""")
    (tmp_path / "providers" / "alpha" / "models.yaml").write_text("models: []\n")

    findings = check_repository(tmp_path)

    assert any("unexpected provider asset" in finding for finding in findings)
```

- [ ] **Step 2: Run the tests and observe the expected failure**

Run:

```bash
uv run --with pytest pytest tests/test_providers.py -q
```

Expected: import errors for `swingle.providers` and `swingle.check`.

- [ ] **Step 3: Implement the provider-note parser**

Create `lib/swingle/providers.py` with immutable records:

```python
from dataclasses import dataclass
from pathlib import Path
import re

TITLE_RE = re.compile(r"^# .+ gotchas$")
CLI_RE = re.compile(r"^CLI: `([a-z0-9-]+)`$")
TABLE_HEADER = "| Failure signature | Impact | Recovery | Evidence |"
TABLE_RULE = "| --- | --- | --- | --- |"


@dataclass(frozen=True)
class Gotcha:
    signature: str
    impact: str
    recovery: str
    evidence: str


@dataclass(frozen=True)
class ProviderNote:
    provider_id: str
    cli: str
    gotchas: tuple[Gotcha, ...]


def _table_cells(line: str) -> tuple[str, ...]:
    if not line.startswith("|") or not line.endswith("|"):
        raise ValueError("gotcha row must start and end with |")
    return tuple(cell.strip() for cell in line[1:-1].split("|"))


def load_provider_note(path: Path) -> ProviderNote:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not TITLE_RE.fullmatch(lines[0]):
        raise ValueError(f"{path}: first line must be '# <Provider> gotchas'")
    cli_lines = [CLI_RE.fullmatch(line) for line in lines]
    cli_values = [match.group(1) for match in cli_lines if match]
    if len(cli_values) != 1:
        raise ValueError(f"{path}: expected one CLI identity")
    if cli_values[0] != path.parent.name:
        raise ValueError(f"{path}: CLI identity must match provider directory")
    if lines.count(TABLE_HEADER) != 1:
        raise ValueError(f"{path}: expected the gotcha-table columns")
    header = lines.index(TABLE_HEADER)
    if header + 1 >= len(lines) or lines[header + 1] != TABLE_RULE:
        raise ValueError(f"{path}: invalid gotcha-table separator")
    gotchas = []
    for number, line in enumerate(lines[header + 2:], header + 3):
        if not line.strip():
            continue
        cells = _table_cells(line)
        if len(cells) != 4 or any(not cell for cell in cells):
            raise ValueError(f"{path}:{number}: invalid gotcha row")
        gotchas.append(Gotcha(*cells))
    return ProviderNote(path.parent.name, cli_values[0], tuple(gotchas))


def load_provider_notes(root: Path) -> dict[str, ProviderNote]:
    return {
        path.parent.name: load_provider_note(path)
        for path in sorted((root / "providers").glob("*/pack.md"))
    }
```

The parser requires four non-empty cells. Evidence is mandatory for every gotcha.

- [ ] **Step 4: Implement repository checks**

Create `lib/swingle/check.py`.

`check_repository(root)` must return `list[str]` and perform these checks:

- Every provider directory contains only `pack.md`.
- Each note parses with `load_provider_note()`.
- The provider heading and CLI identity match the directory.
- Markdown links in tracked documentation resolve to files and headings.
- Skill references to retained contracts resolve.
- The check never reads `PATH` and never runs a subprocess.

Use the existing link parser from `lib/swingle/audit/repo.py` only as source material. Do not retain version, registry, model, purity, or log checks.

- [ ] **Step 5: Replace provider packs with gotcha tables**

Use one `pack.md` per provider. Keep only these evidence-backed rows:

| Provider | Retained failure signatures |
| --- | --- |
| `codex` | open stdin waits for end-of-input and prevents completion |
| `claude` | headless write exits successfully but leaves no change after an unanswered permission request. Nested Claude inherits parent-only environment and refuses the intended write. A never-closing non-TTY stdin pipe makes `claude -p` hang until killed |
| `agy` | signed-out or permission-denied headless run exits successfully with no work. Artifact diversion causes a missing workspace report. Buffered output gives no progress signal |
| `grok` | single-object JSON output buffers until exit and can appear stalled |
| `opencode` | open stdin hangs. Intermittent background startup produces no output until killed and retried |
| `pi` | open stdin can end in `RangeError: Invalid string length` |
| `omp` | no current row passes the inclusion test. Keep an empty table |

For the Claude pipe-stdin row, close stdin with `/dev/null`. Cite issue #73 and `providers/claude/log/2026-07.md`.

For each row:

- Use an observable signature from the existing provider body or log.
- State one impact.
- State one proven recovery.
- Cite the former log path and date, an issue, or a commit.
- Do not copy command tutorials, model names, version claims, or positive capability facts.

- [ ] **Step 5a: Reconcile open provider-guidance PR #55**

Run:

```bash
gh pr view 55 --json state,title,headRefName,baseRefName,url
gh pr diff 55
```

If PR #55 is open, apply the gotcha inclusion rules to each proposed opencode caveat.
Keep a session-attribution caveat only when normal help is insufficient or misleading.
Exclude a basic command tutorial that current help supplies.
Record that the new implementation pull request will supersede PR #55.

- [ ] **Step 6: Remove certification assets**

Remove every provider file except `pack.md`:

```bash
rm -rf providers/*/versions providers/*/log
rm -f providers/*/verification-log.md providers/*/models.yaml providers/*/models.md
```

Review the removal list before the command. Do not remove any `pack.md`.

- [ ] **Step 7: Run provider checks**

Run:

```bash
uv run --with pytest pytest tests/test_providers.py -q
```

Expected: all provider-note tests pass.

Run:

```bash
PYTHONPATH=lib python3 -c 'from pathlib import Path; from swingle.check import check_repository; findings=check_repository(Path(".")); print("\n".join(findings)); raise SystemExit(bool(findings))'
```

Expected: exit 0 and no output.

Continue without a commit. The provider format and old runtime must change in one atomic task.

#### Task 3 continuation: Unified Swingle CLI and Certification Removal

**Files:**
- Replace: `lib/swingle/cli.py`
- Create: `scripts/swingle`
- Create: `tests/test_cli.py`
- Modify: `.github/workflows/release.yml`
- Remove: `lib/swingle/environment.py`
- Remove: `lib/swingle/models.py`
- Remove: `lib/swingle/packs.py`
- Remove: `lib/swingle/report.py`
- Remove: `lib/swingle/resolve.py`
- Remove: `lib/swingle/step0.py`
- Remove: `lib/swingle/audit/`
- Remove: `scripts/validate-packs`
- Remove: `scripts/swingle-models`
- Remove: `scripts/shard-logs`
- Remove: `scripts/codex-smoke`
- Remove: `scripts/opencode-skills-path`
- Remove: obsolete validator tests and fixtures

**Interfaces:**
- Consumes: Tasks 1 and 2 plus the provider notes in this task.
- Produces: `main(argv: list[str] | None = None, *, default_root: Path | None = None) -> int` and `scripts/swingle`.

- [ ] **Step 8: Write CLI contract tests**

Create `tests/test_cli.py`:

```python
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "swingle"


def run_cli(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_config_show_returns_machine_readable_effective_configuration(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"default_provider": "codex"}))

    result = run_cli("config", "show", "--config", str(path), "--root", str(ROOT))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["layer"] == "env"
    assert payload["config"]["default_provider"] == "codex"


def test_config_validate_reports_malformed_json(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bad")

    result = run_cli("config", "validate", str(path), "--root", str(ROOT))

    assert result.returncode == 1
    assert "errors" in json.loads(result.stdout)


def test_ledger_cli_round_trip(tmp_path):
    path = tmp_path / "ledger.md"

    assert run_cli("ledger", "init", "--path", str(path)).returncode == 0
    assert run_cli(
        "ledger", "append", "--path", str(path),
        "001 allocated: role=reader task=a contract=reader",
    ).returncode == 0
    result = run_cli("ledger", "show", "--path", str(path))

    assert result.returncode == 0
    assert json.loads(result.stdout)["events"] == [
        "001 allocated: role=reader task=a contract=reader"
    ]


def test_check_runs_repository_owned_checks(tmp_path):
    result = run_cli("check", "--root", str(ROOT))
    assert result.returncode == 0, result.stdout + result.stderr


def test_python_cli_never_runs_provider_binaries(tmp_path):
    marker = tmp_path / "provider-ran"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for cli in ("agy", "claude", "codex", "grok", "omp", "opencode", "pi"):
        path = bin_dir / cli
        path.write_text(f"#!/bin/sh\ntouch {marker}\n")
        path.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")

    config_path = tmp_path / "boundary-config.json"
    ledger_path = tmp_path / "boundary-ledger.md"
    commands = (
        ("config", "init", "--path", str(config_path)),
        ("config", "show", "--config", str(config_path), "--root", str(ROOT)),
        ("config", "validate", str(config_path), "--root", str(ROOT)),
        (
            "config", "set", "--path", str(config_path),
            "default_provider", '"codex"', "--root", str(ROOT),
        ),
        ("ledger", "init", "--path", str(ledger_path)),
        (
            "ledger", "append", "--path", str(ledger_path),
            "001 complete: status=DONE outcome=ok",
        ),
        ("ledger", "show", "--path", str(ledger_path)),
        ("check", "--root", str(ROOT)),
    )
    for command in commands:
        result = run_cli(*command, env=env)
        assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists()
```

- [ ] **Step 9: Run the CLI tests and observe the expected failure**

Run:

```bash
uv run --with pytest pytest tests/test_cli.py -q
```

Expected: failures because `scripts/swingle` does not exist.

- [ ] **Step 10: Replace the CLI entry point**

Implement `lib/swingle/cli.py` with one `argparse` tree:

Define the entry point with this exact signature:

```python
def main(
    argv: list[str] | None = None,
    *,
    default_root: Path | None = None,
) -> int:
```

```text
swingle config init (--user | --project PATH | --path PATH) [--force]
swingle config show [--config PATH] [--project PATH] [--root PATH]
swingle config validate PATH [--root PATH]
swingle config set --path PATH KEY JSON_VALUE [--root PATH]
swingle ledger init --path PATH
swingle ledger append --path PATH EVENT
swingle ledger show --path PATH
swingle check [--root PATH]
```

All structured output must be JSON. Errors go in an `errors` array and use exit 1.

`config show` returns:

```json
{
  "layer": "env|project|user|none",
  "path": "<absolute path or null>",
  "config": {},
  "warnings": [],
  "errors": []
}
```

Use `load_provider_notes(root)` only to validate provider names. Do not inspect executables.

- [ ] **Step 10a: Update the release workflow**

Replace the release-head command in `.github/workflows/release.yml`:

```yaml
- name: Check Swingle at the release head
  if: steps.tag.outputs.exists == 'false'
  run: python3 scripts/swingle check --root .
```

Remove every release-workflow reference to `scripts/validate-packs`.

- [ ] **Step 11: Add the command shim**

Create executable `scripts/swingle`:

```python
#!/usr/bin/env python3
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "lib"))

from swingle.cli import main

raise SystemExit(main(default_root=root))
```

- [ ] **Step 12: Remove old modules, scripts, tests, and fixtures**

Remove these test files because they enforce retired behavior:

```text
tests/test_validate_packs.py
tests/test_step0_lockstep.py
tests/test_findings_isolation.py
tests/test_shard_logs.py
tests/test_cli_contract.py
tests/test_delegate_skill.py
tests/test_setup_skill.py
```

Remove all old `tests/fixtures/` content. Later tasks add no provider-runtime fixtures.

Task 4 creates replacement skill tests against the new skill boundaries.

- [ ] **Step 13: Run configuration, ledger, provider, and CLI tests**

Run:

```bash
uv run --with pytest pytest tests/test_config.py tests/test_ledger.py tests/test_providers.py tests/test_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 14: Run the new authoring command**

Run:

```bash
python3 scripts/swingle check --root .
```

Expected: JSON with an empty `errors` array and exit 0.

- [ ] **Step 15: Commit the runtime clean cut**

```bash
git add lib scripts tests providers .github/workflows/release.yml
git commit -m "refactor(runtime): replace provider certification with guidance"
```

---

### Task 4: Skills, Contracts, and Controller Boundary

**Files:**
- Replace: `skills/delegate/SKILL.md`
- Replace: `skills/swingle-setup/SKILL.md`
- Replace: `skills/sdd/SKILL.md`
- Update: three `skills/*/agents/openai.yaml` files
- Remove: `skills/swingle-verify/`
- Replace: `contracts/*.md`
- Create: `tests/test_skills.py`
- Remove: `controllers/`
- Remove: `core/`
- Remove: `archive/`

**Interfaces:**
- Consumes: `scripts/swingle`, retained contracts, and provider gotcha tables.
- Produces: three small skill surfaces and transport-neutral contracts.

- [ ] **Step 1: Write skill contract tests**

Create `tests/test_skills.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELEGATE = ROOT / "skills" / "delegate" / "SKILL.md"
SETUP = ROOT / "skills" / "swingle-setup" / "SKILL.md"
SDD = ROOT / "skills" / "sdd" / "SKILL.md"

RETIRED = (
    "verified-version",
    "models.yaml",
    "verification-protocol",
    "controllers/",
    "core/liveness",
    "require-verified-version",
    "native-subagents",
    "superpowers availability",
    "worktree dispatch",
)


def test_delegate_uses_live_cli_contract_and_ledger():
    text = DELEGATE.read_text()
    for required in (
        "executable", "--help", "live", "contract", "ledger",
        "disable", "providers_by_lane", "default_provider",
        "explicit user model", ".swingle/delegate/ledger.md", "--path",
        "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED",
    ):
        assert required in text
    for retired in RETIRED:
        assert retired not in text


def test_setup_manages_only_swingle_owned_state():
    text = SETUP.read_text()
    for required in (
        "swingle config", "swingle ledger", "executable presence",
        "Explicit migration", "SWINGLE_MODELS", "user model directory",
    ):
        assert required in text
    for retired in RETIRED + ("auth", "readiness", "provider version"):
        assert retired not in text


def test_sdd_is_only_a_delegate_wrapper():
    text = SDD.read_text()
    assert "subagent-driven-development" in text
    assert "swingle-delegate" in text
    assert "sole authority" in text
    assert "SDD run-ledger path" in text
    for retired in RETIRED + ("Step 0", "self-reaping", "models.yaml"):
        assert retired not in text


def test_contracts_are_transport_neutral():
    for path in sorted((ROOT / "contracts").glob("*.md")):
        text = path.read_text()
        assert "provider pack" not in text.lower()
        assert "report-transport" not in text
        assert "sandboxed providers" not in text.lower()


def test_removed_skill_and_controller_surfaces_are_absent():
    assert not (ROOT / "skills" / "swingle-verify").exists()
    assert not (ROOT / "controllers").exists()
    assert not (ROOT / "core").exists()
```

- [ ] **Step 2: Run the skill tests and observe the expected failure**

Run:

```bash
uv run --with pytest pytest tests/test_skills.py -q
```

Expected: failures for current Step 0, worktree, controller, and transport text.

- [ ] **Step 3: Rewrite `swingle-delegate`**

Use these sections and no others:

```markdown
# Delegate Through an Installed CLI

## Boundary

The LLM is the controller. The provider CLI is the authority for its current operation.
Use this skill for one self-contained job or one homogeneous batch.
Use `swingle-sdd` for a dependency-aware implementation plan.

## Procedure

1. Select the reader, implementer, task-reviewer, or design-reviewer contract and lane.
2. Use the caller ledger path. Otherwise use `<project>/.swingle/delegate/ledger.md`.
3. Read policy with `swingle config show --project <working-directory>`.
4. Reject a provider listed in `disable`, including an explicit provider.
5. Select an explicit provider before `providers_by_lane` and `default_provider`.
6. If no provider resolves, ask the user. Do not silently choose one.
7. If the selected executable is missing, surface it. Do not silently substitute another provider.
8. Pass an explicit user model directly to the provider CLI.
9. Otherwise apply a preference only when the live CLI exposes it. Use the CLI default when none match.
10. Initialize the selected ledger and record allocation with `swingle ledger append --path`.
11. If current command syntax is not established, inspect top-level and subcommand `--help`.
12. Give the provider the contract, task, working directory, inputs, and report mode.
13. Run the provider with the tools available in the current harness.
14. Record provider, model or provider-default, session when available, attempt, and status in the same ledger.
15. Validate the requested result before reporting completion.

## Failure recovery

Match the observed failure against the provider gotcha table.
Apply a matching recovery, then record the failed attempt.
If no row matches, inspect current help before retrying.
Ask the user only when the provider CLI cannot resolve the blocker.

## Audit statuses

Use `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
The status routes work. The delegated result supplies completion evidence.
```

Keep frontmatter with the existing skill name `swingle-delegate` and explicit-invocation behavior.

- [ ] **Step 4: Rewrite `swingle-setup`**

Use these sections:

```markdown
# Set Up Swingle-Owned State

## Scope

This skill manages Swingle configuration, preferences, and ledgers.
It does not inspect provider auth, versions, readiness, permissions, or controller installation.

## Procedure

1. Run `swingle config show` for the current project.
2. If no configuration exists, offer `swingle config init` at the user or project layer.
3. Apply requested preference changes with `swingle config set`.
4. Show warnings from malformed optional preferences.
5. If requested, report executable presence for known providers with the harness command lookup.
6. Initialize or inspect a ledger with `swingle ledger`.

A configuration failure never establishes that an external provider is unavailable.

## Explicit migration

Run migration only when the user asks for it.
Inspect the old override walk in precedence order: `$SWINGLE_MODELS`, project `.swingle/models/`, then the user model directory.
Retain `disable`, `default_provider`, and compatible lane routing.
Convert clear winning `verified` or `experimental` rows into ordered model preferences by provider and tier.
Show cross-layer or lane conflicts as ambiguous rows before a write.
Apply approved values with `swingle config set`.
Remove each old key, directory, or environment reference only after explicit approval.
```

Keep explicit consent before configuration writes. Remove automatic controller and installation migration searches.

- [ ] **Step 5: Rewrite `swingle-sdd`**

Use this complete workflow body:

```markdown
# SDD Through Swingle Delegate

Run the installed `subagent-driven-development` workflow. That workflow is the sole authority for planning, task order, reviews, fixes, and completion.

At each external dispatch point, use `swingle-delegate`. Pass the current task brief, role, working directory, inputs, report requirement, and exact SDD run-ledger path.

The delegate initializes and appends provider, model or provider-default, session when available, attempt, status, and outcome to that exact path.

Do not add a second setup, worktree, review, liveness, model, or provider-validation process.
```

Keep the frontmatter name `swingle-sdd` and its current plan-execution triggers.

- [ ] **Step 6: Make contracts transport-neutral**

Apply these exact changes:

- Remove “external-CLI edition” from titles.
- Remove provider sandbox claims.
- Replace mandatory report-file wording with a dispatch-selected report mode.
- Keep the full report fields and status vocabulary.
- Keep “do not commit or push” as a role contract. Do not claim sandbox enforcement.
- Keep reader evidence requirements.
- Keep reviewer calibration and output formats.
- Keep design-reviewer no-code premise.

The implementer and reader contracts must say:

```text
Your dispatch selects one report mode. In file mode, write the full report to the named path and return the short status. In captured mode, return the full report in your final response and end with the status block.
```

- [ ] **Step 7: Remove obsolete process surfaces**

Remove:

```text
skills/swingle-verify/
controllers/
core/
archive/
```

Remove `.superpowers/` only when `git ls-files .superpowers` shows that it contains tracked Swingle-specific process artifacts.

Do not remove user-generated `.swingle/delegate/` content.

- [ ] **Step 8: Update skill metadata**

Update the three `agents/openai.yaml` files.

Descriptions must match the new boundaries. Remove verification, worktree, controller, and static-tier claims.

- [ ] **Step 9: Run skill and authoring tests**

Run:

```bash
uv run --with pytest pytest tests/test_skills.py tests/test_providers.py -q
```

Expected: all tests pass.

Run:

```bash
python3 scripts/swingle check --root .
```

Expected: exit 0 with no errors.

- [ ] **Step 10: Commit the skill clean cut**

```bash
git add skills contracts tests/test_skills.py controllers core archive .superpowers
git commit -m "refactor(skills): make the LLM the delegation controller"
```

Omit an absent path from `git add`. Do not add `.swingle/delegate/`.

---

### Task 5: Configuration Migration and Product Documentation

**Files:**
- Modify: `CLAUDE.md`
- Replace: `README.md`
- Replace: `docs/config.md`
- Replace: `docs/model-tiering.md`
- Replace: `docs/pack-authoring.md`
- Replace: `docs/safety.md`
- Create: `docs/migration-4.0.0.md`
- Remove: `docs/credentials.md`
- Remove: old `docs/migration-*.md` files
- Remove: `codex/INSTALL.md`
- Move: `.github/ISSUE_TEMPLATE/verification-finding.md` to `.github/ISSUE_TEMPLATE/provider-behavior.md`
- Update: plugin metadata descriptions when they mention certification

**Interfaces:**
- Consumes: completed CLI and skill surfaces.
- Produces: user and contributor documentation for the new ownership boundary.

- [ ] **Step 1: Replace obsolete contributor doctrine**

Replace the existing certification, validation-gate, Step-0, provider-layout, static-model, append-only-log, and `swingle-verify` sections in `CLAUDE.md`.

Then add this binding section:

```markdown
## Swingle Ownership Doctrine

- The LLM is the controller.
- The live provider CLI is the authority for provider operation.
- Never gate a provider with cached versions, models, auth results, readiness results, or controller facts.
- Python code can manage only universal Swingle state and deterministic Swingle structure.
- Provider notes contain only real, non-obvious failure guidance that changes recovery.
- Preferences steer selection. Preferences never define availability.
- Healthy delegation checks executable presence, briefs the task, records the ledger, and runs.
- Keep contracts and the ledger because they improve quality and auditability.
- Automation responds to observed product failures. It never certifies providers on a schedule.
- If CLI behavior is unclear, inspect current help before you add guidance.
```

Use the repository Grep tool on `CLAUDE.md` with:

```regex
validate-packs|codex-smoke|Step 0|Step-0|verified-version|models\.yaml|verification-log|swingle-verify|versions/
```

Expected: no active instruction uses a removed command or concept.

- [ ] **Step 2: Rewrite configuration documentation**

Document only:

- one JSON configuration file
- whole-file precedence
- `disable`
- optional `default_provider`
- `providers_by_lane`
- advisory `model_preferences`
- `swingle config init|show|validate|set`
- warning and fallback behavior.

Use the schema from the design spec verbatim.

- [ ] **Step 3: Rewrite model-tiering documentation as preference guidance**

Keep the terms `cheapest`, `standard`, and `most-capable` as advisory task intent.

State these rules:

- Swingle ships no model catalog.
- The live CLI supplies model reality.
- An explicit user model goes to the provider CLI.
- A stale preference falls through to the next live preference or provider default.
- No preference can exclude a live model.

- [ ] **Step 4: Rewrite provider authoring documentation**

Document the exact gotcha table and its three inclusion rules.

State that `pack.md` contains no command tutorial, version, model, success matrix, changelog digest, or positive inventory.

State that Git supplies history. Provider notes are living documents.

- [ ] **Step 5: Rewrite README and safety documentation**

README must explain:

- Swingle is a SKILLS plugin.
- The LLM controls the current CLI.
- Three skills ship: delegate, setup, and the small SDD wrapper.
- Contracts and ledger remain.
- Provider notes contain gotchas only.
- The Python CLI manages configuration, ledgers, and authoring checks.

Keep concise plugin installation commands. Remove controller cache paths, capability tables, verified pairings, and provider certification claims.

Safety documentation must cover task trust, prompt injection, write review, and result validation. Remove sandbox and provider capability claims.

- [ ] **Step 6: Replace the verification issue form**

Move `.github/ISSUE_TEMPLATE/verification-finding.md` to `.github/ISSUE_TEMPLATE/provider-behavior.md`.

Use this form:

```markdown
---
name: Provider behavior or guidance gap
about: Report silent or misleading provider CLI behavior that current help does not explain
title: "[provider] <observable failure>"
labels: ""
---

## Observable behavior

- Provider executable:
- Operating system:
- Current help inspected:
- Failure signature:

## Impact

State the missing or unreliable delegated result.

## Recovery attempted

State the action and observed result.

## Evidence

Add redacted output or a reproducible observation.
```

Remove version-bump, model-release, quarterly, probe-matrix, and pack-assertion fields.
Update every README link to use the new form.

- [ ] **Step 7: Write the major-version migration guide**

`docs/migration-4.0.0.md` must contain:

- removed skills and commands
- removed configuration keys and paths
- conversion of `$SWINGLE_MODELS`, project overrides, and user overrides
- cross-layer conflict handling
- provider model preferences are advisory
- each old directory or environment reference requires explicit removal
- no compatibility reader exists
- `swingle-setup` is the supported migration aid.

Remove earlier migration documents. Git retains them.

- [ ] **Step 8: Remove controller-specific install document**

Remove `codex/INSTALL.md` and the empty `codex/` directory.

Keep required plugin manifests under `.claude-plugin/`, `.codex-plugin/`, and `.agents/plugins/`.

- [ ] **Step 9: Run documentation checks**

Run:

```bash
python3 scripts/swingle check --root .
```

Expected: exit 0 with no errors.

Run:

```bash
git diff --check
```

Expected: exit 0 with no output.

- [ ] **Step 10: Commit documentation and doctrine**

```bash
git add CLAUDE.md README.md docs codex .claude-plugin .codex-plugin .agents/plugins .github/ISSUE_TEMPLATE
git commit -m "docs: establish guidance-first Swingle doctrine"
```

Omit unchanged metadata paths from `git add`.

---

### Task 6: Full Validation and One Behavioral Smoke

**Files:**
- Modify only when validation finds a defect in the new implementation.
- Record smoke evidence in the pull request body, not a provider pack.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: release evidence for the major redesign.

- [ ] **Step 1: Run the complete permanent test suite**

Run:

```bash
uv run --with pytest pytest -q
```

Expected: all tests pass with no warnings.

- [ ] **Step 2: Run the Swingle-owned authoring check**

Run:

```bash
python3 scripts/swingle check --root .
```

Expected: JSON with no errors and exit 0.

- [ ] **Step 3: Validate the command surface**

Run:

```bash
python3 scripts/swingle --help
python3 scripts/swingle config --help
python3 scripts/swingle ledger --help
```

Expected: only the new configuration, ledger, and check commands appear.

- [ ] **Step 4: Run one successful delegate smoke through Codex**

Use `swingle-delegate` from the changed branch.

Delegate this read-only task through the installed `codex` executable:

```text
Read README.md and return its first Markdown heading with a file and line citation. Do not change files.
```

Before the provider run:

- check executable presence
- inspect current Codex help
- select the reader contract
- initialize a temporary ledger outside tracked files.

After the run, validate:

- the answer cites `README.md:1` or the actual first-heading line
- the working tree is unchanged
- the ledger contains allocation, dispatch, optional session, and completion events
- no Swingle version, readiness, model table, controller adapter, or provider log was read.

- [ ] **Step 5: Run one synthetic help-first recovery smoke**

Run an invalid Codex subcommand that does not call a model:

```bash
codex swingle-invalid-subcommand
```

Expected: nonzero exit and current CLI error text.

Then run:

```bash
codex --help
```

Record one `attempt-failed` ledger event. Do not add the synthetic error to a provider gotcha table.

- [ ] **Step 6: Validate the final diff**

Run:

```bash
git diff --check develop...HEAD
git status --short
```

Expected: no whitespace errors. Only intended tracked changes appear.

- [ ] **Step 7: Commit any validation corrections**

If validation required changes:

```bash
git add -u
git commit -m "fix: resolve simplification validation findings"
```

If no correction was necessary, do not create an empty commit.

- [ ] **Step 8: Run adversarial post-implementation review**

Use the `requesting-code-review` skill.

Review `develop...HEAD` against the design spec and both implementation plans.
The review must check the LLM-controller boundary, removal completeness, configuration semantics, ledger safety, and provider-note quality.

- [ ] **Step 9: Resolve review findings**

Fix every Critical or Important finding.
Run the complete test suite, `swingle check`, and both smoke paths again.

If review required changes:

```bash
git add -u
git commit -m "fix: resolve simplification review findings"
```

- [ ] **Step 10: Create the implementation pull request**

Before push, confirm that the target base is `develop`.

Write a temporary pull request body with:

- the design spec path
- both implementation-plan paths
- removed certification surfaces
- permanent test results
- successful delegate smoke evidence
- synthetic recovery evidence
- post-implementation review result
- the statement “No plugin version change. The release branch owns the major version.”

Set the body path:

```bash
PR_BODY=/tmp/swingle-guidance-pr-body.md
```

Use the file-writing tool to write the recorded evidence to that path.

Run:

```bash
git push -u origin HEAD
gh pr create --base develop --head "$(git branch --show-current)" --title "refactor: make Swingle guidance-first" --body-file "$PR_BODY"
```

- [ ] **Step 11: Supersede old provider-guidance PR #55**

Check the old pull request state:

```bash
gh pr view 55 --json state,url
```

If its state is `OPEN`, run:

```bash
NEW_PR_URL=$(gh pr view --json url -q .url)
gh pr close 55 --comment "Superseded by ${NEW_PR_URL}. The replacement keeps only gotchas that pass the new inclusion rules."
```

Do not act when PR #55 is already closed or merged.
