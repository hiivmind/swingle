---
name: swingle-delegate
description: >-
  Directly delegate an explicitly requested, self-contained job or homogeneous batch to an
  installed provider CLI using live provider mechanics, dispatch context, and the v2 ledger.
  Use swingle-sdd for dependency-aware implementation plans. Explicit invocation only.
---

# Delegate Through an Installed CLI

## Boundary

The LLM is the controller. The provider CLI is authoritative for its current operation.
The controller owns request interpretation, role and tier selection, explicit overrides,
consent, provider command construction, process control, result interpretation, repository
verification, retry, and ledger lifecycle. Python supplies read-only context, grounding,
and typed ledger transitions; it does not make the final provider, model, effort, retry,
or result decision. There is no command renderer or generic result interpreter in Python.

Use this skill for one self-contained job or one homogeneous batch. Use `swingle-sdd` for
a dependency-aware implementation plan. Keep the complete task in the requesting
repository or worktree.

## Canonical paths

Resolve the placeholders directly from the current invocation:

- `$PLUGIN_ROOT` is the installed plugin tree containing `skills/`, `scripts/`,
  `contracts/`, `providers/`, and `references/`. Derive it from this skill's location.
- `$REPO_ROOT` is the repository or worktree that requested the delegation.

Use only these paths:

```text
$PLUGIN_ROOT/scripts/swingle
$PLUGIN_ROOT/contracts/<role>-contract.md
$PLUGIN_ROOT/providers/<provider-id>/pack.md
$PLUGIN_ROOT/references/<name>.md
$REPO_ROOT/.swingle/delegate/ledger/
$REPO_ROOT/.swingle/grounding/<provider-id>.json
$REPO_ROOT/.swingle.json
```

The ledger directory is project state. Resolve it once from `$REPO_ROOT`; do not inspect
or create project state under `$PLUGIN_ROOT`.

## Common prefix

1. Classify the request's role with the matrix in
   [references/concepts.md](../../references/concepts.md). The available contracts are
   `reader`, `implementer`, `task-reviewer`, `design-reviewer`, `independent-review`,
   `fact-checker`, and `general-task`. Composite work is decomposed when its parts are
   independently executable; entangled work uses `general-task`.
2. Select an explicit tier or derive `cheapest`, `standard`, or `most-capable` from
   [references/model-tiering.md](../../references/model-tiering.md).
3. Run one read-only `dispatch context` command with the explicit user values:

   ```bash
   python3 $PLUGIN_ROOT/scripts/swingle dispatch context \
     --project $REPO_ROOT \
     --role <role> \
     --tier <tier> \
     [--provider <provider-id>] \
     [--model <model-id>] \
     [--effort <effort-id>] \
     [--report-mode <captured-output|report-file>] \
     [--resume] \
     [--liveness-policy-file <path|->]
   ```

   This combines configuration selection, routing precedence, provider and model
   candidates, grounding state, liveness policy, the selected provider pack path, and
   its Dispatch-guidance fingerprint. It does not run provider help, resolve an
   executable, build a command, or write cache, config, or ledger state.
The context's `grounding_source` and receipt metadata travel unchanged into the begin
context and any typed dispatch event.
4. Handle exactly one returned `next_action`. Accept returned candidates or explicitly
   override provider, model, effort, or liveness policy; every override reruns
   `dispatch context` with the explicit values before any ledger allocation.
5. Allocate ledger state only after the context is dispatchable. Never allocate a job
   for an unresolved executable or an explicit provider that cannot be grounded.

## `next_action` handlers

| Action | Controller behavior |
| --- | --- |
| `dispatch` | Accept candidates, call `ledger begin-direct`, compose Bash from current mechanics, transport the complete briefing, run and capture provider output, interpret the result, verify repository state when mutating, reconcile both outcomes, then call `ledger finish-direct`. |
| `choose_provider` | Ask for one provider choice, preserve the task and explicit values, then rerun context. |
| `setup_repair` | Explain the blocker and offer the exact targeted setup repair. Preserve task, role, tier, overrides, `$REPO_ROOT`, ledger directory, blocker, and config path. On `REPAIRED`, rerun context; on `DECLINED`, return `NEEDS_CONTEXT`; on a failed repair, stop. |
| `ground_and_record` | Give a read-only grounding worker the returned scopes and exact targets, or ground inline when isolation is unavailable. Record every scope as `observed`, `not-exposed`, or `unverifiable` with `grounding record`, obey its returned action, then rerun context when it says `refresh_context`. |
| `ground_without_cache` | Ground the required scopes, keep the normalized data in controller context, create an uncached begin context with a null receipt sentinel, and dispatch without cache I/O. |
| `refresh_context` | Rerun `dispatch context` and follow its single returned action. |

Do not reconstruct the grounding cache state machine in prose or in the controller.
The machine-computed action is the authority for the next step.

