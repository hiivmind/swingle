# Swingle Guidance Simplification Design

Date: 2026-08-21

Status: Approved in design workshop

Repositories:

- `hiivmind/swingle`
- `hiivmind/swingle-automation`

## Purpose

Swingle is a SKILLS plugin. It gives an LLM guidance for delegation to an installed provider CLI.

The LLM is the controller. The provider CLI is the authority for its current operation.

Swingle does not certify provider releases. Swingle does not maintain a second model catalog.

Swingle retains two valuable controls:

- role contracts that improve delegated work
- a ledger that records the delegation audit trail.

Provider notes retain only non-obvious failures and proven recoveries.

## Problem

The current package treats each provider CLI as a versioned protocol that Swingle must certify.

This design causes four failures.

### Provider facts become stale

Swingle records versions, models, flags, output formats, permissions, sandbox behavior, and session commands.

Provider releases can occur many times each day. The installed CLI changes faster than the recorded pack.

A health run during this audit found six version mismatches across seven installed providers. All readiness commands succeeded.

The live CLI catalogs also exceeded the static Swingle catalogs:

- Grok used `grok-4.6` as its default. The pack routed only `grok-4.5`.
- AGY listed Gemini 3.7 and Claude models. The pack contained older Gemini rows.
- Pi listed 18 available models. The pack contained eight routing rows.
- OMP listed about 165 models. The pack contained ten routing rows.
- opencode listed many current models. The pack contained seven routing rows.

Static rows therefore blocked models that the installed CLI accepted.

### Routine certification consumes quota

The verification protocol defines P1 through P13.

A routine round uses 10 to 12 model runs before model qualification and repeated intermittent probes.

Recorded rounds used 14 probes for Codex and 16 probes for Grok.

The automation documentation records about half a day for one six-provider sweep.

This cost does not validate delegated work. It repeats facts that the provider CLI already exposes.

### Healthy delegation has too many gates

A one-job delegation currently enters a large setup pipeline.

The pipeline validates all packs, reads configuration, resolves static models, compares versions, probes readiness, and reads provider references.

It can also inspect provider logs, read controller adapters, copy contracts, create a workspace, and construct a custom liveness wrapper.

Most of these steps occur before useful work starts.

### Swingle crosses the ownership boundary

The current package records controller tool names, controller install paths, provider auth state, provider upgrade commands, and provider runtime behavior.

These facts belong to the current harness and provider CLI. They do not belong to Swingle.

## Audit size

The audited surfaces contain about 7,466 lines:

| Surface | Lines |
| --- | ---: |
| `core/` | 893 |
| Four skills | 1,076 |
| Current provider bodies | 721 |
| Provider model tables and narratives | 525 |
| Provider verification logs | 1,146 |
| Python validator code | 1,027 |
| Main validator and skill tests | 1,290 |
| Drift automation | 788 |

The current model tables contain 44 static routing rows.

The target removes whole certification concepts. It does not shorten their current descriptions.

## Ownership doctrine

### Swingle owns

Swingle owns universal, provider-independent state:

- role contracts
- prompt assembly guidance
- ledger format and append behavior
- Swingle configuration and precedence
- advisory provider and model preferences
- provider gotcha-note structure
- repository integrity for Swingle files.

### The LLM owns

The LLM uses the tools that its current harness exposes.

The LLM performs these actions:

- resolve the requested provider executable
- inspect current CLI help
- inspect the live model surface when selection needs it
- build the provider command
- run and observe the command
- resume or diagnose the command
- validate the delegated result
- record the audit trail.

### External runtimes own

Swingle does not cache, certify, or gate these facts:

- controller identity
- controller capabilities
- controller tool names
- controller install paths
- native subagent availability
- provider version
- provider authentication
- provider readiness
- provider command grammar
- provider permissions
- provider sandbox behavior
- provider models
- provider effort levels
- provider output formats
- provider session storage
- provider upgrades.

### Python boundary

Python code can manage only universal Swingle state and deterministic Swingle structure.

Python code must not run or inspect provider or controller binaries.

`<root>` is the directory that contains `skills/`, `contracts/`, `providers/`, and `scripts/`.

The target command surface is:

```text
python3 <root>/scripts/swingle config init|show|validate|set
python3 <root>/scripts/swingle ledger init --path <path>
python3 <root>/scripts/swingle ledger append --path <path> <event fields>
python3 <root>/scripts/swingle ledger show --path <path>
python3 <root>/scripts/swingle check
```

`swingle check` is authoring and CI tooling. Delegation must not run it as a preflight.

## Skill set

The plugin ships three skills.

### `swingle-delegate`

This skill is the primary delegation primitive.

It accepts one self-contained job or one homogeneous batch.

