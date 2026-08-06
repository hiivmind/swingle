# Implementation plan: decompose `scripts/` into `lib/swingle/`

Design: `docs/specs/scripts-decomposition-design.md` (Option A, behaviour-preserving).
This plan is the executable decomposition of that design after its Codex review.

**Architecture:** move the five `scripts/` files + their tests into a vendored,
stdlib-only in-repo package `lib/swingle/` with role-aligned modules; replace the
Python scripts with 4-line `sys.path` bootstrap shims that preserve every existing
path, argv, stdout, and exit code.

**Tech stack:** Python 3 stdlib only (no `pyproject.toml`/`setup.py`, no new deps),
pytest, Markdown docs/skills.

## Global constraints

- **Byte-identical CLI contract.** `scripts/validate-packs`, `scripts/swingle-models`,
  `scripts/shard-logs` keep identical paths, argparse surface, stdout, stderr, and exit
  codes. Phase 0 captures golden outputs; Phase 5 proves them unchanged by `diff`.
- **Behaviour-preserving.** No manifest-schema, resolution-semantics, or Step-0
  outcome-table change. No Option B. No `--audit` flag.
- **Green at every phase boundary.** The hard gate runs before every commit, chained
  with `&&`, never `;`:
  `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && uv run --with pytest pytest -q`
- **stdlib only.** Shims resolve their own location via `__file__`; no install step.
- **Git flow:** work stays on `chore/scripts-decomposition`; PR targets `develop`.
  The CI `develop`-trigger fix is a **separate** PR (Phase 6), not this one.
- **No version bump.** No pack facts change; `plugin.json`/`.codex-plugin`/README
  version lines are untouched (validator enforces their mutual sync).

## Module contract (target)

```
lib/swingle/
  __init__.py       # empty
  report.py         # findings: list; find(msg); reset()  (clear in place, never rebind)
  packs.py          # constants/regexes + parse/validate + load_packs(root) + check_tree_integrity(root, manifests)
  config.py         # CONFIG_KEYS, PROBED_RE, check_superpowers_block, load_config, resolve_config_layer
  resolve.py        # resolve_models, candidate_order, parse_roles, run_resolve(args...)
  environment.py    # HEALTH_PROBE_TIMEOUT_SECONDS, get_path_dirs, is_provider_installed,
                    #   detect_installed_providers, run_argv, check_provider_version,
                    #   check_provider_readiness, run_health
  step0.py          # run_step0(manifests, rows_by_id, root, args...)
  models.py         # main(default_root): which/init  (was swingle-models)
  audit/__init__.py
  audit/repo.py     # check_authoring(root, manifests)  (version-sync + repo-only doc scan)
  audit/logs.py     # parse_log, Entry, render_shard, migrate_provider, ..., main()  (was shard-logs)
  cli.py            # validate_packs_main(): argparse + report.reset() + load_packs + dispatch
```

Import graph (acyclic): `report <- packs <- resolve`; `config -> {packs, report}`;
`environment -> {packs, resolve}`; `audit/repo -> {packs, report}`;
`step0 -> {config, environment, resolve, report}`; `models -> {resolve, packs, report}`;
`cli` composes all; `audit/logs` independent (own stderr contract, no `report`).

Default-mode order in `validate_packs_main` (byte-identical stdout): (1) `load_packs`
bootstrap, (2) `packs.check_tree_integrity`, (3) `audit.repo.check_authoring`, (4) print
the single shared findings list once. `--health`/`--step0`/`--resolve`/`--check-config`
dispatch exactly as today (`scripts/validate-packs:496-579`).

---

## Phase 0 — Golden-output capture (proof harness)

**Files:** none committed (throwaway `/tmp` capture) plus a committed
`tests/test_cli_golden.py`.

