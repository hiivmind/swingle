# Verdict: NOT READY FOR EXECUTION

Rev 3 closes most design issues, but two blockers remain: the pack trust boundary is still unsafe, and the plan’s validator/`--step0` implementation does not implement the rev-3 contract.

## 1. C1–C3 and I4–I13

| Finding | Status | Rev-3 evidence |
|---|---|---|
| C1 | **RESOLVED** | Fallback is explicitly same-provider, follows one ordered candidate list, caps at three total attempts, and makes provider changes a user decision ([rev 3:167](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:167), [rev 3:202](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:202)). |
| C2 | **PARTIALLY** | Rev 3 adds `argv[0] == cli`, metacharacter/path checks, and validation before execution, but validation is not pack trust/approval and still permits examples such as `cli: sh` with `["sh","-c","touch victim"]` or destructive non-shell CLIs ([rev 3:128](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:128)). |
| C3 | **PARTIALLY** | `--step0` now promises detection, config, compatibility, routing, and resolution, but its declared interface has no role/lane input, so it cannot apply `providers_by_lane` or perform role-to-model resolution unambiguously ([rev 3:300](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:300)). |
| I4 | **RESOLVED** | `native-subagents` branches before provider selection and is explicitly not a provider ([rev 3:181](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:181)). |
| I5 | **RESOLVED** | Exclusions are inputs; exact-lane candidates precede `any`; fallback advances through that order; three means three total attempts ([rev 3:165](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:165), [rev 3:202](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:202)). |
| I6 | **RESOLVED** | Ledger entries now include task, role, provider, model, class and outcome, with session-wide exclusion and compaction reconstruction rules ([rev 3:208](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:208)). |
| I7 | **RESOLVED** | Every provider has readiness through optional `readiness-argv`, defaulting to `version-argv`, with timeout and exit-zero semantics ([rev 3:123](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:123), [rev 3:228](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:228)). |
| I8 | **RESOLVED** | Version extraction, exact comparison, command/unparseable failure, warning, hard-block policy, and active-set effect are defined ([rev 3:220](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:220)). |
| I9 | **RESOLVED** | Front matter is explicitly a restricted line grammar, not general YAML ([rev 3:128](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:128)). |
| I10 | **RESOLVED** | Closed types, nested lane keys, unknown IDs, disabled targets, unreadable explicit paths, duplicate disables, and empty active sets are covered ([rev 3:235](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:235)). |
| I11 | **RESOLVED** | Rev 3 distinguishes one primary live destination from archive preservation and optional mirrors ([rev 3:327](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:327)). |
| I12 | **PARTIALLY** | Link scope now includes active docs, tombstones, contracts and Codex installation; `archive/` remains deliberately excluded, while contract purity is added ([rev 3:294](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:294)). This is a documented archival exception, not a blocker. |
| I13 | **PARTIALLY** | Concrete installation instructions and a filesystem/root-resolution smoke are required, but the check deliberately runs without Codex and release validation still calls discovery/resolution “on paper” ([rev 3:91](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:91), [rev 3:321](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:321)). |

## 2. Plan versus rev-3 spec

Most mechanisms have named tasks: migration/archive in Tasks 1–2, packs in Tasks 3–5, validator in Task 6, harness adapters and runtime procedure in Task 7, P13 in Task 8, packaging/tombstones in Task 9, and release in Task 10.

The problem is that Task 6’s supplied code and tests materially under-implement the specification.

| Required rule | Plan result |
|---|---|
| `argv[0] == cli` | **Partial.** The check and fixture exist, but empty argv arrays pass, and the allowed-token rules still permit interpreter execution and arbitrary relative operands ([plan:325](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:325)). |
| Restricted grammar | **No.** The parser silently ignores malformed lines, accepts single-quoted arrays and comments outside the grammar, overwrites duplicate keys, accepts unterminated front matter, and never validates the known schema version ([plan:308](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:308)). |
| Candidate order and exclusions | **Yes in code.** Exact-lane rows are sorted before `any`, and provider-specific exclusions work ([plan:383](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:383)). Tests should additionally cover exact P1 → exact P2 → `any` P1. |
| Full `--step0` pipeline | **No.** It performs path detection, disables, and rudimentary provider selection only. It does not execute/parse versions, enforce `require-verified-version`, run readiness, use `providers_by_lane`, resolve a model, or apply exclusions ([plan:433](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:433)). There is no role argument. |
| Config fail-closed | **No.** Search order and environment-path handling are absent; unknown provider IDs and nested value types are unchecked; wrong root/object types can crash; malformed config records a finding but is replaced with `{}` and processing continues ([plan:389](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:389)). |
| Other validator checks | **Missing.** The proposed code has no core/contracts purity check, version-sync check, all-Markdown link checker, documentary-section validation, or detection of a `providers/*/` directory missing `pack.md`, despite the spec requiring all of these ([rev 3:281](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:281)). |
| Fixture matrix | **Incomplete.** Multiple-active routing, wrong-typed/nested config, unknown IDs, version mismatch in both modes, readiness failure, config search order, and full Step-0 resolution are absent from the listed tests ([plan:194](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:194)). |

Additional plan/spec mismatches:

- Task 7 resolves models before selecting the provider, and says “exact-lane candidates, else `any`”; rev 3 requires provider selection first and exact candidates followed by `any` for fallback ([plan:506](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:506)).
- Task 1 still maps dispatch-reference change history to “archive only,” contradicting rev 3’s required primary live destination; its completeness checks do not verify unique primary ownership or mirrors ([plan:35](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:35)).
- The Codex adapter adds a prohibition on Codex-controller → Codex-provider dispatch that is absent from the spec and conflicts with `codex-if-active` routing unless formally specified ([plan:531](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:531)).
- The release task has no Claude Code install/load/Step-0 smoke, despite the spec’s both-harness release check.
- Requiring three installed CLIs in the release task effectively makes live probes a gate, contrary to the spec’s “environment smoke, never portable release gate” rule ([plan:576](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:576)).
- The plan title and authority statements still say “v2” and “rev 2,” not v2.1/rev 3 ([plan:1](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:1)).

## 3. New blockers

Two blocker-grade contradictions are newly present in the rewritten plan:

1. The migration task reintroduces archive-only ownership where rev 3 requires a primary live destination.
2. The Codex adapter invents a controller/provider prohibition that can override the specified routing algorithm.

The Step-0/validator problem is not conceptually new—it is C3 reintroduced at implementation-plan level.

## 4. Minimal changes needed

1. Define a real trust policy for copied/modified packs: explicit approval or provenance/allowlist before any manifest argv or prose is followed, plus protection against interpreter/destructive CLI declarations.
2. Add a role/lane input to `--step0`, then replace Task 6’s skeleton and fixtures so the full rev-3 validator contract is implemented, including strict grammar, compatibility/readiness, config search and all fail-closed cases, purity, links, and version sync.
3. Reorder Task 7 to native bypass → provider routing → model resolution → readiness; use exact-lane followed by `any`.
4. Bring Task 1’s primary/mirror ownership rules into line with rev 3 and give change history a live primary owner.
5. Remove or specify the Codex-controller restriction; add the required Claude smoke and at least one real Codex discovery/root-resolution smoke. Keep absent live provider CLIs non-blocking.
6. Correct all rev/version labels.

With those changes, the plan would be ready to execute.