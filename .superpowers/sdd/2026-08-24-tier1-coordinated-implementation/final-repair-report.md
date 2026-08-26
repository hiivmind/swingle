# Final Sol review repair report

## Status

Implemented all 19 Critical and Important findings from `sol-final-findings.md`.
Repair commits: `1d3c71f fix: repair final Sol review findings`; `778bb93 docs: preserve setup repair context`.

## Per-finding mapping

1. **Reused grounding schema** — `dispatch._ledger_event` no longer emits `evidence_commands` for `grounding-reused`; schema-safe warm dispatch coverage remains in `tests/test_dispatch.py` and ledger tests.
2. **Cold observed receipt identity** — `ledger.begin_direct` preserves a cached `grounding-observed` receipt ID/revision and generates an ID only for the uncached null sentinel. Regression coverage is in `tests/test_ledger.py`; delegate instructions preserve the event across context refresh.
3. **Shared SDD run** — `skills/sdd/SKILL.md` now requires typed grounding, dispatch, provider-session/retry, and complete records against the allocated shared run/job and forbids `begin-direct`/`finish-direct` for SDD jobs.
4. **Cache epoch scope recovery** — dispatch expands missing, invalid, stale/expired, and fully invalidated epochs to all nine scopes while retaining selected-scope behavior for partial contradictions. Covered by `tests/test_dispatch.py` and grounding tests.
5. **Newer full grounding profile** — full profiles replace the receipt epoch under the cache lock when profile-defining observation time is newer; older concurrent profiles are superseded and partial merges remain unchanged. Existing concurrency coverage plus `tests/test_grounding.py` verifies later-writer survival.
6. **Prompt transport and placeholders** — all shipped provider packs use native stdin, prompt-file, or file-argument transport instead of `$(cat "$PROMPT")`; provider workspace placeholders use `$REPO_ROOT`. Prompt byte-preservation coverage remains in `tests/test_prompt_transport.py`.
7. **Provider-grounding setup repair** — `skills/swingle-setup/SKILL.md` now requires refresh → live grounding → record → show with usable non-null expiry before `REPAIRED`.
8. **Derived finish status** — `finish_direct` accepts the supplied status from the CLI and rejects a mismatch before append; regression coverage is in `tests/test_ledger.py`.
9. **Nested completion validation** — `finish_direct` validates provider and repository objects before derivation, producing `LedgerValidationError` rather than a `KeyError`; regression coverage is in `tests/test_ledger.py`.
10. **Signed exit codes** — provider exit codes accept signed integers and reserve null for no-start outcomes. Schema coverage includes `-15` and missing-success-code rejection in `tests/test_ledger_schema.py`.
11. **Grounding show precedence** — grounding CLI TTL resolution now uses `resolve_config_path`, matching dispatch's selected whole-file configuration layer.
12. **Allocation artifact durability** — allocation creates the artifact directory and ignore file before appending the irreversible allocation event.
13. **Job ID reuse** — ledger validation now rejects job UUID reuse across runs in one session as well as cross-file collisions.
14. **Positive liveness thresholds** — resolved non-null liveness values require at least one second in ledger schema validation; regression coverage is in `tests/test_ledger_schema.py`.
15. **Contract role identity** — allocated contract basename must equal `<role>-contract.md`; regression coverage is in `tests/test_ledger_schema.py`.
16. **Canonical grounding scopes** — observed/reused ledger events reject unknown and duplicate scopes; regression coverage is in `tests/test_ledger_schema.py`.
17. **Concrete provider exit outcomes** — successful provider statuses require a concrete signed exit code; no-start outcomes may retain null.
18. **Typed record subparsers** — `ledger record` now has per-event argparse subparsers with event-specific flags; irrelevant flags are rejected. Coverage is in `tests/test_cli.py`.
19. **Regression and final verification** — focused, concurrency/liveness, full-suite, and whitespace checks were run as recorded below.

## Red/green evidence

Initial red observations while repairing:

- Before the cache status fix, `test_later_invalidation_rejects_older_observation` exposed an over-broad `invalid` classification for a partial contradiction.
- Before signed exit handling, the new `-15` regression failed with `exit_code must be an integer >= 0`.
- Before disabling argparse abbreviation, an irrelevant `--provider` flag was silently accepted as an abbreviation of `--provider-session-id`.
- Before the receipt behavior change, the pre-existing cold observed test asserted rejection of a cached receipt; it was updated to assert the required preservation semantics.

Green evidence after repair:

```text
Focused ledger/dispatch/grounding/CLI:
246 passed

Focused ledger/CLI/schema regressions after additions:
202 passed

Concurrency and liveness scenarios:
20 passed, 68 deselected

Full project suite:
333 passed in 5.78s

git diff --check:
(no output; exit 0)
```

Commands used:

```bash
uv run --with-requirements requirements.txt python -m pytest -q tests/test_ledger_schema.py tests/test_ledger.py tests/test_dispatch.py tests/test_grounding.py tests/test_cli.py
uv run --with-requirements requirements.txt python -m pytest -q tests/test_cli.py tests/test_ledger.py tests/test_ledger_schema.py
uv run --with-requirements requirements.txt python -m pytest -q tests/test_grounding.py tests/test_ledger.py tests/test_liveness.py -k 'concurrent_full_profiles_keep_later_observation or concurrent_disjoint_scope_merges_both_survive or concurrent_sessions_create_distinct_files or concurrent_writers_in_one_session_lose_no_events or two_writer_inversion_keeps_per_file_timestamps_monotonic or aggregate_order_matches_full_sort_oracle or exactly_one_final_event_valid_ledger_and_no_warnings or run_finalization_varied_order_mixed_result or liveness'
uv run --with-requirements requirements.txt python -m pytest -q
git diff --check
```

## Changed files

- Python: `lib/swingle/{cli,dispatch,grounding,grounding_cli,ledger,ledger_cli,ledger_schema}.py`
- Provider guidance: `providers/{agy,claude,codex,copilot,cursor-agent,grok,omp,opencode,pi}/pack.md`
- Skills: `skills/{delegate,sdd,swingle-setup}/SKILL.md`
- Regression tests: `tests/{test_cli,test_dispatch,test_ledger,test_ledger_schema}.py`

## Remaining concerns

- Provider live accounts and binaries were not invoked by this repair; provider pack transport is covered by the repository's byte-preservation fixture and the shipped command forms were structurally reviewed.
- The SDD skill is documentation/controller guidance; Python does not own or synthesize provider execution, so end-to-end SDD controller behavior remains the controller's responsibility.
- No push, PR, merge, or publish was performed.
