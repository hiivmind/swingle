---
name: swingle-delegate
description: >-
  Directly delegate an explicitly requested, self-contained job or homogeneous batch to an
  installed provider CLI using live CLI help, Swingle contracts, configuration, and ledgers.
  Use swingle-sdd for dependency-aware implementation plans. Explicit invocation only.
---

# Delegate Through an Installed CLI

## Boundary

The LLM is the controller. The provider CLI is the authority for its current operation.
Use this skill for one self-contained job or one homogeneous batch.
Use `swingle-sdd` for a dependency-aware implementation plan.
Resolve `<root>` as `Path(<this SKILL.md>).parents[2]`. It must contain `skills/`, `scripts/`, `contracts/`, and `providers/`.
Run every Swingle-owned command as `python3 <root>/scripts/swingle`.
See [references/concepts.md](../../references/concepts.md) for how lane, role, provider,
tier, model, and effort relate.

## Procedure

1. Select the reader or implementer contract (lane `implement`), or the task-reviewer or
   design-reviewer contract (lane `review`). Lane is derived from this choice, not picked
   separately.
2. Select an explicit tier or derive one from the Tier policy.
3. Use the caller ledger path. Otherwise use `<project>/.swingle/delegate/ledger.md`.
4. Read policy with `python3 <root>/scripts/swingle config show --project <working-directory>`.
5. If configuration has errors, stop policy routing and surface them for repair.
6. If configuration has warnings only, continue with its normalized configuration.
7. Reject a provider listed in `disable`, including an explicit provider.
8. Select an explicit provider before `providers_by_lane` and `default_provider`.
9. If no provider resolves, ask the user. Do not silently choose one.
10. If the selected executable is missing, surface it. Do not silently substitute another provider.
11. Pass an explicit user model directly to the provider CLI.
12. Otherwise use the selected tier's preference when the live CLI exposes it. Use the CLI default when none match.
13. Initialize the ledger with `python3 <root>/scripts/swingle ledger init --path <ledger-path>`.
14. Record the allocation with the exact event shape in the Ledger events section below.
15. If current command syntax is not established, inspect top-level and subcommand `--help`.
16. Give the provider the contract, task, working directory, inputs, and report mode.
17. Run the provider with the tools available in the current harness.
18. Record provider, model or provider-default, session when available, and each attempt in the same ledger.
19. Validate the requested result before reporting completion.
20. Append the exact `NNN complete: status=<status> outcome=<outcome>` event to the same ledger.

## Ledger events

Record each applicable delegation step in the shared ledger with one of these exact
one-line event shapes:

```text
NNN allocated: role=<role> task=<summary> contract=<path>
NNN dispatched: provider=<id> model=<id|provider-default> attempt=<n>
NNN session: attempt=<n> <session-id>
NNN attempt-failed: attempt=<n> signature=<summary> recovery=<summary>
NNN resumed: session=<id> reason=<reason>
NNN complete: status=<status> outcome=<outcome>
```

## Tier policy

An explicit user tier has precedence.
Use `cheapest` for transcription, mechanical implementation, and focused codebase location.
Use `standard` for adaptation implementation, external synthesis, and task review.
Use `most-capable` for large or long-context implementation, design review, and final review.
The tier selects one advisory preference list. It never excludes a live model.

## Failure recovery

Read only `<root>/providers/<selected-provider>/pack.md` after an observed failure.
Apply a matching recovery, then record the failed attempt.
If no row matches, inspect current help before retrying.
Ask the user only when the provider CLI cannot resolve the blocker.

## Audit statuses

Use `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
The status routes work. The delegated result supplies completion evidence.