## Contract selection announcement

Emit one block per `dispatched` event, immediately before that attempt's provider
launch; never emit one summary per run. The announcement is informational only:
no pause, confirmation, consent, or prompt.

Use the accepted role and tier. Derive `contract` from the basename of
`$PLUGIN_ROOT/contracts/<role>-contract.md` by removing `-contract.md`. Use the
provider, model, and effort resolved for and transported to this specific producing
call, including `provider-default` or `none`. Use `attempt=1` as a known constant on
attempt-1 paths; on a retry use the exact integer transported to
`ledger record dispatched --attempt N`. Render run and job as full lowercase UUIDs.
Use the producing call's `artifact_dir` field returned verbatim; never reconstruct it.
Use the controller-held resolved `$REPO_ROOT` and `$PLUGIN_ROOT`.

For the announcement fields and the displayed artifact directory, render a value bare
only when it matches `^[A-Za-z0-9._/@+-]+$`; otherwise render it with
`json.dumps(value, ensure_ascii=True)`. Examples:
`gpt-5.2` → `model=gpt-5.2`; `foo effort=high` → `model="foo effort=high"`.

For the inspection command's two shell operands, JSON quoting is unsafe. Render each
resolved root with POSIX shell quoting via `shlex.quote` or equivalent before composing
the command; `/tmp/Swingle repo` → `'/tmp/Swingle repo'`. If either root contains a
literal CR or LF byte, reject the dispatch before rendering instead of emitting a
broken multi-line command. `$REPO_ROOT=/tmp/repo\nbreak` → reject;
`$PLUGIN_ROOT=/tmp/plugin\rbreak` → reject. The two roots are shell operands; the
artifact directory is still a display value.

## Consent and isolation

A direct task authorizes safe read-only inspection necessary for that task. It does not
authorize billable, permission-changing, destructive, or workspace-writing probes. When
safe help and listing do not establish a scope, record `unverifiable`; ask only if the
task cannot run safely without an extra probe.

Use a read-only grounding subagent only for live provider inspection. Keep configuration,
context decisions, cache writes and invalidation, ledger writes, consent, and dispatch in
the controller. A grounding worker reports observed mechanics; it never chooses a
provider, model, effort, retry, or write.

## Direct dispatch lifecycle

### Warm cache path

For `next_action=dispatch`, the two Swingle calls before launch are:

```text
dispatch context
ledger begin-direct
compose and run provider Bash
interpret provider result
verify repository when mutating
ledger finish-direct
```

Use the returned context to accept or override candidates. Call `ledger begin-direct`
once with `$REPO_ROOT` and retain its returned artifact directory. Its command shape is:

```bash
python3 $PLUGIN_ROOT/scripts/swingle ledger begin-direct \
  --project $REPO_ROOT \
  --dir <ledger-directory> \
  --controller-session-id <uuid> \
  --role <role> \
  --contract '$PLUGIN_ROOT/contracts/<role>-contract.md' \
  --tier <tier> \
  --task <summary> \
  --dispatch-context-file <path|-> \
  --provider <provider-id> \
  --model <model-id|provider-default> \
  --effort <effort-id|none>
```

After `begin-direct` returns the artifact directory, read the selected provider pack
path from context and read and adapt Dispatch guidance from its `## Dispatch guidance`
section. Confirm that its `Dispatch-guidance fingerprint` matches the usable receipt
and the context result before composing the command. Build Bash from current mechanics,
the adapted guidance, the artifact directory, and the authored inputs. Do not invent
provider syntax or carry mechanics from another provider or an earlier run.

For mutating work, transport the exact authored briefing. Preserve every byte, including
fenced literals, quotes, blank lines, trailing newlines, dollar signs, backticks, and
shell metacharacters. Use the provider's native prompt-file, stdin, supported file
argument, or one complete positional value. If shell quoting cannot preserve it, write a
temporary launch script in the artifact directory. Never summarize, paraphrase, or omit
the briefing. A read-only one-line task may use an inline prompt when no authored
briefing exists.

#### Announce warm attempt 1

Retain `run_id`, `job_id`, and `artifact_dir` from the successful
`ledger begin-direct` JSON result. Set the attempt to the known constant `1`; do not
look for an attempt response field. Use the resolved selection transported to
`ledger begin-direct`. After the complete provider command is composed and immediately
before launch, emit exactly:

```text
delegate: role=<role> contract=<contract> tier=<tier> provider=<provider> model=<model> effort=<effort> attempt=<attempt> run=<run-id> job=<job-id>
artifacts: <artifact-dir> — inspect: cd <quoted-repo-root> && python3 <quoted-plugin-root>/scripts/swingle workspace show --run <run-id> --job <job-id>
```

