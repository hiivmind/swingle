# Design: decompose `scripts/` into a vendored `swingle` library

Status: proposed (design; not yet implemented)
Scope: reorganise `scripts/` and `tests/` into a vendored, stdlib-only in-repo
Python package with modules aligned to functional boundaries. Behaviour-preserving.

## Problem

`scripts/` is five standalone files plus 1,312 lines of tests and 54 fixture trees,
with no organising principle. The centre of gravity, `scripts/validate-packs` (583
lines), is a monolith fusing four distinct concerns:

- **Repo/pack self-validation** — `check_repo_docs` (manifest grammar, argv safety,
  registry structure, log-shard structure, hygiene, `core/`+`contracts/` purity,
  doc link/anchor integrity, `plugin.json`/`.codex-plugin`/README version-sync).
- **Runtime resolution** — `--resolve`, `--check-config`, `--step0`; the executable
  rendering of the dispatch skills' normative outcome tables.
- **Environment introspection** — `--health`: CLI-on-PATH, installed-vs-`verified-version`,
  bounded readiness/auth probe, resolving model layer.
- **Shared core** — manifest parsing + the model-resolution walk (also imported by
  `swingle-models` via a `SourceFileLoader` filename hack, since `validate-packs` is
  not an importable module name).

The load-bearing axis is **runtime-shipped vs authoring-only**, and the file's
organisation hides it. Four skills (`sdd`, `delegate`, `swingle-setup`, `swingle-verify`)
invoke `validate-packs` at dispatch time on the user's machine; `CLAUDE.md` mandates the
`--step0` path stay lockstep with skill prose ("the script is its executable rendering —
change them together").

## Non-negotiable constraints

1. **Vendored, stdlib-only, zero install step.** Skills invoke
   `python3 <root>/scripts/validate-packs …` directly under arbitrary CLI harnesses.
   No `pip install`, no `pyproject.toml`, no external dependency. This is why we do
   **not** extract to an external library — an install step is a portability regression
   and a new failure mode (version skew against the skill prose that must stay lockstep).
2. **Zero contract break.** Every path referenced by 4 skills, CI, `codex-smoke`,
   `docs/config.md`, `docs/pack-authoring.md`, `docs/model-tiering.md`, `docs/safety.md`,
   and 3 migration docs — `scripts/validate-packs`, `scripts/swingle-models`,
   `scripts/shard-logs` — keeps working with byte-identical CLI surface, stdout, and
   exit codes.
3. **Modules aligned to functional boundaries**, with the runtime/authoring axis
   legible in the tree.
4. **Lockstep intact.** `step0` stays a single named implementation so the
   outcome-table contract is *more* enforceable, not less.

## Key finding: the trust gate runs `check_repo_docs`

The skills' trust gate is `validate-packs --root <root>` with no other flag, which
(`main()` line 498) runs `check_repo_docs`. So `check_repo_docs` is **not** purely
authoring-only; it splits into two sub-concerns:

- **(a) Pack-tree integrity** — registry files/headers, log-shard structure,
  `pack.md` manifest-only, hygiene. Validates the *shipped* knowledge base; this IS
  the runtime trust anchor.
- **(b) Repo-authoring correctness** — `plugin.json`↔README↔`.codex-plugin`
  version-sync, markdown link/anchor integrity across `docs/`/`README`, purity of
  `core/`+`contracts/` against banned model ids. Only meaningful in the source repo.

This drives the one real decision (Option A/B below).

## Package layout (`lib/swingle/` — package name `swingle`)

Placing the package under `lib/` (not repo root) keeps the repo root uncluttered and
signals "this is the library, vendored".

```
lib/swingle/
  __init__.py
  report.py        # finding collector (shared)                     [runtime]
  packs.py         # manifest+models parse/validate; tree integrity  [runtime]
  config.py        # dispatch config load/gate + config-layer walk   [runtime]
  resolve.py       # model-resolution walk, roles, candidate order   [runtime]
  environment.py   # install/version/readiness/health introspection  [runtime]
  step0.py         # Step-0 dispatch simulator (the outcome table)   [runtime]
  models.py        # models.yaml layer seed/inspect (was swingle-models) [runtime]
  audit/
    __init__.py
    repo.py        # authoring correctness (version-sync/links/purity)  [AUTHORING]
    logs.py        # verification-log sharding (was shard-logs)          [AUTHORING]
  cli.py           # argparse for the validate-packs combined surface
scripts/           # thin bootstraps preserving the exact existing paths
  validate-packs        # -> swingle.cli:validate_packs_main
  swingle-models        # -> swingle.models:main
  shard-logs            # -> swingle.audit.logs:main
  codex-smoke           # unchanged bash (still calls python3 scripts/validate-packs)
  opencode-skills-path  # unchanged bash
conftest.py        # inserts <root>/lib on sys.path for tests
```

## Function-by-function map (relocation, not rewrite)

| Target module | Symbols moved from `validate-packs` |
|---|---|
| `report.py` | `findings`, `find`; new `reset()` (replaces `findings.clear()`) |
| `packs.py` | `REQ/OPTIONAL/ENUMS/INTERPRETERS/TIERS/LANES/STATUSES/ELIGIBLE`, all name/version/`MODEL_ROW_*`/`Y_*`/`HEADER_RE`/`SHARD_FILE_RE`/`ENTRY_DATE_RE`/`VERSION_FILE_RE`/`LINE_RE` regexes, `version_key`, `version_cmp_key`, `registry_path_for`, `parse_front_matter`, `check_manifest`, `yaml_scalar`, `parse_models_yaml`, `check_rows`, `check_md_has_no_eligible_rows`; **new** `load_packs(root)` (extracts the manifest/models bootstrap now inlined at lines 481-495) and **new** `check_tree_integrity(root, manifests)` (the (a) half of `check_repo_docs`) |
| `config.py` | `CONFIG_KEYS`, `PROBED_RE`, `check_superpowers_block`, `load_config`, `resolve_config_layer` |
| `resolve.py` | `resolve_models`, `candidate_order`, `parse_roles`; **new** `run_resolve(...)` (lines 569-579 `--resolve` handler) |
| `environment.py` | `HEALTH_PROBE_TIMEOUT_SECONDS`, `get_path_dirs`, `is_provider_installed`, `detect_installed_providers`, `run_argv`, `check_provider_version`, `check_provider_readiness`, `run_health` |
| `step0.py` | **new** `run_step0(...)` = the entire `elif a.step0:` block (lines 502-568), composing config+environment+resolve |
| `audit/repo.py` | the (b) half of `check_repo_docs` (version-sync, link/anchor scan, `core/`+`contracts/` purity) |
| `audit/logs.py` | all of `shard-logs` (`parse_log`, `migrate_provider`, parity, `main`) |
| `models.py` | all of `swingle-models` (`which`/`init`), importing `resolve.resolve_models`, `packs.parse_front_matter`, `report.findings` instead of the `SourceFileLoader` hack. **Root:** `models.main(default_root)` takes the plugin root as a parameter — the shim passes it; `models.py` carries no `parents[N]` layout assumption (blocking-1) |
| `cli.py` | `validate_packs_main()` = today's `main()` argparse + dispatch, calling `report.reset()`, `packs.load_packs`, then routing to config/health/step0/resolve/audit |

Dependency graph (acyclic), corrected after review:
`report <- packs <- resolve`; `config -> {packs, report}`;
`environment -> {packs, resolve}` (environment calls **no** `find()` — no `report`
edge; `run_health` calls `resolve_models`, so `environment -> resolve`);
`audit/repo -> {packs, report}`; `step0 -> {config, environment, resolve, report}`;
`models -> {resolve, packs, report}`; `cli` composes all.
**`audit/logs` is independent** — `shard-logs` uses no findings collector; it owns its
own `shard-logs: <error>` stderr + `sys.exit` contract (`scripts/shard-logs:210-227`).

## Findings collector

Centralise the module-global in `report.py`: `findings: list`, `find()`, and
`reset()` (which calls `findings.clear()` in place — **never rebinds** the list, so
object identity is preserved for importers). `models.py` reads `report.findings` — the
same object the old code read via `vp.findings`.

**Per-entrypoint reset (blocking-3).** As importable modules, `report.findings`
persists across calls in one interpreter, which never happened when each script was a
fresh process. Therefore **every** command entrypoint that owns an invocation calls
`report.reset()` first — both `cli.validate_packs_main()` and `models.main()`.
(`audit/logs` does not touch the collector.) A prior failed validation must not poison
a later `models` call in the same interpreter. Doctrine unchanged: "malformed = STOP
finding, never silent drop."

## Shim mechanism (the compatibility guarantee)

Each Python shim is a small bootstrap that inserts `<root>/lib` on `sys.path` (absolute,
resolved, index 0) and hands the derived root to entrypoints that need it. e.g.
`scripts/validate-packs`:

```python
#!/usr/bin/env python3
import sys, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "lib"))
from swingle.cli import validate_packs_main
sys.exit(validate_packs_main())
```

`scripts/swingle-models` additionally passes the root:
`sys.exit(main(default_root=root))` — resolving blocking-1.

Same file path, same executable bit, same argparse, same stdout/exit codes, so every
existing caller is untouched. `codex-smoke` and `opencode-skills-path` stay pure bash.

## The one real decision: what the trust-gate command runs

- **Option A — behaviour-preserving (CHOSEN for this work).** `validate-packs --root`
  runs the same checks in the **same execution order** as today. Critically, the
  default-mode repo scan is NOT re-sequenced: `check_repo_docs` survives as a single
  **orchestration façade** whose five sections run in their existing order — (1)
  version-sync, (2) per-pack structural, (3) hygiene, (4) purity, (5) one global
  path-sorted `rglob("*.md")` link scan (`scripts/validate-packs:344-473`). The façade
  lives in `audit/repo.py` and calls integrity primitives owned by `packs.py`; the
  single link scan stays one traversal emitting findings in global path order (splitting
  it into shipped-tree vs repo-only groups would reorder findings and break the
  byte-identical contract — verified in review). The runtime/authoring distinction is
  therefore **code ownership + per-finding classification**, NOT an execution split.
  `cli.validate_packs_main` default mode: `packs.load_packs` bootstrap →
  `audit.repo.check_repo_docs` → print the single shared findings list once.
- **Option B — boundary-enforcing (BACKLOG).** Trust gate runs integrity only; a new
  `--audit` flag runs authoring checks; CI switches to `--audit`. Tighter/faster runtime
  gate, but it changes what the trust-gate command does and needs CI + `CLAUDE.md` +
  skill-doc updates. Deserves its own spec.

## Runtime/authoring classification — by scanned surface, execution unchanged (review)

The a/b line is documentary under Option A (it enables the future Option B split); it
never reorders execution. Drawn by **what surface a check scans**:

- **Integrity (runtime trust anchor — ships, runs at the trust gate):** registry
  file/header/log-shard structure, `pack.md` manifest-only, hygiene, **purity of
  `core/`+`contracts/`** (`CLAUDE.md:40-44`), and link/anchor integrity within
  runtime-shipped trees (`core/`, `contracts/`, `providers/`, `skills/`;
  `CLAUDE.md:92-101`). Primitives owned by `packs.py`.
- **Authoring-only (source repo):** `plugin.json`↔README↔`.codex-plugin` version-sync
  and link/anchor scanning over repo-only docs (`docs/`, `docs/specs`, README prose).
  Owned by `audit/repo.py`.

Because the link scan is one traversal, findings from shipped and repo-only trees
interleave in path order; classification is a per-finding **tag**, not a separate pass.
Option B (backlog) is the only place execution would actually split — and it must
re-derive the two ordered groups deliberately, not by reusing this façade.

## Tests, CI, distribution

- **Tests (blocking-2).** Today two suites import the scripts as modules, not purely by
  subprocess: `tests/test_validate_packs.py:36` `SourceFileLoader`s the script and calls
  `vp.main()` (lines 46/50); `tests/test_shard_logs.py:10` loads the script and reaches
  into its classes. The thin shims `sys.exit(...)` at import, so these break at
  collection. Migration is explicit:
  - Re-point the in-process import at `tests/test_validate_packs.py:36` to
    `from swingle.cli import validate_packs_main` (the `vp.main()` re-entrancy test).
  - Re-point `tests/test_shard_logs.py` to `import swingle.audit.logs`.
  - **Keep** every subprocess `run()` test — they invoke the shims as scripts and are
    the coverage of the path-preserving contract.
  - **Add** subprocess smoke tests for the `swingle-models` and `shard-logs` shims (not
    only `validate-packs`), and a cross-entrypoint findings test: a failing
    `validate_packs_main()` followed by a clean `models.main()` in one interpreter must
    not leak findings.
  - `conftest.py` inserts the absolute resolved `<root>/lib` at `sys.path` index 0.
    Subprocess tests keep their scrubbed `XDG_CONFIG_HOME`/`SWINGLE_CONFIG`/`SWINGLE_MODELS`
    env; **direct-import** tests run in the pytest process and need an autouse
    env-isolation fixture (monkeypatch the same vars) so ambient config cannot leak.
  - The `swingle-models` `SourceFileLoader` hack is deleted. Fixtures unchanged.
- **CI (separate change).** `.github/workflows/ci.yml` triggers only on `main`; add
  `develop` (this is why back-merge PRs show "no checks reported"). This is a distinct
  workflow fix, **not** part of the behaviour-preserving reorg — land it as its own
  commit/PR so the decomposition stays purely mechanical.
- **Distribution:** no `pyproject.toml`/`setup.py`. Explicitly vendored + stdlib-only.
  Packaging would imply an install step the plugin contract forbids — the reason we do
  not extract to an external library.

## Risks

- **`sys.path` under exotic harnesses** — mitigated: the shim resolves its own location
  via `__file__`, independent of cwd/`PYTHONPATH`.
- **Hidden global-state coupling (`findings`)** — the collector module preserves object
  identity and semantics; the subprocess tests catch any drift.

## Acceptance criteria — live-pointer updates (not deferred "cleanup")

Updating living doctrine that names `scripts/validate-packs` internals is an acceptance
criterion of this change, done in the same PR (historical `docs/specs/*` and migration
docs are dated records — left as-is):

- `CLAUDE.md:50-52` and `docs/pack-authoring.md:49` — "update `REQ`/`OPTIONAL`/`ENUMS` in
  `scripts/validate-packs`" → `lib/swingle/packs.py`.
- `docs/safety.md:34` — "enforcement lives in `scripts/validate-packs`" → name the package.
- `CLAUDE.md:153-154` — inaccurately states all validator testing is subprocess-based;
  correct it to reflect the import + subprocess split.
- **Lockstep pointers** — `CLAUDE.md:27-30`, `skills/sdd/SKILL.md:80-92`,
  `skills/delegate/SKILL.md:107-118` point maintainers at `scripts/validate-packs` for
  the Step-0 outcome table. Re-point them at `lib/swingle/step0.py`, and add a
  structural test asserting the typed `STOP:`/`ASK:`/`CHANNEL:`/`warning:` outcome set in
  `step0.py` matches both skills' Markdown tables (a new file does not, by itself,
  enforce lockstep — it can make drift *easier* if the doctrine still points elsewhere).