It performs this flow:

1. Resolve `<root>` from the loaded skill path.
2. Select the applicable role contract, tier, and ledger path.
3. Read the Swingle configuration through the vendored script.
4. Stop policy routing when configuration has errors.
5. Continue with normalized configuration when it has warnings only.
6. Reject a provider that user policy lists in `disable`.
7. Use an explicit provider before lane and default preferences.
8. Use `providers_by_lane`, then `default_provider`, when no provider is explicit.
9. Surface a missing preferred executable. Do not silently substitute another provider.
10. Pass an explicit user model directly to the provider CLI.
11. Otherwise apply the selected tier's live model preferences or use the CLI default.
12. Initialize the selected ledger and record the allocation.
13. Check that the selected executable exists.
14. Inspect current help when command syntax is not established in the session.
15. Inspect current help after any rejected or unknown invocation.
16. Run the provider with the current harness tools.
17. Record provider, model, session, attempts, status, outcome, and evidence.
18. Validate the requested result before reporting completion.

A missing executable is the only provider preflight blocker. A malformed Swingle policy blocks routing, not provider availability.

The skill does not perform these actions:

- run Step 0
- validate all provider notes
- compare versions
- probe auth or readiness
- resolve static model eligibility
- inspect controller adapters
- create worktrees
- probe superpowers availability
- choose native subagents
- select a supervision flavor
- read provider history on the healthy path.

If isolation is necessary, the LLM prepares the workspace before delegation.

Swingle receives a working directory. Swingle does not decide how the LLM created it.

### `swingle-setup`

This skill manages Swingle-owned setup only.

It can perform these actions:

- show the effective Swingle configuration
- validate or create the Swingle configuration
- show or edit advisory preferences
- initialize or inspect ledger paths
- report executable presence for known providers.

Executable presence is informational. Setup does not define provider availability for later sessions.

The skill does not perform these actions:

- probe provider auth
- compare provider versions
- probe readiness
- inspect controller installation
- inspect plugin paths
- inspect provider permission baselines
- probe superpowers
- hand work to a verification skill
- search for old controller layouts.

### `swingle-sdd`

This skill remains as a small workflow wrapper.

It performs only these actions:

1. Run the installed `subagent-driven-development` workflow.
2. Route each external dispatch through `swingle-delegate`.
3. Add provider, model, session, attempt, and outcome evidence to the run ledger.

The installed SDD workflow remains the process authority.

`swingle-sdd` does not restate briefs, reviews, fix cadence, worktree rules, superpowers rules, or final review rules.

### Removed skill

Remove `swingle-verify`.

Provider releases and model releases do not trigger Swingle work.

## Contracts

Retain these contracts:

- `contracts/implementer-contract.md`
- `contracts/reader-contract.md`
- `contracts/task-reviewer-contract.md`
- `contracts/design-reviewer-contract.md`

Make each contract independent of provider transport.

A dispatch can use one of two report modes:

- a report file plus a short final status
- a captured full final response plus a status.

The LLM selects the mode from current CLI help and applicable gotchas.

No provider manifest field selects the report mode.

Retain the four statuses:

- `DONE`
- `DONE_WITH_CONCERNS`
- `NEEDS_CONTEXT`
- `BLOCKED`

The statuses support workflow routing and the ledger. They do not prove that work is correct.

## Ledger

Keep a human-readable Markdown ledger.

The Python CLI performs atomic appends. It never rewrites prior events.

Direct delegation uses `<project>/.swingle/delegate/ledger.md` unless the caller passes another path.

The SDD wrapper passes its run-ledger path into every `swingle-delegate` call.

All events for one run use the same ledger path.

Use one event vocabulary for direct delegation and SDD:

```text
NNN allocated: role=<role> task=<summary> contract=<path>
NNN dispatched: provider=<id> model=<id|provider-default> attempt=<n>
NNN session: attempt=<n> <session-id>
NNN attempt-failed: attempt=<n> signature=<summary> recovery=<summary>
NNN resumed: session=<id> reason=<reason>
NNN complete: status=<status> outcome=<outcome>
```

The ledger records what occurred. It does not establish provider compatibility.

## Configuration

Use one configuration file with whole-file precedence:

1. `$SWINGLE_CONFIG`
2. `<project>/.swingle.json`
3. `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`

The target schema is:

```json
{
  "disable": [],
  "providers_by_lane": {},
  "model_preferences": {
    "<provider>": {
      "cheapest": ["<preferred-model>"],
      "standard": ["<preferred-model>"],
      "most-capable": ["<preferred-model>"]
    }
  }
}
```

`default_provider` is optional.

### Provider preferences

`disable` is explicit user policy. Swingle must honor it.

