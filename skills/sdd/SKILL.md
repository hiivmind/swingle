---
name: swingle-sdd
description: >-
  Execute a written implementation plan through subagent-driven-development with
  swingle-delegate at each external dispatch point. Use for plan execution; keep the
  installed workflow as the authority for planning, task order, reviews, fixes, and
  completion.
---

# SDD Through Swingle Delegate

The installed `subagent-driven-development` workflow is the sole authority for task
order, review, fixes, and completion. This wrapper supplies transport and shared state;
it never creates a second task, role, review, setup, worktree, liveness, retry, parser,
or completion policy.

## Start one shared SDD run

Resolve `$PLUGIN_ROOT` from this skill's installed location and `$REPO_ROOT` from the
repository that requested the plan. Resolve one project-local ledger directory:

```text
$REPO_ROOT/.swingle/delegate/ledger/
```
This explicit directory is the SDD run-ledger path shared by the controller and every
delegate; no delegate selects a different path.

Create no ledger until the plan is accepted and dispatch is about to begin. At that
point, start exactly one SDD run:

```bash
python3 $PLUGIN_ROOT/scripts/swingle ledger start \
  --dir $REPO_ROOT/.swingle/delegate/ledger/ \
  --kind sdd \
  --controller-session-id <controller-session-id>
```

Retain the returned `controller-session-id`, `run-id`, and ledger directory. The
controller session ID identifies this run's event stream; `run-id` identifies the SDD
plan execution. Pass both IDs, the ledger directory, and `$REPO_ROOT` to every
delegate call. Do not initialize an empty ledger or write a readiness marker merely
because the wrapper was invoked.

## Per-job controller flow

Keep the installed SDD workflow's current task and review sequence. For each job, and
before any allocation, run the read-only context command with the job's explicit role,
tier, provider intent, model, effort, and repository:

```bash
python3 $PLUGIN_ROOT/scripts/swingle dispatch context \
  --project $REPO_ROOT \
  --role <role> \
  --tier <tier> \
  [--provider <provider-id>] \
  [--model <model-id>] \
  [--effort <effort-id>]
```

Handle the one returned `next_action`. Preserve the job's exact authored task and
explicit values when choosing, repairing, grounding, or refreshing context. Allocate
only after the action is dispatchable, with the same explicit repository and shared run:

```bash
python3 $PLUGIN_ROOT/scripts/swingle ledger allocate \
  --project $REPO_ROOT \
  --dir $REPO_ROOT/.swingle/delegate/ledger/ \
  --controller-session-id <controller-session-id> \
  --run-id <run-id> \
  --role <role> \
  --contract <contract-path> \
  --tier <tier> \
  --task <exact-task-summary>
```

Retain the returned artifact directory for that job. The controller, not a direct
sub-run helper, appends the job's typed lifecycle records to this same SDD run and
session. Use the allocated job ID and shared IDs for:

```text
grounding-observed or grounding-reused
dispatched
provider-session (when supplied)
retry/attempt records (when applicable)
complete
```

Do not call `ledger begin-direct` or `ledger finish-direct` for an allocated SDD job:
those commands create and finalize a separate direct run. The controller performs the
provider transport, interpretation, repository verification, and typed record appends
against the existing allocation, then retains both independently interpreted outcomes.

For each job, retain both independently interpreted outcomes:

- `provider_outcome` — exit, output, report, session, and provider concerns.
- `repository_verification` — changed paths, requested contents, invariants, and tests.

Only `VERIFIED` repository verification permits a successful mutating completion.
Preserve the provider's raw output and authored evidence in the returned artifact
directory; temporary parser and artifact management stay controller-owned. Do not
replace either outcome with a provider self-report.

## Shared ledger lifecycle

The controller retains each job's terminal status in the one shared SDD run. Its
per-job lifecycle is:

```text
dispatch context
ledger allocate
grounding-observed/reused
dispatched
provider-session/retry records
complete
```

Never use `begin-direct` or `finish-direct` in this flow. They are direct-run helpers,
not SDD job transitions.

For concurrent jobs, the controller waits for or joins concurrent jobs. If the run is
stopping, terminalize every remaining allocated job with one valid `complete` event.
Do not finalize while an allocated job is active. Every allocated job must have exactly
one terminal `complete` event before finalization.

When all allocated jobs are terminal and no further jobs will be allocated, invoke the
sole finalizer:

```bash
python3 $PLUGIN_ROOT/scripts/swingle ledger finalize-run \
  --project $REPO_ROOT \
  --dir $REPO_ROOT/.swingle/delegate/ledger/ \
  --controller-session-id <controller-session-id> \
  --run-id <run-id>
```

`ledger finalize-run` calls `finalize_run`. It rejects an absent or duplicate
`run-started`, every nonterminal allocation, and an existing `run-completed`. It derives
the run status in this order:

```text
BLOCKED > NEEDS_CONTEXT > DONE_WITH_CONCERNS > DONE
```

It emits exactly:

```text
jobs=N done=N done_with_concerns=N needs_context=N blocked=N
```

It appends exactly one typed `run-completed`, after the `complete` event for each
allocated job. The direct caller cannot emit the final event; the finalizer rejects a
caller-supplied completion event. The final event contains both the derived status and
exact outcome.

## Authority and boundaries

The native SDD workflow remains the only authority for task order, review, fixes, and
completion. The controller owns context calls, `ledger allocate`, dispatch transport,
provider process control, output interpretation, repository verification, and final
ledger finalization. `swingle-delegate` owns provider mechanics and its direct ledger
transitions. This wrapper does not add a setup flow, worktree flow, liveness flow, retry
flow, parser loop, or review loop.