Launch only after the command is composed. Store stdout, stderr, reports, and event
streams in the returned artifact directory. If output is large, write a temporary
`jq` filter or Python parser there and read its compact output; do not load the raw
stream into controller context. Retain the raw stream as evidence.
The temporary parser remains in the artifact directory and is controller-only support,
not installed product code.

Start supervision only after provider launch. Keep one run and one provider context.
Use the policy from [references/liveness.md](../../references/liveness.md): silence is a
diagnosis threshold, not completion or proof of a stall; terminate only under an explicit
resolved hard timeout. Record liveness warnings and provider sessions as typed ledger
events.

Interpret process exit, stdout, stderr, structured completion, final response, tool
denials, quota errors, and report-file presence together. A provider claim never replaces
independent verification. For mutating work, inspect changed paths, verify requested
contents and invariants, reject out-of-scope changes, and run applicable behavioral
tests. Record `repository_verification` separately from the provider outcome. Only
`VERIFIED` permits a successful mutating completion; `INVALID_RESULT`, `UNCHANGED`, and
`FAILED_TESTS` force `BLOCKED`.

Reconcile provider and repository outcomes, write one completion file containing
`provider_outcome` and `repository_verification`, and call `ledger finish-direct` once:

```bash
python3 $PLUGIN_ROOT/scripts/swingle ledger finish-direct \
  --project $REPO_ROOT \
  --dir <ledger-directory> \
  --controller-session-id <uuid> \
  --run-id <uuid> \
  --job-id <uuid> \
  --status <status> \
  --outcome <outcome> \
  --evidence-file <evidence.json> \
  --completion-file <completion.json> \
  [--provider-session-id <provider-session-id>]
```

## Positive-TTL miss and TTL-zero paths

For `ground_and_record`, ground every returned scope, call:

```bash
python3 $PLUGIN_ROOT/scripts/swingle grounding record \
  --project $REPO_ROOT \
  --provider <provider-id> \
  --payload-file <path|->
```

Follow the returned action. A positive-TTL miss grounds and records, then reruns
`dispatch context`; it does not allocate ledger state before that rerun.
When the user explicitly requests fresh grounding, run `grounding refresh` for the
requested provider and scopes, then rerun `dispatch context`:

```bash
python3 $PLUGIN_ROOT/scripts/swingle grounding refresh \
  --project $REPO_ROOT \
  --provider <provider-id> \
  [--scope <scope>] \
  --reason user-request
```


For `ground_without_cache`, do not read or write the cache. Keep the normalized
grounding result and the returned `ledger_event` in controller context across
`refresh_context`. Pass that exact event as `grounding-observed` when the cache was
written (preserving its Python-generated receipt ID and revision), or with
`storage: none` and null receipt fields when cache is bypassed; only the latter
sentinel receives a fresh receipt UUID in `begin-direct`.

If live grounding cannot resolve the executable, do not cache negative availability and
do not allocate a ledger job. For a configured provider, offer `repair=provider-routing`.
For an explicit missing provider, return `BLOCKED` without substitution.

### Announce TTL-zero attempt 1

For `ground_without_cache`, retain the normalized uncached grounding event with
`storage: none` and null receipt fields. Run the low-level uncached
`ledger begin-direct`. After it succeeds, retain `run_id`, `job_id`, and
`artifact_dir` from its JSON result and set the attempt to the known constant `1`.
Use the resolved selection transported to that call, then compose the complete provider Bash command from the uncached mechanics and authored inputs. After the
complete command is composed and immediately before launch, emit exactly:

```text
delegate: role=<role> contract=<contract> tier=<tier> provider=<provider> model=<model> effort=<effort> attempt=<attempt> run=<run-id> job=<job-id>
artifacts: <artifact-dir> — inspect: cd <quoted-repo-root> && python3 <quoted-plugin-root>/scripts/swingle workspace show --run <run-id> --job <job-id>
```

Then launch provider Bash.

The block does not add cache I/O or a second ledger call.

## Failure recovery

After an observed failure, use this exact order:

1. Record `attempt-failed`.
2. Invalidate executable or contradicted command mechanics only.
3. Preserve mechanics after permission, quota, credit, or entitlement failures.
4. When invalidation occurs, record its reason and time.
5. After a mechanics contradiction, inspect current help and the matching Gotcha in the
   selected provider pack.
6. Rerun `dispatch context` after invalidation.
7. Let the controller choose retry, resume, policy change, worktree reset, or stop.

### Announce a same-job retry

This block applies to retries from the warm `begin-direct`, TTL-zero, and batch paths.
For the same job, choose N as the prior dispatched attempt plus one. First record
`ledger record attempt-failed --attempt N-1`; after any required invalidation, rerun
`dispatch context`; then record `ledger record dispatched --attempt N` with the full
provider, model, effort, liveness, and grounding fields for the new launch. Use the
exact integer passed to that dispatched record; never infer or recompute it in the
announcement. Preserve the same run_id, job_id, and artifact_dir from attempt 1.

