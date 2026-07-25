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
`--root`/`--project`). For each pack manifest, emit one line to stdout:

```
<id>: installed=<yes|no> version=<v|-> verified=<v> drift=<yes|no> readiness=<ok|fail|timeout|skipped> registry-layer=<env|project|user|default|->
```

- Reuses existing plumbing only: manifest parsing, `command -v` detection,
  `version-argv` execution, `readiness-argv` execution, `resolve_models` for the layer
  column. **No route selection, no role argument, exit 0 even when CLIs are missing**
  (missing CLIs are data, not findings) — exit non-zero only for the existing manifest
  findings.
- Readiness/version probes are timeout-bounded (reuse or add a single constant, ~30s);
  a timeout reports `readiness=timeout`, never hangs the mode.
- Uninstalled provider: `readiness=skipped`, `version=-`.
- `--health` composes with `--check-config <file>` in one invocation (setup Phase A
  calls both).

**Tests** (fixture-driven, no real CLIs): a fake pack whose `cli` is a stub script on a
temp PATH — installed/uninstalled, drift yes/no, readiness ok/fail/timeout (stub sleeps
past a test-shortened timeout), layer column agrees with `resolve_models` fixtures.
Assert `--health` never exits non-zero for environment states, only for manifest
findings.

**Acceptance:** spec §7 `--health` paragraph satisfied; `--step0` behavior untouched
(existing tests unchanged and green).

## T2 — `docs/config.md` (canonical config schema)

**Files:** `docs/config.md` (new), `skills/sdd/SKILL.md`, `skills/delegate/SKILL.md`.

Write the schema doc: the four keys (`disable`, `default_provider`,
`providers_by_lane`, `require-verified-version`) with types and semantics; the layer
walk and whole-file-wins rule; the dispatch STOP conditions verbatim (quoted as the
consumers enforce them); unknown-keys-are-warnings semantics (I1); the neutral template
JSON block (§6.2); `validate-packs --check-config` as the validation entry point.

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
the new files.

## T4 — structural tests for the setup skill

**Files:** `tests/test_setup_skill.py` (new).

- Frontmatter: `^name: swingle-setup$`; description present; explicit-only wording.
- Boundary guard (I7, precisely scoped): no line matches a probe label regex
  (`^#+ P\d+\b|P\d+ —`) and no line contains a timeout-bounded probe invocation
  (reuse/adapt the `_cli_invocation` discriminator from `tests/test_delegate_skill.py`);
  the bare recommendation string `swingle-verify <id>` is asserted PRESENT (the Phase D
  hand-off must survive the guard).
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

**Files:** `README.md`, `CLAUDE.md`, `codex/INSTALL.md`, `skills/sdd/SKILL.md`,
`skills/delegate/SKILL.md`.

- README: Skills table row for `swingle-setup`; one install-section line ("after
  installing, run `swingle-setup` for a guided environment check"); Model-tiering
  registry prose reordered to name the skill first, raw script second.
- Both dispatch skills: reword the once-per-session no-override-layer nudge to point at
  `swingle-setup` (spec §2 last line) — keep "never create user config uninvited".
- CLAUDE.md: skills table row (name | `skills/swingle-setup/` | owns).
- `codex/INSTALL.md`: mention in Prerequisites.

**Acceptance:** validator link scan green; README/CLAUDE/codex surfaces list all four
skills consistently.

## T6 — migration-runbook guard (I6 spillover)

**Files:** `docs/migration-3.0.0.md`.

Add the both-directories-exist guard to the runbook's step 2: check for an existing
`.swingle/` before `mv` (a bare `mv` nests the source inside the target); provide the
guarded form:

```bash
[ -d .sdd-dispatch ] && { [ -e .swingle ] && echo "BOTH exist — merge manually or run swingle-setup" || mv .sdd-dispatch .swingle; }
```

and the same guard for the `~/.config` move. This is a correction to live migration
instructions, not a rewrite of a historical doc (3.0.0 is the current migration).

**Acceptance:** runbook commands are copy-paste safe under partial-prior-migration
state.

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
- **Nudge rewording** touches the dispatch skills' Step-0 prose; the delegate
  structural suite pins several exact strings — run it after T5, not just at T7.
- **Stacked branch**: if `develop` moves under the stack (3.0.0 PR merged with
  changes), rebase before T7's final review so the review covers what will merge.
