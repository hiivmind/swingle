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
Run mechanical grounding — help inspection, model listing, config and ledger reads,
and failure-repair hunts — per [references/isolation.md](../../references/isolation.md):
isolated in a harness subagent when one exists, inline otherwise. The dispatch itself
and every ledger write stay in this thread.
See [references/concepts.md](../../references/concepts.md) for how the classification
matrix, contract, tier, provider, model, and effort relate.

## Procedure

1. Select the contract: `reader`, `implementer`, `task-reviewer`, `design-reviewer`,
   `independent-review`, or `fact-checker` — classify through the matrix in
   [references/concepts.md](../../references/concepts.md). Use `general-task` only when
   the request resists classification or arrives composite and entangled.
2. Select an explicit tier or derive one from the Tier policy.
3. Use the caller ledger path. Otherwise use `<project>/.swingle/delegate/ledger.md`.
4. Read policy with `python3 <root>/scripts/swingle config show --project <working-directory>`.
5. If configuration has errors, stop policy routing and surface them for repair.
6. If configuration has warnings only, continue with its normalized configuration.
7. Reject a provider listed in `disable`, including an explicit provider.
8. Select an explicit provider before `providers_by_contract` (role-level or
   tier-keyed) and `default_provider`.
9. If no provider resolves, ask the user. Do not silently choose one.
10. If the selected executable is missing, surface it. Do not silently substitute another provider.
11. Pass an explicit user model directly to the provider CLI.
12. Otherwise use the selected tier's preference when the live CLI exposes it. Use the CLI default when none match.
13. Resolve effort together with the model as one joined choice at dispatch time: inspect current `--help` for how this CLI accepts effort alongside the model — a separate flag, folded into the model identifier, a config-override mechanism, or none — set what it exposes, and never carry one provider's pattern to another.
14. Initialize the ledger with `python3 <root>/scripts/swingle ledger init --path <ledger-path>`.
15. Record the allocation with the exact event shape in the Ledger events section below.
16. If current command syntax is not established, inspect top-level and subcommand `--help`, and consult the selected provider's dispatch-guidance note rows for mechanics the help under-specifies, verifying each against the help just inspected. Inspect the help again before retrying any rejected invocation.
17. Give the provider the contract, task, working directory, inputs, and report mode.
18. Run the provider with the tools available in the current harness.
19. Record provider, model or provider-default, session when available, and each attempt in the same ledger.
20. Validate the requested result before reporting completion.
21. Append the exact `NNN complete: status=<status> outcome=<outcome>` event to the same ledger.

## Ledger events

Record each applicable delegation step in the shared ledger with one of these exact
one-line event shapes:

```text
NNN allocated: role=<role> task=<summary> contract=<path> tier=<cheapest|standard|most-capable>
NNN dispatched: provider=<id> model=<id|provider-default> attempt=<n>
NNN session: attempt=<n> <session-id>
NNN attempt-failed: attempt=<n> signature=<summary> recovery=<summary>
NNN resumed: session=<id> reason=<reason>
NNN complete: status=<status> outcome=<outcome>
```

`tier=` is part of the current allocated-event shape; include it on every allocation.
Ledgers written before this field existed keep their historical lines as records of the
old format — do not rewrite or delete them.

## Provider notes

`<root>/providers/<selected-provider>/pack.md` holds two evidence-backed tables with
different read timing. **Dispatch guidance** is proactive: consult it while building an
unfamiliar dispatch, and verify each row against the help inspected this run. **Gotchas**
are reactive: open them only after an observed failure.

## Tier policy

An explicit user tier has precedence. Otherwise derive the tier by intent per
[references/model-tiering.md](../../references/model-tiering.md). The tier selects one
advisory preference list. It never excludes a live model.

## Failure recovery

After an observed failure, apply a matching row from the Gotchas table of
`<root>/providers/<selected-provider>/pack.md`, then record the failed attempt.
If no row matches, inspect current help again before retrying.
Ask the user only when the provider CLI cannot resolve the blocker.

## Audit statuses

Use `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
The status routes work. The delegated result supplies completion evidence.
