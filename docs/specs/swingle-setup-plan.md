# Implementation plan — `swingle-setup` skill (target 3.1.0)

**Source spec:** [docs/specs/swingle-setup.md](swingle-setup.md) (revised after design
review job 017). **Branch:** `feature/swingle-setup-skill` → PR to `develop` (after the
3.0.0 rename PR merges). Execute via `swingle-sdd` or inline; every task ends green on
the full suite and the hard gate (`validate-packs && codex-smoke`, chained `&&`).

Dependency order: T1 and T2 are independent of each other; T3 needs both; T4–T6 need
T3; T7 is last.

---

## T1 — `validate-packs --health` mode

**Files:** `scripts/validate-packs`, `tests/test_validate_packs.py`.

Add a `--health` flag (with optional repeated `--provider <id>` scoping and the existing
`--root`/`--project`). For each pack manifest, emit one line to stdout, plus one
trailing config line:

```
<id>: installed=<yes|no> version=<v|-> verified=<v> drift=<yes|no> readiness=<ok|fail|timeout|skipped> registry-layer=<env|project|user|default|->
config-layer=<env|project|user|none|env-unreadable>
```

- **Refactor first (review finding N1)**: extract the detection / version-drift /
  readiness / layer-resolution body currently inline in the `--step0` branch into named
  module-level helpers; `--step0` and `--health` both consume them — one
  implementation, two modes. `--step0`'s external behavior (output, findings, exit
  codes) is unchanged; existing `--step0` tests must pass unmodified.
- **Config-layer emission (review finding P3)**: `--health` walks the config chain
  (`$SWINGLE_CONFIG` → project → user) in the script and emits the winning layer,
  including the `env-unreadable` case (set-but-unreadable `$SWINGLE_CONFIG`) — the
  dispatch STOP-equivalent is detected by the script, not skill prose.
- **No route selection, no role argument, exit 0 even when CLIs are missing**
  (missing CLIs are data, not findings) — exit non-zero only for the existing manifest
  findings.
- Readiness/version probes are timeout-bounded via a module-level constant
  `HEALTH_PROBE_TIMEOUT_SECONDS = 30`, referenced (not inlined) at the call sites so
  tests can override it with `monkeypatch.setattr` (review finding P1); a timeout
  reports `readiness=timeout`, never hangs the mode.
- Uninstalled provider: `readiness=skipped`, `version=-`.
- **Argparse composition (review finding P2)**: `main()`'s existing mutually-exclusive
  branch structure is extended so `--health` + `--check-config <file>` run in ONE
  invocation (setup Phase A calls both together); dedicated test
  `test_health_composes_with_check_config` asserts both outputs appear in a single
  argv run.

**Tests** (fixture-driven, no real CLIs): a fake pack whose `cli` is a stub script on a
temp PATH — installed/uninstalled, drift yes/no, readiness ok/fail/timeout (stub sleeps
past a `monkeypatch`-shortened `HEALTH_PROBE_TIMEOUT_SECONDS`), registry-layer column
agrees with `resolve_models` fixtures, config-layer cases (none / project / user /
env / env-unreadable), the composition test above. Assert `--health` never exits
non-zero for environment states, only for manifest findings.

**Acceptance:** spec §7 `--health` section satisfied (including the N1 helper mandate);
`--step0` behavior untouched (existing tests unchanged and green).

## T2 — `docs/config.md` (canonical config schema)

**Files:** `docs/config.md` (new), `skills/sdd/SKILL.md`, `skills/delegate/SKILL.md`.