Neither append-time validation nor `ledger validate` enforces this ordering; a ledger
that violates it may still pass `ledger validate`. The controller must append
`attempt-failed(N-1)` before `dispatched(N)`. After the dispatched record succeeds,
compose the complete provider command for attempt N from the refreshed context and
current provider mechanics. After the command is composed and immediately before
launch, emit exactly:

```text
delegate: role=<role> contract=<contract> tier=<tier> provider=<provider> model=<model> effort=<effort> attempt=<attempt> run=<run-id> job=<job-id>
artifacts: <artifact-dir> — inspect: cd <quoted-repo-root> && python3 <quoted-plugin-root>/scripts/swingle workspace show --run <run-id> --job <job-id>
```

Then launch attempt N.

After `INVALID_RESULT`, `UNCHANGED`, or `FAILED_TESTS`, record repository evidence before
recovery. A provider claim, changed-files field, or exit code never replaces independent
verification. Capture, interpret, and verify each mutating job independently.

## Homogeneous batches and finalization

Use one run and one provider context for a homogeneous batch. Start one run, allocate
each job only after dispatchable context, and record each dispatch with typed ledger
events. After a contradiction, rerun context before later jobs. Every mutating job gets
independent repository verification; one job's evidence never proves another job.

### Announce each batch attempt

Use one block per job per attempt, never one block for the shared run. After
`ledger allocate` succeeds, retain its `job_id` and `artifact_dir` returned by
`ledger allocate`, alongside the shared run_id. Call
`ledger record dispatched --attempt 1` with the provider, model, effort, liveness,
and grounding values for that job. Use the resolved selection transported to
`ledger record dispatched`, then compose the complete provider command for that job.
After the complete command is composed and immediately before launch, emit exactly:

```text
delegate: role=<role> contract=<contract> tier=<tier> provider=<provider> model=<model> effort=<effort> attempt=<attempt> run=<run-id> job=<job-id>
artifacts: <artifact-dir> — inspect: cd <quoted-repo-root> && python3 <quoted-plugin-root>/scripts/swingle workspace show --run <run-id> --job <job-id>
```

Then launch that job. Repeat the sequence independently for every allocated job.

### Finalize the batch

Retain every job's terminal status. The controller must wait or join concurrent jobs,
then terminalize every remaining allocated job with one valid `complete` event if it is
stopping. Do not finalize while an allocated job is active. After every allocated job
has exactly one terminal `complete` and no further jobs will be allocated, invoke the
sole finalizer:

```bash
python3 $PLUGIN_ROOT/scripts/swingle ledger finalize-run \
  --project $REPO_ROOT \
  --dir <ledger-directory> \
  --controller-session-id <uuid> \
  --run-id <uuid>
```

`ledger finalize-run` calls `finalize_run` under the session lock. It rejects a missing
or duplicate `run-started`, any nonterminal allocation, and an existing `run-completed`.
It does not wait, terminalize, choose outcomes, or accept caller status. It derives status
with:

```text
BLOCKED > NEEDS_CONTEXT > DONE_WITH_CONCERNS > DONE
```

and emits exactly:

```text
jobs=N done=N done_with_concerns=N needs_context=N blocked=N
```

The finalizer appends exactly one typed `run-completed`, never one per job. Do not record
that event directly. A stopping path must terminalize all remaining jobs first, then
invoke the same sole finalizer.

## Status and reports

Use `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`. Preserve provider and
repository evidence, artifact paths, liveness observations, and concerns in the selected
report mode. Completion requires the applicable repository verification; provider
self-report alone is never enough.

## Reporting the workspace output

Every terminal job's manifest is automatic; no extra step produces it. For direct work:

1. Keep all useful provider inputs, outputs, and evidence in the allocated job directory.
2. Call `ledger finish-direct --project $REPO_ROOT` after result interpretation and
   repository verification.
3. Report the request-named output path as the deliverable when one exists.
4. When no request-named output exists, report the primary output path — the job's
   main workspace output — as the deliverable.
5. Report the job directory in both cases.
6. Run `workspace copy` only when the original request names the exact destination and selection;
   a proactive copy is never the default.

A full-job copy publishes `manifest.json`; copying a narrowed file selection publishes
`source-manifest.json` instead, so the destination never claims to be the complete job.

Deletion uses one preview, one confirmation, and the exact preview digest:

```bash
python3 $PLUGIN_ROOT/scripts/swingle workspace delete --run <run-id> [--job <job-id>] --json
python3 $PLUGIN_ROOT/scripts/swingle workspace delete --run <run-id> [--job <job-id>] \
  --expect-selection-sha256 <digest> --apply --json
```

`workspace delete` never touches a ledger file: it deletes only the artifact tree the
preview named.