- [ ] **0.1** Capture, from a clean tree at current HEAD, stdout+exit for a
  representative matrix into `/tmp/golden-before/`:
  - `validate-packs --root .` (exit 0, CLEAN)
  - `validate-packs --root tests/fixtures/good-lanes --resolve "per-task reviewer" alpha`
  - `validate-packs --step0 --root tests/fixtures/good-lanes --path-dir tests/fixtures/bins-alpha`
  - `validate-packs --check-config tests/fixtures/config-malformed.json`
  - `validate-packs --health --root tests/fixtures/good-lanes --path-dir tests/fixtures/bins-alpha`
  - `swingle-models which`
  - `shard-logs --root . ` (read-only, no `--write`)
  Record exact argv used.
- [ ] **0.2** Add `tests/test_cli_golden.py`: for each matrix row, run the script via
  subprocess under `isolated_env()` and assert stdout + returncode. Seed expectations
  from 0.1. This test must pass NOW (pre-refactor) and after — it is the contract lock.
- [ ] Gate; commit `test: golden CLI output lock for scripts (pre-decomposition)`.

## Phase 1 — Package scaffold + mechanical extraction

Single coherent move: a half-extracted `validate-packs` cannot run, so 1.x–1.10 land as
one green checkpoint. Extract in dependency order; keep every function body verbatim.

**Files:** create `lib/swingle/**`; shrink `scripts/validate-packs` to `main()`-less
after cli extraction (Phase 2 makes it a shim).

- [ ] **1.1** `lib/swingle/__init__.py`, `lib/swingle/audit/__init__.py` (empty).
- [ ] **1.2** `report.py`: `findings=[]`, `find(msg)`, `reset()` → `findings.clear()`.
- [ ] **1.3** `packs.py`: move all constants/regexes (`REQ/OPTIONAL/ENUMS/INTERPRETERS/
  TIERS/LANES/STATUSES/ELIGIBLE`, name/version/`MODEL_ROW_*`/`Y_*`/`HEADER_RE`/
  `SHARD_FILE_RE`/`ENTRY_DATE_RE`/`VERSION_FILE_RE`/`VERSION_TOKEN_RE`/`VER_RE`/`LINE_RE`),
  `version_key`, `version_cmp_key`, `registry_path_for`, `parse_front_matter`,
  `check_manifest`, `yaml_scalar`, `parse_models_yaml`, `check_rows`,
  `check_md_has_no_eligible_rows`. Add `load_packs(root)` (extract
  `validate-packs:481-495` → returns `(manifests, rows_by_id, packs)`) and
  `check_tree_integrity(root, manifests)` (the pack-tree-integrity half of
  `check_repo_docs`: registry/header/log-shard/`pack.md`-manifest-only/hygiene, plus
  purity of `core/`+`contracts/` and link/anchor scan over shipped trees). `find` via
  `from . import report`.
- [ ] **1.4** `resolve.py`: `resolve_models`, `candidate_order`, `parse_roles`, and
  `run_resolve(root, rows_by_id, role, provider, project, excluded)` (extract
  `validate-packs:569-579`).
- [ ] **1.5** `config.py`: `CONFIG_KEYS`, `PROBED_RE`, `check_superpowers_block`,
  `load_config`, `resolve_config_layer`.
- [ ] **1.6** `environment.py`: `HEALTH_PROBE_TIMEOUT_SECONDS`, `get_path_dirs`,
  `is_provider_installed`, `detect_installed_providers`, `run_argv`,
  `check_provider_version`, `check_provider_readiness`, `run_health` (imports
  `packs` regexes + `resolve.resolve_models`; **no** `report` import — no `find()` here).
- [ ] **1.7** `step0.py`: `run_step0(...)` = the entire `elif a.step0:` block
  (`validate-packs:502-568`) verbatim, composing `config`/`environment`/`resolve`.
- [ ] **1.8** `audit/repo.py`: `check_authoring(root, manifests)` = the
  authoring-only half of `check_repo_docs` (version-sync `plugin.json`↔README↔
  `.codex-plugin`; link/anchor scan restricted to repo-only docs). Wire the exact
  print order in `cli` so combined stdout is unchanged (Phase 5 diff proves it).
- [ ] **1.9** `audit/logs.py`: move all of `scripts/shard-logs` verbatim (`parse_log`,
  `Entry`, `render_shard`, `migrate_provider`, parity, `main`). Keep its own
  `shard-logs: <error>` stderr + `sys.exit` contract; no `report` import.
