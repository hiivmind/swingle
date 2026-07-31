# Test Subprocess Configuration Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every subprocess test helper in `tests/test_validate_packs.py` hermetic, so a developer's ambient Swingle configuration can never change what the test suite observes.

**Architecture:** Introduce one test-only `isolated_env(**overrides)` helper that builds a subprocess environment from the current process environment, redirects `XDG_CONFIG_HOME` at the deliberately nonexistent `tests/fixtures/no-such-xdg`, drops inherited `SWINGLE_CONFIG` and `SWINGLE_MODELS`, then applies caller overrides (a `None` value removes the variable). All three helpers — `run`, `run_env`, `run_models` — construct their environment through it. `run_env` and `run_models` lose their partial, duplicated isolation logic. A regression test is written first and must fail before the helper change.

**Tech Stack:** Python 3, pytest (via `uv run --with pytest`), `subprocess`, pytest's `monkeypatch` fixture.

## Global Constraints

- **No production files change.** Only `tests/test_validate_packs.py` is modified. `scripts/validate-packs`, `scripts/swingle-models`, `core/`, `providers/`, `skills/` are untouched. Configuration resolution semantics are unchanged.
- **No version bump.** No pack facts change, so `plugin.json`, `.codex-plugin/plugin.json`, and the README `**Version:**` line stay as they are.
- **`tests/fixtures/no-such-xdg` must remain absent.** It is a deliberately nonexistent path, not a fixture directory. Never create it.
- **The hard gate runs before every commit, chained with `&&`, never `;`:**
  `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit ...`
- **Full suite command:** `uv run --with pytest pytest tests/ -q`
- **Git flow:** work stays on the current `bugfix/test-config-isolation` branch; the PR targets `develop`. Do not push to `main`.

---

## File Structure

| File | Responsibility | Change |
| --- | --- | --- |
| `tests/test_validate_packs.py` | Validator + `swingle-models` subprocess test suite; owns the three subprocess helpers and the new `isolated_env` | Modify |
| `tests/fixtures/no-such-xdg` | Nonexistent-by-design path referenced by `isolated_env` | Must NOT exist |

Current shape of the file, for orientation:

- Lines 1–6: module imports and the `ROOT` / `SCRIPT` / `FIX` constants.
- Lines 14–15: `run` — no `env=` argument at all, so it inherits everything.
- Line 131: a second, mid-file `import os`.
- Lines 133–137: `run_env` — partial isolation (`XDG_CONFIG_HOME` redirect, `SWINGLE_MODELS` popped, but `SWINGLE_CONFIG` left inherited).
- Lines 213–217: `run_models` — the same partial isolation, duplicated.
- Line 249: `make_health_test_root(tmp_path, providers=("alpha", "beta"))`.
- Lines 342–369: `test_health_config_layers` — the explicit `none` / `project` / `user` / `env` / `env-unreadable` coverage that must keep passing.

---

### Task 1: Regression test proving ambient config leaks through `run`

**Files:**
- Modify: `tests/test_validate_packs.py` — insert one new test immediately after `test_health_config_layers` (which currently ends at line 369)

**Interfaces:**
- Consumes: `run(*args)` (line 14), `make_health_test_root(tmp_path, providers)` (line 249), the `FIX` constant (line 6), and the `good-yaml` fixture tree.
- Produces: `test_run_ignores_ambient_swingle_config(tmp_path, monkeypatch)` — the RED test that Task 2 turns green. No other task depends on its internals.

This task deliberately ends with a **failing** test committed. That is the point: the failure is the evidence the leak is real. Commit it on its own so the fix commit demonstrably flips it.

- [ ] **Step 1: Write the failing regression test**

Insert this immediately after the end of `test_health_config_layers` (after the `env-unreadable` assertion, currently line 369) and before `def test_health_composes_with_check_config`:

```python
def test_run_ignores_ambient_swingle_config(tmp_path, monkeypatch):
    """A developer's real Swingle config must not reach subprocess tests.

    Sets valid-looking ambient config at all three inputs the production layer
    walk reads, then invokes plain `run`. The subprocess must still report the
    built-in model layer and config-layer=none.
    """
    root = make_health_test_root(tmp_path, ("alpha",))

    ambient_xdg = tmp_path / "ambient-xdg"
    (ambient_xdg / "swingle").mkdir(parents=True)
    (ambient_xdg / "swingle" / "config.json").write_text("{}")

    ambient_cfg = tmp_path / "ambient-config.json"
    ambient_cfg.write_text("{}")

    ambient_models = tmp_path / "ambient-models"; ambient_models.mkdir()
    (ambient_models / "alpha.yaml").write_text(
        "schema: 1\nprovider: alpha\nmodels:\n"
        "  - tier: standard\n    lane: review\n    priority: 1\n"
        "    model: ambient-review-model\n    status: experimental\n")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(ambient_xdg))
    monkeypatch.setenv("SWINGLE_CONFIG", str(ambient_cfg))
    monkeypatch.setenv("SWINGLE_MODELS", str(ambient_models))

    r = run("--health", "--root", str(root))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "config-layer=none" in r.stdout

    r2 = run("--root", str(FIX / "good-yaml"), "--resolve", "per-task reviewer", "alpha")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "layer: default path=" in r2.stdout
    assert "ambient-review-model" not in r2.stdout
```

