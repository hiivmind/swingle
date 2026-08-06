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
| `models.py` | all of `swingle-models` (`which`/`init`), importing `resolve.resolve_models`, `packs.parse_front_matter`, `report.findings` instead of the `SourceFileLoader` hack |
| `cli.py` | `validate_packs_main()` = today's `main()` argparse + dispatch, calling `report.reset()`, `packs.load_packs`, then routing to config/health/step0/resolve/audit |

Dependency graph (acyclic):
`report` <- `packs` <- {`config`, `resolve`, `environment`, `audit/repo`} <- `step0` <- `cli`;
`models` -> {`resolve`, `packs`, `report`}; `audit/logs` -> `report`.

## Findings collector

Centralise the module-global in `report.py` (`findings: list`, `find()`, `reset()`).
Every validator calls `report.find(...)`; `cli.validate_packs_main` calls
`report.reset()` first (today's `findings.clear()`). `models.py` reads `report.findings`
(the same object the old code read via `vp.findings`). Behaviour-preserving; the
"malformed = STOP finding, never silent drop" doctrine is unchanged.

## Shim mechanism (the compatibility guarantee)

Each Python shim is a 4-line bootstrap, e.g. `scripts/validate-packs`:

```python
#!/usr/bin/env python3
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lib"))
from swingle.cli import validate_packs_main
sys.exit(validate_packs_main())
```

Same file path, same executable bit, same argparse, same stdout/exit codes, so every
existing caller is untouched. `codex-smoke` and `opencode-skills-path` stay pure bash.

## The one real decision: what the trust-gate command runs

- **Option A — behaviour-preserving (CHOSEN for this work).** `validate-packs --root`
  runs integrity **and** authoring checks exactly as today; the split is purely at the
  module level (`packs.check_tree_integrity` + `audit.repo.check_authoring` both invoked
  under the default flag). Pure refactor, lowest risk, fully covered by the existing
  subprocess tests.
- **Option B — boundary-enforcing (BACKLOG).** Trust gate runs integrity only; a new
  `--audit` flag runs authoring checks; CI switches to `--audit`. Tighter/faster runtime
  gate, but it changes what the trust-gate command does and needs CI + `CLAUDE.md` +
  skill-doc updates. Deserves its own spec.

## Tests, CI, distribution

- **Tests:** keep the existing subprocess-through-shim tests (they now exercise
  shim -> package end to end — valuable coverage of the compat guarantee); add direct
  `import swingle.<module>` unit tests where they sharpen a boundary. Fixtures unchanged.
  Add root `conftest.py` guaranteeing `lib/` on `sys.path`. The `swingle-models`
  `SourceFileLoader` hack is deleted.
- **CI:** `.github/workflows/ci.yml` triggers only on `main`; add `develop` (this is why
  back-merge PRs show "no checks reported"). In-scope because tests move in this change.
- **Distribution:** no `pyproject.toml`/`setup.py`. Explicitly vendored + stdlib-only.
  Packaging would imply an install step the plugin contract forbids — the reason we do
  not extract to an external library.

## Risks

- **`sys.path` under exotic harnesses** — mitigated: the shim resolves its own location
  via `__file__`, independent of cwd/`PYTHONPATH`.
- **Hidden global-state coupling (`findings`)** — the collector module preserves object
  identity and semantics; the subprocess tests catch any drift.
- **Docs referencing internals** — `CLAUDE.md`/`docs/pack-authoring.md` say "update
  `REQ`/`OPTIONAL`/`ENUMS` in `scripts/validate-packs`". Those pointers must be updated to
  `lib/swingle/packs.py`. Cleanup phase, tracked.

## Out of scope / backlog

- Option B (trust-gate tightening + `--audit`).
- Any change to manifest schema, resolution semantics, or the Step-0 outcome table.
- Extraction to an external/installable package.