- [ ] **1.10** `models.py`: move all of `scripts/swingle-models`; delete the
  `SourceFileLoader` `load_validate_packs()`; import `resolve.resolve_models`,
  `packs.parse_front_matter`, `report`. Signature `main(default_root: Path)` — replace
  the `Path(__file__).resolve().parents[1]` default with `default_root`.
- [ ] **1.11** `cli.py`: `validate_packs_main()` = today's `main()` (argparse surface
  verbatim: `--root/--resolve/--exclude/--check-config/--step0/--health/--provider/
  --config/--path-dir/--lever/--task-provider/--role/--project`). First line
  `report.reset()`; call `packs.load_packs`; dispatch to `config.load_config`
  (`--check-config`), `environment.run_health` (`--health`), `step0.run_step0`
  (`--step0`), `resolve.run_resolve` (`--resolve`), else
  `packs.check_tree_integrity` + `audit.repo.check_authoring`; print `report.findings`
  once; return `1 if report.findings else 0`.
- [ ] **Note:** at this checkpoint `scripts/validate-packs` still imports/embeds the old
  code path only if needed to stay runnable; prefer to convert it to the shim in Phase 2
  in the same working session so the gate is run once against the shim.

## Phase 2 — Shims

**Files:** `scripts/validate-packs`, `scripts/swingle-models`, `scripts/shard-logs`.

- [ ] **2.1** Replace `scripts/validate-packs` with the bootstrap:
  `root = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root/"lib"));
  from swingle.cli import validate_packs_main; sys.exit(validate_packs_main())`.
- [ ] **2.2** `scripts/swingle-models` shim → `from swingle.models import main;
  sys.exit(main(default_root=root))`.
- [ ] **2.3** `scripts/shard-logs` shim → `from swingle.audit.logs import main;
  sys.exit(main())`.
- [ ] **2.4** Preserve `chmod +x` on all three (`git update-index --chmod=+x` if needed).
- [ ] `codex-smoke` and `opencode-skills-path` untouched (still call
  `python3 scripts/validate-packs`).
- [ ] Gate. The golden test (Phase 0) must still pass unchanged.

## Phase 3 — Test migration

**Files:** `conftest.py` (new, repo root), `tests/test_validate_packs.py`,
`tests/test_shard_logs.py`, `tests/test_setup_skill.py`, `tests/test_delegate_skill.py`
(only if they import scripts), plus new `tests/test_findings_isolation.py`.

- [ ] **3.1** Add root `conftest.py`: `sys.path.insert(0, str(Path(__file__).resolve().parent/"lib"))`.
- [ ] **3.2** `tests/test_validate_packs.py:36` — replace the `SourceFileLoader`
  `vp` import with `from swingle.cli import validate_packs_main` and update the two
  in-process `vp.main()` call sites (lines 46/50). Keep all subprocess `run()` tests
  as-is (they exercise the shim path).
- [ ] **3.3** Add an autouse env-isolation fixture for the **direct-import** tests
  (monkeypatch `XDG_CONFIG_HOME` → nonexistent, drop `SWINGLE_CONFIG`/`SWINGLE_MODELS`)
  so `validate_packs_main()` in-process cannot read ambient config. Subprocess tests
  keep their existing `isolated_env()`.
- [ ] **3.4** `tests/test_shard_logs.py:10` — replace loader with
  `import swingle.audit.logs as shard_logs`; keep every symbol reference.
- [ ] **3.5** Add subprocess smoke tests for the `swingle-models` and `shard-logs`
  **shims** (invoke the script path, assert exit + a stdout marker) — the compat
  contract for those two paths was previously import-only.
- [ ] **3.6** `tests/test_findings_isolation.py`: in one interpreter, call
  `validate_packs_main()` against a failing fixture (asserts exit 1, non-empty
  findings), then `swingle.models.main(default_root=...)` against a good root, and
  assert the models call is not poisoned by the earlier findings. Reverse order too.
- [ ] Gate.

## Phase 4 — Live-pointer + lockstep doc updates (acceptance criteria)

