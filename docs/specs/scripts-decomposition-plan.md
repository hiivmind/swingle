# Implementation plan: decompose `scripts/` into `lib/swingle/`

Design: `docs/specs/scripts-decomposition-design.md` (Option A, behaviour-preserving).
This plan is the executable decomposition of that design after two Codex reviews
(design review + this plan's review).

**Architecture:** move the five `scripts/` files + their tests into a vendored,
stdlib-only in-repo package `lib/swingle/` with role-aligned modules; replace the three
Python scripts with `sys.path` bootstrap shims that preserve every existing path, argv,
stdout, and exit code.

**Tech stack:** Python 3 stdlib only (no `pyproject.toml`/`setup.py`, no new deps),
pytest, Markdown docs/skills.

## Global constraints

- **Byte-identical CLI contract.** `scripts/validate-packs`, `scripts/swingle-models`,
  `scripts/shard-logs` keep identical paths, argparse surface, stdout, stderr, and exit
  codes. Proven by (a) an ordering-lock fixture whose exact output is captured from the
  **current** code before extraction, and (b) a controller-run before/after diff.
- **Default-mode execution order is NOT re-sequenced** (plan-review blocking-3).
  `check_repo_docs` survives as a single orchestration façade running its five sections
  in existing order: version-sync → per-pack structural → hygiene → purity → one global
  `sorted(rglob("*.md"))` link scan (`scripts/validate-packs:344-473`). The a/b
  runtime/authoring split is code ownership + per-finding tagging, never an execution
  split. The single link traversal is never split in two.
- **Behaviour-preserving.** No manifest-schema, resolution-semantics, or Step-0
  outcome-table change. No Option B. No `--audit` flag.
- **Green only at defined checkpoints.** Because the shims `sys.exit` at import and the
  current tests import the scripts as modules, the package extraction, the shims, AND
  the test-import migration MUST land in ONE atomic checkpoint (Phase 1) — there is no
  intermediate state that passes the gate (plan-review blocking-1). The hard gate,
  chained with `&&` never `;`:
  `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && uv run --with pytest pytest -q`
- **stdlib only.** Shims resolve their own location via `__file__`; no install step.
- **Git flow:** work stays on `chore/scripts-decomposition`; PR targets `develop`. The
  CI `develop`-trigger fix is a **separate** PR (Phase 6).
- **No version bump.** No pack facts change; version lines untouched.

## Module contract (target)

```
lib/swingle/
  __init__.py       # empty
  report.py         # findings: list; find(msg); reset()  (clear in place, never rebind)
  packs.py          # constants/regexes + parse/validate primitives + load_packs(root)
  config.py         # CONFIG_KEYS, PROBED_RE, check_superpowers_block, load_config, resolve_config_layer
  resolve.py        # resolve_models, candidate_order, parse_roles, run_resolve(...)
  environment.py    # HEALTH_PROBE_TIMEOUT_SECONDS, get_path_dirs, is_provider_installed,
                    #   detect_installed_providers, run_argv, check_provider_version,
                    #   check_provider_readiness, run_health   (no report import — no find())
  step0.py          # run_step0(...) + OUTCOME_PREFIXES constant
  models.py         # main(default_root): which/init  (was swingle-models)
  audit/__init__.py
  audit/repo.py     # check_repo_docs(root, manifests) façade (5 sections, legacy order)
  audit/logs.py     # parse_log, Entry, render_shard, migrate_provider, ..., main()  (was shard-logs)
  cli.py            # validate_packs_main(): argparse + report.reset() + load_packs + dispatch
```

Import graph (acyclic): `report <- packs <- resolve`; `config -> {packs, report}`;
`environment -> {packs, resolve}`; `audit/repo -> {packs, report}`;
`step0 -> {config, environment, resolve, report}`; `models -> {resolve, packs, report}`;
`cli` composes all; `audit/logs` independent (own stderr contract, no `report`).

`cli.validate_packs_main` default mode: `report.reset()` → `packs.load_packs` bootstrap
→ `audit.repo.check_repo_docs` (the ordered façade) → print `report.findings` once →
`return 1 if report.findings else 0`. `--health`/`--step0`/`--resolve`/`--check-config`
dispatch exactly as `scripts/validate-packs:496-579`.

---

## Phase 0 — Golden + ordering locks (captured from CURRENT code)

**Files:** new `tests/fixtures/bad-multi-region/`, new `tests/test_cli_contract.py`.

- [ ] **0.1** Build `tests/fixtures/bad-multi-region/` — a minimal repo tree that fires
  exactly one finding in EACH default-mode region, in order to lock section ordering:
  - `.claude-plugin/plugin.json` version `9.9.9` and `README.md` `**Version:** 0.0.0`
    → version-sync mismatch (region 1).
  - one provider pack with a structural break (e.g. `versions/` entry above frontier or
    missing class header) → per-pack structural (region 2).
  - a `~~strikethrough~~` in a pack body → hygiene (region 3).
  - a banned model id (e.g. `gpt-5.6`) in a `core/*.md` line → purity (region 4).
  - a broken relative link in a shipped tree file AND in a repo-only doc → link scan
    (region 5, both must appear in one global path-sorted pass).
- [ ] **0.2** `tests/test_cli_contract.py` (must pass on CURRENT code, pre-refactor):
  - **Ordering lock:** run `scripts/validate-packs --root tests/fixtures/bad-multi-region`
    under `isolated_env()`; assert the **exact ordered** stdout + exit 1. Seed the
    expected block by running the current script and pasting its output (so the lock
    encodes real current order, not a guess).
  - **Portable semantic matrix** (paths normalised — see 0.3): `--resolve` on
    `good-lanes`, `--step0` on `good-lanes` + `--path-dir bins-alpha`, `--health` on
    `good-lanes` + `--path-dir bins-alpha`, `--check-config config-malformed.json`,
    `swingle-models which`, `shard-logs --root .`. Assert exit codes and normalised
    stdout. Document that `shard-logs --root .` exits **1** (retained logs are indexes
    with no top-level entries; `scripts/shard-logs:221-222`) — that IS the expected row.
- [ ] **0.3** Path portability (plan-review blocking-4): `--resolve` and
  `swingle-models which` print `path.resolve()` (absolute:
  `scripts/validate-packs:574-575`, `scripts/swingle-models:36-42`). The test normalises
  absolute paths by substituting the resolved fixture/repo root with `<ROOT>` before
  asserting, so it passes in CI and a fresh clone. No literal machine path is committed.
- [ ] Gate; commit `test: CLI contract + ordering lock (pre-decomposition)`.

## Phase 1 — Atomic extraction + shims + test migration (one green checkpoint)

A half-extracted `validate-packs` cannot run and the shims break import-based tests, so
1.x land together; the gate runs once at the end of the phase. Extract in dependency
order, keeping every function body verbatim.

**Create `lib/swingle/**`:**

- [ ] **1.1** `__init__.py`, `audit/__init__.py` (empty).
- [ ] **1.2** `report.py`: `findings=[]`, `find(msg)`, `reset()` → `findings.clear()`
  (never rebinds).
- [ ] **1.3** `packs.py`: all constants/regexes (`REQ/OPTIONAL/ENUMS/INTERPRETERS/TIERS/
  LANES/STATUSES/ELIGIBLE`, name/version/`MODEL_ROW_*`/`Y_*`/`HEADER_RE`/`SHARD_FILE_RE`/
  `ENTRY_DATE_RE`/`VERSION_FILE_RE`/`VERSION_TOKEN_RE`/`VER_RE`/`LINE_RE`), `version_key`,
  `version_cmp_key`, `registry_path_for`, `parse_front_matter`, `check_manifest`,
  `yaml_scalar`, `parse_models_yaml`, `check_rows`, `check_md_has_no_eligible_rows`, and
  `load_packs(root)` (extract `validate-packs:481-495` → `(manifests, rows_by_id, packs)`).
  `find` via `from . import report`.
- [ ] **1.4** `resolve.py`: `resolve_models`, `candidate_order`, `parse_roles`,
  `run_resolve(root, rows_by_id, role, provider, project, excluded)`
  (extract `validate-packs:569-579`).
- [ ] **1.5** `config.py`: `CONFIG_KEYS`, `PROBED_RE`, `check_superpowers_block`,
  `load_config`, `resolve_config_layer`.
- [ ] **1.6** `environment.py`: `HEALTH_PROBE_TIMEOUT_SECONDS`, `get_path_dirs`,
  `is_provider_installed`, `detect_installed_providers`, `run_argv`,
  `check_provider_version`, `check_provider_readiness`, `run_health`. Imports `packs`
  regexes + `resolve.resolve_models`; **no** `report` import (no `find()` here).
- [ ] **1.7** `step0.py`: `run_step0(...)` = the entire `elif a.step0:` block
  (`validate-packs:502-568`) verbatim; add `OUTCOME_PREFIXES = {"STOP:", "ASK:",
  "CHANNEL:", "warning:", "native-subagents:", "installed:", "active:", "provider:",
  "layer:", "model:", "ready:", "available (auth unverified):"}` derived from the block's
  literal prints (for the Phase 4 lockstep test).
- [ ] **1.8** `audit/repo.py`: move `check_repo_docs` (`validate-packs:344-473`)
  **wholesale** as the ordered façade. Refactor its five sections into private helpers
  `_version_sync`, `_pack_structural`, `_hygiene`, `_purity`, `_link_scan` called in the
  **exact same order**; the link scan stays one `sorted(rglob("*.md"))` traversal. It may
  call `packs` primitives, but MUST NOT reorder or split any loop. `find` via `report`.
- [ ] **1.9** `audit/logs.py`: move all of `scripts/shard-logs` verbatim (`parse_log`,
  `Entry`, `render_shard`, `migrate_provider`, parity, `main`). Keep its own
  `shard-logs: <error>` stderr + `sys.exit` contract; no `report` import.
- [ ] **1.10** `models.py`: move all of `scripts/swingle-models`; delete
  `load_validate_packs()`; import `resolve.resolve_models`, `packs.parse_front_matter`,
  `report`; call `report.reset()` at the top of `main`. Signature
  `main(default_root)`; the `--root` argparse default becomes `default=str(default_root)`
  (`scripts/swingle-models:26`) — no `__file__`/`parents[N]` in the module.
- [ ] **1.11** `cli.py`: `validate_packs_main()` = today's `main()` with the argparse
  surface verbatim (`--root/--resolve/--exclude/--check-config/--step0/--health/
  --provider/--config/--path-dir/--lever/--task-provider/--role/--project`). First line
  `report.reset()`; `packs.load_packs`; dispatch to `config.load_config`
  (`--check-config`), `environment.run_health` (`--health`), `step0.run_step0`
  (`--step0`), `resolve.run_resolve` (`--resolve`), else `audit.repo.check_repo_docs`;
  print `report.findings` once; `return 1 if report.findings else 0`.

**Shims (replace the three Python scripts):**

- [ ] **1.12** `scripts/validate-packs`:
  `root = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root/"lib"));
  from swingle.cli import validate_packs_main; sys.exit(validate_packs_main())`.
- [ ] **1.13** `scripts/swingle-models` → `from swingle.models import main;
  sys.exit(main(default_root=root))`.
- [ ] **1.14** `scripts/shard-logs` → `from swingle.audit.logs import main;
  sys.exit(main())`.
- [ ] **1.15** Preserve exec bits; verify with `test -x scripts/validate-packs`
  (and the other two) — not merely `git update-index --chmod`.

**Test migration (same checkpoint):**

- [ ] **1.16** Add root `conftest.py`:
  `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "lib"))` — loaded
  before collection.
- [ ] **1.17** `tests/test_validate_packs.py` — the `SourceFileLoader` `vp` import
  (line 35) is removed; map every `vp.<symbol>` (plan-review blocking-2, full list):
  - `vp.main` (lines 46, 50, 614, 629, 642, 664, 688) → `swingle.cli.validate_packs_main`.
  - `vp.check_provider_version` (223, 501, 506, 510, 514),
    `vp.check_provider_readiness` (519) → `swingle.environment`.
  - `vp.parse_front_matter` (222), `vp.version_cmp_key` (386) → `swingle.packs`.
  Keep every subprocess `run()` test unchanged (they exercise the shim path).
- [ ] **1.18** Add a **module-scoped autouse** env-isolation fixture to
  `tests/test_validate_packs.py` (monkeypatch `XDG_CONFIG_HOME` → nonexistent, delete
  `SWINGLE_CONFIG`/`SWINGLE_MODELS`) so in-process `validate_packs_main()` /
  `environment.*` calls cannot read ambient config. It affects only in-process tests in
  that module; subprocess helpers keep their own explicit `isolated_env()` and are
  unaffected. Scope stated explicitly so it neither leaks into nor is defeated by the
  subprocess tests.
- [ ] **1.19** `tests/test_shard_logs.py` (loader at line 9) →
  `import swingle.audit.logs as shard_logs`; keep every symbol reference.
- [ ] **1.20** Gate. Phase 0's ordering-lock + portable matrix must pass **unchanged**.

## Phase 2 — Added contract tests

**Files:** `tests/test_cli_contract.py` (extend), `tests/test_findings_isolation.py`.

- [ ] **2.1** Subprocess smoke for the `swingle-models` and `shard-logs` shims (invoke
  the script path; assert exit + a stdout marker) — the compat contract for those two
  paths was import-only before.
- [ ] **2.2** `tests/test_findings_isolation.py` (plan-review blocking-6): in one
  interpreter, with `monkeypatch.setattr(sys, "argv", [...])` and `capsys`:
  1. call `validate_packs_main()` against `bad-multi-region` (assert exit 1,
     `report.findings` non-empty);
  2. call `swingle.models.main(default_root=<good root>)` with argv `["swingle-models",
     "which"]` (assert exit 0);
  3. assert the models call output is NOT polluted by the prior findings AND
     `report.findings == []` was true at models entry (prove `reset()` ran).
  Repeat in the reverse order. Assert on the cleared list, not just the return code.
- [ ] Gate.

## Phase 3 — Live-pointer + lockstep doc updates (acceptance criteria)

**Files:** `CLAUDE.md`, `docs/pack-authoring.md`, `docs/safety.md`,
`skills/sdd/SKILL.md`, `skills/delegate/SKILL.md`, new `tests/test_step0_lockstep.py`.
(`core/verification-log.md:82,94` keep the path `scripts/validate-packs` — no edit;
confirm in the compat checklist.)

- [ ] **3.1** `CLAUDE.md:50-52`, `docs/pack-authoring.md:49`: `REQ`/`OPTIONAL`/`ENUMS`
  live in `lib/swingle/packs.py`.
- [ ] **3.2** `docs/safety.md:34`: enforcement lives in the `swingle` package.
- [ ] **3.3** `CLAUDE.md:153-154`: correct the "all validator testing is subprocess"
  claim to reflect the import + subprocess split.
- [ ] **3.4** Lockstep pointers `CLAUDE.md:27-30`, `skills/sdd/SKILL.md:80-92`,
  `skills/delegate/SKILL.md:107-118`: re-point the "executable rendering" reference at
  `lib/swingle/step0.py` (the invocation `scripts/validate-packs --step0` is unchanged).
- [ ] **3.5** `tests/test_step0_lockstep.py` — concrete, subagent-executable algorithm
  (not free-form table parsing): assert `swingle.step0.OUTCOME_PREFIXES` is the canonical
  set, and that each **STOP/ASK/CHANNEL** prefix token appears verbatim in BOTH
  `skills/sdd/SKILL.md` and `skills/delegate/SKILL.md` (simple substring check per token).
  Fails if `step0.py` gains an outcome class not documented in either skill.
- [ ] Gate (default-mode link checker enforces that these doc edits keep links valid).

## Phase 4 — Verification (byte-identical proof) + PR

- [ ] **4.1** Controller before/after diff: on one machine, capture the Phase 0 matrix
  stdout+exit at the pre-refactor commit into `/tmp/golden-before/` and post-refactor
  into `/tmp/golden-after/`; `diff -r` → empty (paths match on the same machine, so this
  catches any non-path drift the normalised test might mask).
- [ ] **4.2** `python3 scripts/validate-packs --root .` → CLEAN; `./scripts/codex-smoke`
  → all PASS (unaffected — presence checks); `uv run --with pytest pytest -q` → all pass.
- [ ] **4.3** Fresh-clone reproduction: `git clone` the branch to a temp dir; run the
  gate from there — proves `__file__`-relative `lib/` resolution with no ambient state.
- [ ] **4.4** Confirm no tracked `__pycache__`/`*.pyc` (`.gitignore` covers it).
- [ ] **4.5** Open PR → `develop`; body links design + both reviews + this plan; note
  "no version bump".

## Phase 5 — CI develop-trigger (SEPARATE PR)

**Files:** `.github/workflows/ci.yml`.

- [ ] Add `develop` to `on.pull_request.branches` and `on.push.branches`. Own branch/PR
  (`chore/ci-develop-trigger`) off `develop`, independent of the decomposition.

## Confirmed compatibility (from review — no action needed)

- `scripts/codex-smoke:70` and `.github/workflows/release.yml:34-36` invoke
  `python3 scripts/validate-packs` — path preserved, no change.
- The four skills use preserved paths and flags — no change.
- No module appends findings at import time; all `find()` calls are inside functions, so
  per-entrypoint `reset()` is sufficient.
- `setup`/`delegate` tests assert on skill text only; they do not import scripts.

## Risks & mitigations

- **Section-order or link-scan drift** → Phase 0 ordering-lock fixture (captured from
  current code) + Phase 4.1 diff. The façade + single-traversal rule (constraint above)
  is the design guard.
- **`report.findings` leakage in-interpreter** → Phase 2.2 test.
- **`models` root regression** → golden `swingle-models which` + shim `default_root`.
- **Absolute paths in golden** → Phase 0.3 normalisation.
- **Lost exec bit** → Phase 1.15 `test -x` + subprocess tests invoking the path.

## Execution note (SDD)

Phase 1 is one tightly-coupled mechanical move on a single source file plus its two
dependents and their tests → a **single implementer**, sequential; faking fan-out here
only adds merge risk (adaptation-implementer tier, reviewer scaled to the diff). The
controller runs the gate + the Phase 4.1 diff and reads every diff itself. Phases 2–3
(added tests / doc updates) touch disjoint files and MAY run as two parallel slices once
Phase 1 is green.