Write the schema doc: the four keys (`disable`, `default_provider`,
`providers_by_lane`, `require-verified-version`) with types and semantics; the layer
walk and whole-file-wins rule; the dispatch STOP conditions verbatim (quoted as the
consumers enforce them); unknown-keys-are-warnings semantics (I1); the neutral template
JSON block (§6.2); `validate-packs --check-config` as the validation entry point.
**STOP-wording canonicality (review finding P5)**: the sdd skill's inline statement is
the canonical source; `docs/config.md` quotes it verbatim; the delegate skill's
existing cross-reference ("the same malformed-config STOP conditions as the
`swingle-sdd` skill") stays; the sdd skill's inline copy remains load-bearing.

In both dispatch SKILL.md files: add a link to `docs/config.md` at the config step
(`See docs/config.md for the schema`) — **inline STOP conditions stay verbatim**; only
key-by-key explanation is delegated to the doc. No behavior change.

**Acceptance:** validator link/anchor scan green (M6); structural tests still count
their asserted strings correctly (run the suite — the delegate skill's
single-negative-mention assertions must not be disturbed).

## T3 — the skill itself

**Files:** `skills/swingle-setup/SKILL.md` (new), `skills/swingle-setup/agents/openai.yaml` (new).

Author SKILL.md implementing the spec's §2–§6 exactly:

- Frontmatter `name: swingle-setup`; description covers the natural-language triggers
  (§3) and states explicit-invocation-only.
- Harness + root resolution preamble (grandparent rule), same shape as the delegate
  skill's.
- Phase A as spec §4: trust gate with the M4 "enumeration skipped" rule; **all env
  inspection via `validate-packs --health` + `--check-config`** (no manifest argv in
  skill prose); config-finding inventory incl. set-but-unreadable `$SWINGLE_CONFIG`
  (M2); registry layer record (I4); legacy-residue classification
  (untracked/tracked/target-exists, I5/I6); local-state-only baseline reads (I3
  criterion stated in the skill text); workspace ignore state.
- Phase B report format (the §4 table), OK / ACTION AVAILABLE / HAND-OFF grouping.
- Phase C consent rules: per-item, re-inspect-and-show-before→after, plain-question
  fallback restates the item, "yes to all" never covers destructive options.
- Phase D hand-off list verbatim from spec.
- Write inventory §6.1–§6.4 with the I4 shadowed-layer rule, M5 already-seeded-OK rule,
  I5/I6 migration branching, and the §5 tracked-files scope note (M3).
- Argument scoping rules (M1).
- Purity: no provider names in operational logic beyond reading packs; no model ids or
  invocation strings anywhere (cli/argv come from manifests at run time).

`agents/openai.yaml`: display name "Swingle Setup", implicit invocation OFF, default
prompt "Check and set up this machine's swingle environment with the swingle-setup
skill."

**Acceptance:** spec §2–§6 traceable line-by-line; existing purity glob tests pass over
the new files; **and the new SKILL.md is run through the `_cli_invocation` discriminator
from `tests/test_delegate_skill.py` standalone before T3 closes** (review finding P6 —
Phase B's sample report rows naming CLIs sit near the heuristic's boundary; verify
deliberately, don't discover in T4).

## T4 — structural tests for the setup skill

**Files:** `tests/test_setup_skill.py` (new).

- Frontmatter: `^name: swingle-setup$`; description present; explicit-only wording.
- Boundary guard (I7, precisely scoped): no line matches a probe label regex
  (`^#+ P\d+\b|P\d+\s+—` — spell the em-dash as an explicit `—` escape and
  declare the test file UTF-8, review finding P4) and no line contains a
  timeout-bounded probe invocation (reuse/adapt the `_cli_invocation` discriminator
  from `tests/test_delegate_skill.py`); the bare recommendation string
  `swingle-verify <id>` is asserted PRESENT (the Phase D hand-off must survive the
  guard).
- **Guard-strength fixtures (review finding P8)**: commit two deliberately-violating
  SKILL.md snippets under `tests/fixtures/setup-skill/` (one embedding a P-label probe
  step, one embedding a probe invocation) and assert the boundary guard FAILS on each —
  the self-audit becomes a committed regression test.
- No-superpowers: setup's SKILL.md never mentions a superpowers skill invocation,
  `scripts/sdd-workspace`, or `.superpowers/` except (if needed) a single negative
  disclaimer — mirror the delegate suite's exact-count pattern only if the disclaimer
  is included; otherwise assert zero mentions.
- Consent invariants greppable: the phrases "consent" (per-item) and "never" +
  "yes to all" destructive-exclusion rule appear (cheap tripwires against prose edits
  dropping the guarantees).

**Acceptance:** suite green; deliberately breaking any invariant in a scratch copy
fails the matching test.

## T5 — docs & distribution surfaces

**Files:** `README.md`, `CLAUDE.md`, `codex/INSTALL.md`, `scripts/codex-smoke`,
`skills/sdd/SKILL.md`, `skills/delegate/SKILL.md`.

- README: Skills table row for `swingle-setup`; one install-section line ("after
  installing, run `swingle-setup` for a guided environment check"); Model-tiering
  registry prose reordered to name the skill first, raw script second.
- Both dispatch skills: reword the once-per-session no-override-layer nudge to point at
  `swingle-setup` (spec §2 last line) — keep "never create user config uninvited".
- CLAUDE.md: skills table row (name | `skills/swingle-setup/` | owns).
- `codex/INSTALL.md`: mention in Prerequisites.
- `scripts/codex-smoke`: add existence checks for `skills/swingle-setup/SKILL.md` and
  `skills/swingle-setup/agents/openai.yaml` (the smoke script is presence-checks only —
  verified at plan time — so the new skill must be added to be covered at all).

**Acceptance:** validator link scan green; README/CLAUDE/codex surfaces list all four
skills consistently.

## T6 — migration-runbook guard (I6 spillover)

**Files:** `docs/migration-3.0.0.md`.

Add the both-exist guard to ALL THREE moves in the runbook (review finding P7 — the
directory move nests, and the config-**file** rename silently *replaces* an existing
`.swingle.json` with the old file, which is just as destructive):

```bash
# step 1 (config file): guard before git mv / mv
[ -f .swingle.json ] && echo "BOTH config files exist — reconcile manually or run swingle-setup" || <existing rename>
# step 2 (directory): a bare mv into an existing target NESTS the source inside it
[ -d .sdd-dispatch ] && { [ -e .swingle ] && echo "BOTH exist — merge manually or run swingle-setup" || mv .sdd-dispatch .swingle; }
# per-machine (~/.config): same both-exist guard
```

This is a correction to live migration instructions, not a rewrite of a historical doc
(3.0.0 is the current migration).

**Acceptance:** every runbook move is copy-paste safe under partial-prior-migration
state (target-exists → explicit message, never a silent nest or replace).

## T7 — version, gate, review

**Files:** `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `README.md`.

- Bump all three version stamps to `3.1.0` (validator sync check enforces).
- Full suite + hard gate chained to the commit.
- Final whole-branch review (most-capable tier, review lane) before the PR is marked
  ready — per `core/roles.md` final-review row.

**Acceptance:** gate green; PR to `develop` (retarget after the 3.0.0 PR merges);
backlog issues from spec §10 filed on merge.

---

## Task-level review policy

T1 and T3 are the judgment-bearing tasks — per-task review (standard tier, review
lane) after each. T2/T4/T5/T6 are mechanical-to-adaptation; controller gate suffices
unless a reviewer is explicitly requested. T7 includes the final review by definition.

## Risks

- **`--health` probe execution**: readiness/version argv come from manifests;
  the mode must keep the validator's data-only discipline (argv arrays executed
  directly, never via shell). Test with a stub CLI, never a live one.
- **T1 is a restructure, not an addition** (review findings N1/P2): factoring
  `--step0`'s inline body into shared helpers and making the argparse branches
  compose touches the dispatch skills' one load-bearing script — `--step0`'s
  external behavior is pinned by existing tests; run the full validator suite after
  the refactor commit, before building `--health` on top.
- **Nudge rewording** touches the dispatch skills' Step-0 prose; the delegate
  structural suite pins several exact strings — run it after T5, not just at T7.
- **`_cli_invocation` boundary on Phase B sample rows** (review finding P6): the
  skill's illustrative report table names CLIs; verify against the discriminator at
  T3 close, not first at T4.
- **Stacked branch**: if `develop` moves under the stack (3.0.0 PR merged with
  changes), rebase before T7's final review so the review covers what will merge.
