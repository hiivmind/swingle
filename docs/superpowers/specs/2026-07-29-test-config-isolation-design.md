# Test subprocess configuration isolation

## Problem

Subprocess tests in `tests/test_validate_packs.py` can inherit a developer's valid
Swingle user configuration. Tests that intend to exercise the no-config baseline then
observe `config-layer=user` or `config-layer=env` instead of `config-layer=none`.
The production layer walk is correct; the test harness fails to establish its intended
environment.

## Design

Add one test-only `isolated_env` helper that starts with the current process environment,
redirects `XDG_CONFIG_HOME` to the existing nonexistent fixture path, removes inherited
`SWINGLE_CONFIG` and `SWINGLE_MODELS`, and finally applies explicit overrides supplied by
the caller. An override whose value is `None` removes that variable instead of placing a
non-string value in the subprocess environment.

All three subprocess helpers use this environment:

- `run` gets the isolated defaults, making ordinary subprocess tests hermetic.
- `run_env` gets the same defaults plus explicit overrides, preserving the existing
  project, user, environment, and inherited-`PATH` test cases.
- `run_models` gets the same defaults plus explicit overrides, replacing its partial
  duplicate isolation logic and preventing inherited `SWINGLE_CONFIG` from affecting
  `scripts/swingle-models` tests.

`FIX / "no-such-xdg"` is deliberately a nonexistent path, not a fixture directory. The
test suite must preserve that invariant so the isolated default cannot accidentally
discover a user configuration beneath it.

Production configuration resolution remains unchanged.

## Regression coverage

Before changing the helpers, add a test that places valid-looking Swingle config and model
files behind ambient `XDG_CONFIG_HOME`, `SWINGLE_CONFIG`, and `SWINGLE_MODELS` values, then
invokes plain `run`. The test uses pytest's `monkeypatch` fixture to set the ambient
variables so the parent process environment is restored when the test finishes. It must
expect the built-in model layer and `config-layer=none`. The test fails against the current
helper because ambient state leaks into the subprocess.

After the helper change, run the focused regression and the complete test suite without
manually overriding `XDG_CONFIG_HOME`.

## Success criteria

- The regression test demonstrates the leak before the fix and passes afterward.
- Existing explicit config-layer tests continue to cover `none`, `project`, `user`, `env`,
  and `env-unreadable`.
- `run`, `run_env`, and `run_models` all construct subprocess environments through
  `isolated_env`; explicit string overrides win, while `None` removes a variable.
- `tests/fixtures/no-such-xdg` remains absent.
- The full suite passes for developers with or without Swingle user configuration.
- No production files or configuration semantics change.