`default_provider` and `providers_by_lane` are routing preferences.

If a preferred provider executable is missing, the LLM surfaces that fact. It does not silently substitute another provider.

### Model preferences

Model preferences are ordered hints. They are not eligibility records.

The LLM uses a preferred model only when the current CLI exposes it.

If no preference matches, the LLM uses the CLI default.

An explicit user model bypasses Swingle preferences. The provider CLI accepts or rejects that model.

Swingle must not reject the model from cached data.

### Tier policy

An explicit user tier has precedence.

Use `cheapest` for transcription, mechanical implementation, and focused codebase location.

Use `standard` for adaptation implementation, external synthesis, and task review.

Use `most-capable` for large or long-context implementation, design review, and final review.

The tier selects one advisory preference list. It never excludes a live model.

Configuration commands derive known provider IDs from provider directory names.

They do not parse provider notes. Only `swingle check` parses every note.

### Removed configuration

Remove these keys and paths:

- `require-verified-version`
- `superpowers`
- `$SWINGLE_MODELS`
- `<project>/.swingle/models/`
- `${XDG_CONFIG_HOME:-~/.config}/swingle/models/`

Malformed optional preferences can produce a warning. They must not make an installed provider unavailable.

## Provider notes

Each provider has one living Markdown note.

Use this format:

```markdown
# <Provider> gotchas

CLI: `<executable>`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| <observable signature> | <unreliable result> | <proven action> | <issue, commit, or date> |
```

A gotcha must pass all inclusion rules:

1. The behavior is silent, misleading, confusing, or missing from normal help.
2. The behavior occurred in real operation.
3. The note changes recovery after the LLM observes the signature.

Every gotcha row requires evidence. An empty Evidence cell is invalid.

Do not include these items:

- successful probe results
- command tutorials
- model catalogs
- effort values
- permission summaries
- sandbox inventories
- output-format inventories
- changelog summaries
- current version claims
- cross-provider comparison tables.

Provider notes are living guidance. Update or remove a note when it is no longer true.

Git retains the history. Swingle does not ship append-only verification history.

## `swingle` repository changes

### Remove

Remove these surfaces:

- `controllers/`
- `core/verification-protocol.md`
- `core/verification-log.md`
- `core/liveness.md`
- `skills/swingle-verify/`
- provider `versions/`
- provider `log/`
- provider `verification-log.md`
- provider `models.yaml`
- provider `models.md`
- Step-0 implementation and tests
- version and readiness implementation and tests
- static model resolution implementation and tests
- provider health implementation and tests
- worktree and superpowers guidance in Swingle skills

### Replace

Replace each `providers/<id>/pack.md` with CLI identity and a gotcha table.

Reduce `core/playbook.md`, `core/roles.md`, and `core/safety-doctrine.md` to generic policy.

Fold a file into a skill when the file has no independent reader.

Replace `scripts/validate-packs` and `scripts/swingle-models` with the unified `swingle` command.

Replace the release workflow call to `scripts/validate-packs` with `scripts/swingle check`.

Replace the verification-finding issue form with an observable provider-behavior and guidance-gap form.

Reduce `lib/swingle/` to configuration, ledger, and authoring checks.

Update the README and authoring documentation for the new ownership boundary.

### Open pull request migration

PR #55 contains an opencode caveat in the old structure.

Extract only valid, non-obvious gotchas into the new provider table.

Then close or supersede PR #55. Do not merge its old structure unchanged.

## `swingle-automation` changes

### Remove provider maintenance

Remove these paths:

- `TEMPLATE-drift-verify.md`
- `drift-verify-agy/`
- `drift-verify-claude/`
- `drift-verify-codex/`
- `drift-verify-grok/`
- `drift-verify-opencode/`
- `drift-verify-pi/`
- `probe-runtime/`

Automation no longer upgrades provider CLIs or runs provider probes.

### Change issue triage

Remove these concepts from `TEMPLATE-issue-triage.md`:

- verification-finding fields
- drift-stub routing
- `Awaiting verifier`
- verifier reconciliation.

Provider behavior reports use the normal `Triaged` status.

### Change issue investigation

`TEMPLATE-issue-investigate.md` investigates only the reported behavior.

The lane uses the live CLI and current help.

It never reconstructs the old probe matrix.

A confirmed failure can produce one of three results:

- provider gotcha-table update
- generic skill guidance update
- no Swingle change because current help explains the behavior.

### Change issue fixes

`TEMPLATE-issue-fix.md` uses `swingle-delegate` for external work.

It does not resolve roles through static model tables.

It records the actual provider and model from the live run.

A gotcha change is a normal product change. It is not a stamped pack fact.

### Change conventions

Remove these sections from `CONVENTIONS.md`:

- provider and install locks
- version and probe rules
- append-only verification logs
- registry carry-forward
- drift result fields
- `Awaiting verifier`
- complete-matrix thresholds
- provider supervised-run records
- provider runtime inventories.

Keep these automation-owned rules:

- worktree isolation for repository changes
- scoped GitHub credentials
- the GitHub write allowlist
- one stage per issue lane
- result files
- operator-only `Ready to fix` and merge gates
- the shared lock for social lanes that write one repository.

Rewrite `swingle-automation/CLAUDE.md` so that it lists only active lanes and current checks.

### Change operations

The remaining issue cycle is:

```text
triage → investigate → operator Ready to fix → fix and review → operator merge
```

Social-listening lanes remain separate.

No schedule reacts to provider releases or model releases.

### Migrate board and result data

After the new automation merge is deployed, pause affected schedules and move existing `Awaiting verifier` items to `Triaged`.

Remove `drift-verify` and `runtime-probe` from the current result schema.

Remove version, probe, and stamp fields.

Keep old result files as historical artifacts. New automation does not consume them.

## Future-change doctrine

Replace conflicting certification sections in `CLAUDE.md`, then add this doctrine:

1. The LLM is the controller.
2. The live provider CLI is the authority for provider operation.
3. Swingle never gates a provider by cached runtime facts.
4. Python code manages only universal Swingle state and structure.
5. Provider notes contain only real, non-obvious failure guidance.
6. Preferences steer selection. Preferences never define availability.
7. Healthy delegation checks executable presence, briefs the task, records the ledger, and runs.
8. Contracts and the ledger remain because they improve quality and auditability.
9. Automation responds to observed product failures. It does not certify providers on a schedule.
10. If CLI behavior is unclear, inspect current help before adding guidance.

Repeat the author-facing provider-note rules in `docs/pack-authoring.md`.

## Migration

Release this change as a new major version.

Do not add compatibility readers for removed provider registries, model catalogs, Step-0 output, or automation result kinds.

When the user runs `swingle-setup`, it can migrate the current Swingle configuration:

1. Retain `disable`, `default_provider`, and compatible lane routing.
2. Remove `require-verified-version` and `superpowers`.
3. Inspect old model overrides in `$SWINGLE_MODELS`, the project layer, and the user layer.
4. Convert clear winning rows into advisory `model_preferences`.
5. Show cross-layer and lane conflicts for user selection.
6. Remove each obsolete directory or environment reference only after explicit approval.

The setup skill does not search for old controller installation layouts.

## Validation strategy

Permanent tests cover Swingle-owned behavior only.

### Configuration tests

- Whole-file precedence selects the correct configuration.
- Advisory model preferences retain their order.
- A stale preference does not reject a provider or model.
- Removed keys do not become active policy.
- Malformed optional preferences do not mark a provider unavailable.

### Ledger tests

- Initialization creates one valid Markdown ledger.
- Append operations are atomic.
- Event order is stable.
- Inspection returns all events without changing the file.
- Concurrent appends do not remove prior events.

### Authoring tests

- Each provider note has one CLI identity.
- Each provider note has the required gotcha-table columns.
- Provider packs contain no version registry or model catalog.
- Contract and skill references resolve.
- Internal links resolve.

### Python boundary test

Python commands must not run provider or controller binaries.

Use marker executables in `PATH`. Run every Python command and validate that no marker ran.

### Release smoke

Run one behavioral smoke before the major release:

1. Load `swingle-delegate`.
2. Delegate one read task through one installed provider.
3. Use current CLI help.
4. Validate contract use and ledger events.
5. Trigger one synthetic invocation failure.
6. Validate help-first recovery and a failed-attempt ledger entry.

Do not run a provider matrix. Do not qualify models. Do not perform a version sweep.

## Success criteria

The implementation is complete when all conditions are true:

- A healthy delegate reaches the provider after one executable-presence check and Swingle-owned artifact writes.
- No healthy path reads provider versions, model tables, verification logs, or controller adapters.
- An explicit model reaches the provider CLI without a Swingle eligibility gate.
- Stale preferences fall back to current CLI reality.
- Contracts and ledger records remain available for direct delegation and SDD.
- Provider notes contain only qualifying gotchas.
- Swingle Python code never runs external provider or controller binaries.
- Provider drift automation no longer exists.
- Provider behavior issues use the normal triage and investigation lanes.
- The contributor doctrine prevents certification machinery from returning.

## Non-goals

This design does not define provider command syntax.

This design does not define provider model quality.

This design does not define controller tool names or installation paths.

This design does not manage provider upgrades or authentication.

This design does not remove task-result validation.

This design does not remove contracts or the delegation ledger.