Notes for the implementer:
- `monkeypatch.setenv` mutates the *parent* process environment and pytest restores it at teardown — that is why the ambient state is safe to set here and nowhere else.
- The three ambient values are ordered so that a leak is unmistakable: `SWINGLE_CONFIG` outranks the user layer, so a leaking `run` reports `config-layer=env`, and a leaking `SWINGLE_MODELS` reports `layer: env` with `ambient-review-model`.
- Do **not** touch `run` in this task.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pytest pytest tests/test_validate_packs.py::test_run_ignores_ambient_swingle_config -q`

Expected: **FAIL**, on the first assertion, with `assert "config-layer=none" in r.stdout` where stdout contains `config-layer=env` — because `run` passes no `env=` to `subprocess.run` and therefore inherits `SWINGLE_CONFIG` from the parent.

If instead it fails on `layer: default path=` or passes outright, stop and report: the leak is not the one the spec describes and the diagnosis needs revisiting before any helper changes.

- [ ] **Step 3: Confirm the rest of the suite is unaffected**

Run: `uv run --with pytest pytest tests/ -q`

Expected: the new test fails. **How many other tests fail depends on the machine** — corrected
during execution, 2026-07-29. On a developer with no Swingle user config, this is the only
failure. On a developer who *does* have `~/.config/swingle/config.json` — the exact condition
the spec is about — three pre-existing tests fail too, because they call plain `run` and
observe `config-layer=user` instead of `config-layer=none`:
`test_health_installed_and_uninstalled`, `test_health_composes_with_check_config`, and
`test_health_provider_scoping`.

Those three failures are the bug, not collateral damage, and Task 2 must fix them without
being edited. Record which of the two baselines you saw; Task 2 Step 7 expects a clean suite
either way.

- [ ] **Step 4: Commit the red test**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git add tests/test_validate_packs.py && git commit -m "test: prove ambient Swingle config leaks into subprocess tests

Adds a failing regression test that sets valid-looking XDG_CONFIG_HOME,
SWINGLE_CONFIG, and SWINGLE_MODELS via monkeypatch and asserts plain run()
still observes the built-in model layer and config-layer=none. Fails today
because run() passes no env= to subprocess.run."
```

---

### Task 2: Route all three subprocess helpers through `isolated_env`

**Files:**
- Modify: `tests/test_validate_packs.py:1` (imports), `:14-15` (`run`), `:131-137` (stray `import os` + `run_env`), `:213-217` (`run_models`)
- Test: `tests/test_validate_packs.py` (the whole suite is the test for this change)

**Interfaces:**
- Consumes: `test_run_ignores_ambient_swingle_config` from Task 1 — it must flip from FAIL to PASS.
- Produces: `isolated_env(**overrides) -> dict[str, str]` — the single environment constructor for every subprocess helper in this file. Explicit string overrides win; an override whose value is `None` removes that variable. `run(*args)`, `run_env(*args, **env)`, and `run_models(*args, **env)` keep their existing signatures and return `subprocess.CompletedProcess`.

- [ ] **Step 1: Add `isolated_env` and hoist the `os` import**

Change line 1 from:

```python
import json, shutil, subprocess, sys
```

to:

```python
import json, os, shutil, subprocess, sys
```

Then insert `isolated_env` immediately after the `FIX` constant on line 6, before the `importlib` block:

```python
def isolated_env(**overrides):
    """Build a subprocess environment with ambient Swingle config removed.

    Starts from the current process environment, redirects XDG_CONFIG_HOME at a
    path that deliberately does not exist, drops any inherited SWINGLE_CONFIG
    and SWINGLE_MODELS, then applies caller overrides. An override whose value
    is None removes that variable rather than putting a non-string in the
    environment.
    """
    e = dict(os.environ, XDG_CONFIG_HOME=str(FIX / "no-such-xdg"))
    e.pop("SWINGLE_CONFIG", None)
    e.pop("SWINGLE_MODELS", None)
    for name, value in overrides.items():
        if value is None:
            e.pop(name, None)
        else:
            e[name] = value
    return e
```

- [ ] **Step 2: Delete the mid-file `import os`**