**Files:** `CLAUDE.md`, `docs/pack-authoring.md`, `docs/safety.md`,
`skills/sdd/SKILL.md`, `skills/delegate/SKILL.md`, `core/verification-log.md`,
new `tests/test_step0_lockstep.py`.

- [ ] **4.1** `CLAUDE.md:50-52` and `docs/pack-authoring.md:49`: `REQ`/`OPTIONAL`/`ENUMS`
  now live in `lib/swingle/packs.py`.
- [ ] **4.2** `docs/safety.md:34`: enforcement lives in the `swingle` package.
- [ ] **4.3** `CLAUDE.md:153-154`: correct the inaccurate "all validator testing is
  subprocess" statement to reflect the import + subprocess split.
- [ ] **4.4** Lockstep pointers `CLAUDE.md:27-30`, `skills/sdd/SKILL.md:80-92`,
  `skills/delegate/SKILL.md:107-118`: re-point the "executable rendering" reference at
  `lib/swingle/step0.py` (the invocation `scripts/validate-packs --step0` is unchanged).
- [ ] **4.5** `core/verification-log.md:82,94`: paths unchanged (still
  `scripts/validate-packs`), so no edit needed — confirm and note in the compat
  checklist.
- [ ] **4.6** `tests/test_step0_lockstep.py`: assert the typed outcome prefixes emitted
  by `step0.run_step0` (`STOP:`/`ASK:`/`CHANNEL:`/`warning:`/`native-subagents:`) are
  exactly the set documented in both skills' Markdown outcome tables (parse the table
  rows from the SKILL.md files). Fails if either drifts.
- [ ] Gate. Note: since `validate-packs --root .` runs the doc link/anchor checker over
  all shipped `*.md`, doc edits must keep links valid — the gate enforces this.

## Phase 5 — Verification (byte-identical proof)

- [ ] **5.1** Re-run the Phase 0 matrix into `/tmp/golden-after/`; `diff -r
  /tmp/golden-before /tmp/golden-after` → empty.
- [ ] **5.2** `python3 scripts/validate-packs --root .` → CLEAN; `./scripts/codex-smoke`
  → 4/4 (now includes the new package? no — codex-smoke checks skill/controller/contract
  presence, unaffected); `uv run --with pytest pytest -q` → all pass incl. new tests.
- [ ] **5.3** Fresh-clone reproduction: `git clone` the branch to a temp dir, run the
  gate from there — proves the shim's `__file__`-relative `lib/` resolution works with
  no ambient state.
- [ ] **5.4** Confirm no stray `__pycache__` tracked (`.gitignore` already covers).
- [ ] Open PR → `develop`. Body: design + review + this plan; note "no version bump".

## Phase 6 — CI develop-trigger (SEPARATE PR)

**Files:** `.github/workflows/ci.yml`.

- [ ] Add `develop` to `on.pull_request.branches` and `on.push.branches`. Its own
  branch/PR (`chore/ci-develop-trigger`) off `develop`, independent of the
  decomposition. Rationale: back-merge/feature PRs to `develop` currently get no checks.

## Risks & mitigations

- **Combined stdout order drift** (default mode splits `check_repo_docs` into two calls)
  → Phase 5.1 `diff` is the hard proof; if it differs, the integrity/authoring call
  order or the single-`print(findings)` placement is wrong.
- **`report.findings` leakage across in-interpreter calls** → Phase 3.6 test.
- **`models` root regression** → covered by golden `swingle-models which` (Phase 0/5)
  and the shim passing `default_root`.
- **Exec bit lost on shims** → Phase 2.4 explicit; `codex-smoke` + subprocess tests
  invoke via `python3 <path>` and directly, catching a lost bit.

## Execution note (SDD)

Phases 1–2 are one tightly-coupled mechanical move on a single source file → a single
implementer, sequential (no genuine parallel slices; faking fan-out here only adds
merge risk). The controller runs the gate + the golden diff between phases and reads
every diff. Suitable tier: adaptation implementer (prose-guided move), reviewer scaled
to the diff. Phases 3–4 (tests + docs) may run as two parallel slices once Phase 2 is
green, since they touch disjoint files.