- **Consumer inventory** must also list the live references at
  `core/verification-log.md:82` and `core/verification-log.md:94`.

## Out of scope / backlog

- Option B (trust-gate tightening + `--audit`).
- Any change to manifest schema, resolution semantics, or the Step-0 outcome table.
- Extraction to an external/installable package.

## Adversarial review (Codex gpt-5.6-sol, 2026-08-02)

Verdict: **needs rework → resolved in this revision.** Four blocking issues, all
verified against source and folded in above:

1. `swingle-models` default root would become `<root>/lib` after a verbatim move —
   fixed by `models.main(default_root)` passed from the shim.
2. Thin shims `sys.exit` at import, breaking the in-process `SourceFileLoader` tests
   (`test_validate_packs.py:36`, `test_shard_logs.py:10`) — fixed by explicit test
   re-pointing to `swingle.cli` / `swingle.audit.logs`, keeping subprocess tests.
3. Shared `report.findings` persists across in-interpreter calls — fixed by
   per-entrypoint `report.reset()` (both `validate_packs_main` and `models.main`).
4. Dependency graph was inaccurate (`environment -> resolve` missing; `audit/logs`
   is independent, not `-> report`) — corrected.

Non-blocking items folded in: scanned-surface classification, explicit trust-gate
stdout ordering, lockstep pointer/test acceptance criteria, `conftest`/direct-import
env-isolation, CI-trigger as a separate change, live-pointer updates as acceptance
criteria.