Remove the standalone `import os` line (currently line 131, sitting between `test_eligible_row_guard`-style tests and `run_env`) along with the blank line it introduced. `os` is now imported at the top of the module.

- [ ] **Step 3: Rewrite the three helpers**

Replace `run` (currently lines 14–15) with:

```python
def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=isolated_env())
```

Replace `run_env` (currently lines 133–137) with:

```python
def run_env(*args, **env):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=isolated_env(**env))
```

Replace `run_models` (currently lines 213–217) with:

```python
def run_models(*args, **env):
    return subprocess.run([sys.executable, str(SDD_MODELS), *args],
                          capture_output=True, text=True, env=isolated_env(**env))
```

Leave `SDD_MODELS = ROOT / "scripts" / "swingle-models"` where it is, directly above `run_models`.

Because `isolated_env` starts from `os.environ`, `PATH` is still inherited — `test_health_never_exits_nonzero_for_env_states` and the other `--path-dir` cases keep working.

- [ ] **Step 4: Add the fixture-absence invariant test**

`isolated_env`'s guarantee rests on `FIX / "no-such-xdg"` never existing. Make that a checked invariant rather than a comment. Insert immediately after the `isolated_env` definition:

```python
def test_no_such_xdg_fixture_stays_absent():
    """isolated_env's XDG redirect only isolates while this path does not exist."""
    assert not (FIX / "no-such-xdg").exists()
```

- [ ] **Step 5: Run the regression test to verify it now passes**

Run: `uv run --with pytest pytest tests/test_validate_packs.py::test_run_ignores_ambient_swingle_config -q`

Expected: **PASS**.

- [ ] **Step 6: Run the config-layer and models tests explicitly**

Run:

```bash
uv run --with pytest pytest tests/test_validate_packs.py -q \
  -k "config_layer or sdd_models or no_such_xdg or ambient or resolve or env_layer"
```

Expected: all PASS. `test_health_config_layers` must still exercise `config-layer=none`, `project`, `user`, `env`, and `env-unreadable` — the explicit overrides still win over the isolated defaults.

- [ ] **Step 7: Run the full suite with no manual environment overrides**

Run: `uv run --with pytest pytest tests/ -q`

Expected: all PASS. Run it plainly — do **not** prefix with `XDG_CONFIG_HOME=...`. That the bare command passes is the deliverable.

- [ ] **Step 8: Confirm no production file changed**

Run: `git status --porcelain`

Expected: exactly one modified path, `tests/test_validate_packs.py` (plus this plan document if it is not yet committed). No `scripts/`, `core/`, `providers/`, `skills/`, or `*plugin.json` entry. No new `tests/fixtures/no-such-xdg`.

- [ ] **Step 9: Commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git add tests/test_validate_packs.py && git commit -m "test: isolate subprocess helpers from ambient Swingle config

Adds isolated_env(), which starts from os.environ, redirects XDG_CONFIG_HOME
at the deliberately nonexistent no-such-xdg path, drops inherited
SWINGLE_CONFIG and SWINGLE_MODELS, then applies caller overrides (None
removes a variable). run, run_env, and run_models all build their subprocess
environment through it, replacing run_env's and run_models' duplicated
partial isolation. Guards the no-such-xdg absence invariant with a test.

Production config resolution is unchanged."
```

---

## Verification Summary

Against the spec's success criteria:

| Criterion | Where it is verified |
| --- | --- |
| Regression test demonstrates the leak before the fix and passes after | Task 1 Step 2 (FAIL), Task 2 Step 5 (PASS) |
| Explicit config-layer tests still cover `none`/`project`/`user`/`env`/`env-unreadable` | Task 2 Step 6 |
| All three helpers construct environments through `isolated_env`; string overrides win, `None` removes | Task 2 Steps 1 and 3 |
| `tests/fixtures/no-such-xdg` remains absent | Task 2 Step 4 (test) and Step 8 (`git status`) |
| Suite passes with or without developer Swingle config | Task 2 Step 7 — the bare command passes in both states, since ambient config can no longer reach the subprocess |
| No production files or configuration semantics change | Task 2 Step 8 |

## Wrap-up

Open a PR from `bugfix/test-config-isolation` to `develop`:

```bash
gh pr create --base develop \
  --title "test: hermetic subprocess config isolation" \
  --body "Implements docs/superpowers/specs/2026-07-29-test-config-isolation-design.md.

Subprocess tests could inherit a developer's valid Swingle user configuration, so
tests intending the no-config baseline observed config-layer=user or =env. Adds a
single isolated_env() helper and routes run, run_env, and run_models through it,
replacing two copies of partial isolation logic. Ships with a regression test that
fails against the old helpers.

Tests only. Production resolution semantics unchanged; no version bump."
```
