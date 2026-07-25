---
name: swingle-delegate
description: Directly delegate an explicitly requested, self-contained job or homogeneous batch to an external CLI (codex/opencode/agy/grok/pi/claude) through validated provider packs — role inference, model tiering, liveness, evidence gates, and session resume — without a written implementation plan. Use the swingle-sdd skill for multi-task implementation plans; keep sub-triviality-floor tasks inline unless delegation was explicitly requested.
---

# Delegate — Direct One-Off Dispatch

**Harness**: identify your controlling harness and read
`<root>/skills/sdd/harnesses/<harness>.md` (claude-code, codex, grok, opencode, pi, agy) before setup — it
maps skill-loading, native subagent dispatch, background jobs, completion observation,
and asset-root resolution. `<root>` is this skill directory's grandparent (the directory
containing `skills/`, `core/`, `providers/`, `contracts/`).

**Never dispatch from memory.** Before the first dispatch of a session, read
`<root>/core/roles.md`, `<root>/core/playbook.md`, `<root>/core/safety-doctrine.md`,
`<root>/core/liveness.md`, and the active `<root>/providers/<id>/pack.md`. Recalled
doctrine is a paraphrase of whatever was true when it was learned, and these documents
change under you — packs are re-verified on every CLI version bump, and tiering, roles,
and dispatch templates move with them. A dispatch built from memory looks identical to a
correct one and fails silently: a stale flag, a superseded model id, a tier that no longer
matches the role. Read the files; they are short by design.

**Boundary (semantic, not transport-based)**: `swingle-sdd` = dependency-aware execution
of a multi-task implementation plan (task reviews, plan ledger, final review) — use it
whenever the work is a plan, whether it arrived as a file, a pasted numbered checklist,
or a structured message. `swingle-delegate` = an **explicitly requested**, self-contained job or
homogeneous batch, wherever its text originated. The playbook's triviality floor still
applies: work the controller can finish inline for less than the orchestration cycle
stays inline unless the caller explicitly asked for external delegation. This skill has
**no superpowers dependency**: it never invokes superpowers skills, never runs
`scripts/sdd-workspace`, and never reads or writes `.superpowers/sdd/`.

**v1 scope: git repositories.** In a non-repo working directory accept only read-only
research/synthesis: artifacts go to a fresh
`mktemp -d "${TMPDIR:-/tmp}/sdd-delegate.XXXXXX"` directory, no durable ledger exists,
and no resume promise is made — say so in the reply. Refuse write-lane work outside a
git repository. Report the directory's path with the answer and leave it in place for
the session (the report is the deliverable and the user may want it); never delete it
before returning the answer, and never treat OS temp pruning as a guarantee it will
persist.

Read these plugin documents when their policy is needed:

- `<root>/core/roles.md` — the role → tier → lane table (the classification authority)
- `<root>/core/playbook.md` — dispatch flavours, economics, and controller gates
- `<root>/core/liveness.md` — required background and stall protocol
- `<root>/core/safety-doctrine.md` — containment and controller-gate doctrine
- `<root>/providers/<id>/pack.md`, `models.yaml`, and `models.md` — validated provider behavior,
  canonical dispatch, session source, report transport, recovery rules, and
  model candidates (models.yaml is the table of record; models.md is narrative)

## Levers (parsed from anywhere in the request)

- **Provider**: "via agy" / "via codex" / "via opencode".
- **Tier**: "floor it" (default when silent) = cheapest model clearing the role's bar;
  "play it safe" = one tier up (at most-capable that is already the ceiling — say so
  and proceed); an explicit model id must appear in the resolved role's eligible
  resolution sequence (the tier/lane candidate walk in the provider's resolved models.yaml) —
  otherwise ask, never silently accept or substitute.
- **Review**: "with review" — write lane: one reviewer dispatch before commit (see
  Gate). Read lane: a second independent reader WITHIN the resolved provider (next
  eligible candidate in the resolution walk when one exists, else a fresh session of
  the same model; a provider change is a user decision, never silent); the controller
  compares reports.
- **Lane pin**: "read-only" — forces the read lane. If the task text simultaneously
  demands writes ("fix this, read-only"), ask which governs — never silently convert
  requested write work into analysis.
- **Supervision**: "supervised" / "unsupervised" — overrides the automatic trigger.
- **Native**: the `native-subagents` lever ("all Claude" under Claude Code) bypasses
  external dispatch per the harness adapter; provider routing, model resolution, and
  supervision do not apply. Explicitly requested but unavailable → stop and ask;
  auto-selected (supervision) but unavailable → controller orchestrates, announced.

## Setup (once per session) — Step-0-lite

1. **Trust gate**: run `python3 <root>/scripts/validate-packs --root <root>` — refuse to
   proceed past a non-zero exit. THEN check `git -C <root> status --porcelain
   providers/` — any untracked or modified provider directory requires explicit user
   approval before its manifest or prose is used.
2. **Detect providers**: read each `<root>/providers/*/pack.md` manifest; a provider is
   INSTALLED iff `command -v -- "<cli>"` succeeds for its validated cli name (data-only
   manifests — never execute manifest strings as shell).
3. **Layered config** (first found): `$SDD_DISPATCH_CONFIG` →
   `<project>/.sdd-dispatch.json` →
   `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/config.json` — disable/steer only; the
   same malformed-config STOP conditions as the `swingle-sdd` skill. ACTIVE = installed −
   disabled (− incompatible iff require-verified-version).
4. **Compatibility (advisory)**: compare `version-argv` output to `verified-version`. A
   mismatch is a WARNING, not a gate — warn (installed X vs verified Y) and PROCEED.
   Re-verifying a bumped CLI is maintenance (`swingle-verify <id>`), never a per-dispatch
   stop; block only under config `require-verified-version`. Note that **drift is in
   effect** for the session: if a later dispatch fails with a channel-class signature
   (Failure handling), that failure IS a verification finding — recommend recording it
   per the existing recording ladder and dedup (`core/verification-protocol.md`
   Recording), capturing plugin + CLI versions. Never file automatically; never block the
   user pre-dispatch on drift alone.
5. **Routing**: per-request provider directive → session lever → config
   `providers_by_lane[lane-of-role]` / `default_provider` → codex-if-active else
   sole-active-iff-exactly-one → ask. Inactive provider named anywhere → ask, never
   silently reroute.
6. **Model resolution**: role → (tier, lane) via `core/roles.md` → the provider's
   layered models.yaml (first found wins whole-file: `$SDD_DISPATCH_MODELS/<id>.yaml` →
   `<project>/.sdd-dispatch/models/<id>.yaml` →
   `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` → the pack's
   `models.yaml`) → ordered candidates (statuses verified/experimental; exact-lane rows
   by priority, then (tier, any) rows by priority); take the first; none → ask, naming
   the winning file. A found-but-malformed override, or set-but-unreadable
   `$SDD_DISPATCH_MODELS`, is a STOP, never a fall-through.
   (`scripts/validate-packs --resolve "<role>" <id> --project <repo>` prints the layer
   and walk; `scripts/sdd-models which|init` inspects and seeds override layers.)
7. **Readiness**: before the FIRST dispatch to a chosen provider, run its bounded
   preflight per its pack (version + auth/session probe; agy: the headless permission
   baseline check — on miss, STOP and hand the user the pack's baseline section).
8. **Workspace**: create `.sdd-dispatch/delegate/` at the repo root. Check
   `git check-ignore -q .sdd-dispatch/delegate/.probe` (a child sentinel, so negation
   rules cannot silently expose workspace files); if not ignored, append
   `.sdd-dispatch/delegate/` to the file resolved by `git rev-parse --git-path info/exclude`
   (repo-local, never tracked; a literal `.git/info/exclude` path breaks in linked
   worktrees) and tell the user — NEVER edit a tracked `.gitignore` implicitly (it
   dirties the tree right before a gate that requires it clean; a tracked entry is the
   user's separate commit). `.sdd-dispatch/models/` is committable project config —
   never ignore `.sdd-dispatch/` at the root. Copy
   `implementer-contract.md`, `task-reviewer-contract.md`, `design-reviewer-contract.md`,
   and `reader-contract.md` from `<root>/contracts/` into the workspace once per session.

## Role inference and the announcement line

Classify the task against the **full seven-row table in `core/roles.md`** —
transcription implementer, adaptation implementer, large-codebase / long-context
implementer, read-only explore, external research/synthesis, per-task reviewer,
final/design reviewer. The table is the authority — never work from a shortened
paraphrase (that under-tiers design reviews and long-context work).

**Review of an unimplemented artifact routes to the design-reviewer contract.** When the
target is a spec, design document, or implementation plan rather than a diff — a
`specs/*-design.md`, a `plans/*.md`, or any artifact the caller describes as not yet
built — dispatch it as the final/design reviewer row with
`design-reviewer-contract.md`, never the task-reviewer contract. The path shape is a
prompt to check, not the test: the test is whether the subject exists in code yet. Ask
when it is genuinely ambiguous. Sending an unimplemented design to the task reviewer
produces a review that reports the design's own absence as findings — the artifact is
judged on whether it would work if built, not on whether it has been.

Then announce, in ONE line before dispatching:

```
delegate: job=NNN role=<roles.md row> tier=<tier> lane=<lane> provider=<id> model=<model> supervised=<yes: N cycles|no>[ review=yes]
```

Native routing announces
`delegate: job=NNN role=<role> tier=<tier> lane=<lane> route=native supervised=no`
instead (no provider/model fields).

The announcement is the caller's override point. When a task genuinely straddles lanes
("look into X and fix it"), ask ONE question (investigate-only vs investigate-and-fix)
before dispatching — never guess a write when a read was plausible.

**Contract by role class**: implement roles → implementer contract; explore /
research / synthesis → reader contract; a primary review job ("review this diff/PR/
document") → task-reviewer contract, with the controller generating the inputs that
contract expects: the artifact under review as a package file (for a diff: commit list
+ stat + `-U10`) plus whatever requirements text the caller supplied in place of a
brief. For whole-artifact scopes (a design doc, a whole branch) the dispatch prompt
overrides the contract's task-scoped framing explicitly — state the actual scope; the
contract's method and calibration rules still apply.

**Output capture is role-, lane-, AND pack-specific — never demand a file write the
lane forbids or the provider cannot reliably perform**: review-role dispatches use the
reviewer contract's own output protocol (final message IS the verdict report), not the
four-status block. Two independent conditions switch a report-producing role from the
report-file protocol to **captured output** — the FULL report/answer is the captured
final message, saved by the controller (or the pack's host-side output mechanism) to
the workspace path, on initial AND resumed turns:

1. **The lane forbids writing** — an enforced read-only lane; the agent simply cannot
   write `NNN-report.md`.
2. **The pack declares `report-transport: captured-output`** — the provider cannot
   reliably write an agent-authored file to a workspace path at all. This is a pack
   fact, not a per-task judgement: read it from the routed pack's manifest.

Either condition alone is sufficient. The reader contract carries the switch, so no
prompt surgery is needed — state which protocol applies and the contract does the rest.
A pack whose manifest says `report-transport: report-file` (or omits the field —
`report-file` is the default) keeps the report-file + short-status protocol on
unsandboxed read-intent lanes.

Why this is a manifest field rather than a workaround in the prompt: a provider whose
file-writing tool refuses workspace paths will fail *intermittently*, producing a
missing report on some fraction of dispatches while the exit code stays 0. Prompt-level
steering can only lower that rate; routing the report through captured output removes
the failure mode. Record the transport where the provider's other verified facts live.

**Batching**: a homogeneous batch (near-identical mechanical items) is ONE job = one
dispatch. Heterogeneous tasks are separate jobs, run sequentially. Never parallel
write-lane dispatches. Parallel read-lane dispatches ONLY when all hold: the routed
provider has an ENFORCED read-only lane (read-only is intent, not enforcement, on
unsandboxed packs — concurrent "readers" there can both write and conflict), output
paths are distinct, and the pack's `session-source` attributes sessions
deterministically under concurrency (a newest-first session list races — serialize
those providers).

## Dispatch cycle

Each **job** gets the next number `NNN` (001, 002, …), allocated durably in the ledger
BEFORE launch — a crash or compaction never loses the number→task mapping.

1. Write the prompt to `.sdd-dispatch/delegate/NNN-prompt.md`: contract path (per role
   class), the task text verbatim, scene (one line: repo, branch, relevant paths), and
   the role's output protocol — branch by role, lane, AND the routed pack's
   `report-transport` per the output-capture rules: implement and unsandboxed read roles
   on a `report-transport: report-file` pack → report-file path (`NNN-report.md`) + the
   four-status block (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) as the
   final message; review roles → the reviewer verdict protocol (controller saves it
   to `NNN-review.md`); enforced read-only lanes **or** a `report-transport:
   captured-output` pack → full report as captured final output (controller saves to
   `NNN-report.md`), on initial AND resumed turns. Whatever the transport, state the
   status vocabulary **inline in the prompt** — the contract path carries each token's
   semantics, the prompt carries the tokens (playbook E1a): “End with a status block whose
   first line is exactly one of: STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT |
   BLOCKED.” Cheapest-tier conformance was 3/3 with the line inline and 0/3 by contract
   reference alone; a missing block is still UNKNOWN, never DONE.
2. EVERY repository dispatch, both lanes: the tree must be CLEAN — `git status
   --porcelain=v1 --untracked-files=all` empty, no exceptions on any pack (pre-existing
   dirt is indistinguishable from agent mutation). Record BASE (= HEAD) and the current
   branch for both lanes.
3. Dispatch with the active pack's canonical template inside the self-reaping wrapper
   (`core/liveness.md`), stdout to `NNN-dispatch.log`. Observe completion via the
   harness adapter's declared mechanism (background-task notification, polling, or the
   detached marker-file form — whichever the adapter specifies for the mode in use);
   never foreground stdout. Session capture is asynchronous and provider-specific:
   obtain the session id per the pack's `session-source` and append it to the ledger
   the moment it is observed.
4. **Evidence gate** (exit codes are never evidence of work):
   - Write lane: HEAD must be UNCHANGED (an agent-created commit is a doctrine
     violation to surface, not absorb); then `git status --porcelain=v1
     --untracked-files=all` + `git diff HEAD --stat` — together covering unstaged,
     staged, AND untracked changes. Agent-created untracked files are part of the
     change: list them; include their content in any review package.
   - Read lane: HEAD must be UNCHANGED (an unsandboxed "reader" can commit and leave
     a clean tree) and porcelain must be EMPTY (any mutation is a violation to
     surface, not silently reset); the report (file or captured output, per the lane's
     output-capture rule) must exist, postdate the dispatch, and answer the task.
5. **NEEDS_CONTEXT, follow-ups, and fixes ride the resume channel** — the pack's
   validated continuation mechanism against the recorded session id. Cold re-dispatch
   only when the resume channel fails, with the prior report attached.
6. **Failure handling — classify by scope; apply the pack's own recovery FIRST**:
   - Provider-wide (auth, misconfiguration, missing permission baseline) → STOP; fix
     the environment or ask. Never advance the model candidate.
   - Candidate-specific rejection (model-not-found, model-level 4xx) → next candidate
     in the resolution order (same provider, max 3 attempts per job); cross-provider
     moves are always a user question.
   - Transient transport/startup → the pack's documented recovery first (e.g. a
     retry-once rule); only then treat as candidate-specific.
   - Stall/kill with partial progress → RESUME the session (a kill is a checkpoint,
     not a restart); check `git diff HEAD` for landed work before resuming.
   - Task/context blocker (BLOCKED, NEEDS_CONTEXT) → controller adjudication; nothing
     automatic.
   - Quality failure → stops ALL automatic recovery; any tier escalation requires
     user approval (tier moves are never the controller's unilateral call).
   - **Channel-class failure while version drift is in effect** (setup warned installed ≠
     `verified-version`): after applying the pack's recovery, treat the failure as a
     verification finding — the pack is a candidate for being stale on this CLI version.
     **Recommend** (do not auto-file) recording it via the existing recording ladder and
     dedup in `core/verification-protocol.md` Recording: search existing `verification`
     issues first, then 👍 / comment / new-issue as the evidence warrants. The finding
     captures plugin version, installed CLI version vs `verified-version`, the controlling
     harness + its version, and the failure signature. Maintenance signal, not a user
     block; quality failures are excluded (they are not drift evidence).
   - Every attempt appends:
     `model-attempt: job=NNN phase=<worker|review|reader2> attempt=<n> role=<role> provider=<id> model=<id> class=<scope> outcome=<failed|ok>`.

## Gate, results, and opt-in review

**Controller hard gate — always, both lanes** (on-disk checks per the cycle above):

- Write lane, no review requested: the controller inspects the ACTUAL diff
  (`git diff HEAD` plus untracked-file content), not just the stat — unreviewed change
  contents must pass controller eyes before tests/commit. With review requested, the
  reviewer reads the full package and the controller may gate on stat + verdicts.
- Write lane: the controller re-runs the covering tests named in the task (or the
  project's default gate) itself, never trusting the agent's claimed results.
- **The controller commits** — and only when the user asked for a commit; otherwise
  leave the working tree for the user with a `git diff --stat` summary. External
  agents never commit.
- **Read lane — the report IS the deliverable**: the controller reads the report,
  checks freshness (postdates the dispatch) and that it actually answers the task,
  then returns the substantive answer (or a faithful summary plus the report path) to
  the user. Report-exists is the floor, not the gate.

**Opt-in review ("with review", write lane)**: one reviewer dispatch before any
commit — review role, standard tier (scaled up for large/risky diffs), review lane,
task-reviewer contract, given the task text, the report, and a review package
(BASE→current: commit list + stat + `-U10` diff of tracked changes + full content of
agent-created untracked files) written to `NNN-review-package.md`; reviewer output to
`NNN-review.md`. **Pre-commit review containment — always artifact-only**: the target
tree holds uncommitted worker changes, so pre-commit reviewers run in an artifact-only
scratch directory containing just the review package and task text, on EVERY provider
(the package is self-contained by construction). Concretely: the controller COPIES
`NNN-review-package.md` and `NNN-prompt.md` (plus the reviewer contract) into that
scratch directory and scopes the dispatch to it — it never passes workspace paths that
would pull the reviewer back into the repository. A pre-commit reviewer never enters
the target repository — the clean-tree rule stays exception-free and a reviewer
mutation can never masquerade as worker work. Critical/Important findings ride the implementer's resume channel;
the re-review resumes the ORIGINAL reviewer's thread with the fix summary and a fresh
versioned package (`NNN-review-package-2.md`). One fix/re-review round by default.

**"with review" on a read-lane job**: a second independent reader (same contract and
inputs, fresh session) per the lever's routing rule — within the resolved provider,
next eligible candidate else same model; report to `NNN-reader2-report.md`, ledger
events `NNN reader2-dispatched:` / `NNN reader2-session:`. The controller compares the
two reports and reconciles disagreements before answering.

## Supervised delegate (auto by cost, announced)

One cheap harness-native subagent (per the harness adapter) runs the mechanical cycle —
prompt files, pack dispatch inside the liveness wrapper, completion watching, the
mechanical gate reads (status block, porcelain/diff checks, report existence), reviewer
dispatch when "with review", verdict collection — and returns ONE concise report with
evidence paths plus the ledger lines it appended.

**Trigger — computed AFTER batching:**

```
cycles = (planned initial worker dispatches) + (planned initial reviewer dispatches)
```

A homogeneous batch is one job = 1 cycle (2 "with review"). Retries, resumes, fix
rounds, and re-reviews are NOT counted — they are unplanned. cycles ≤ 2 → controller
orchestrates directly. cycles ≥ 3 → supervised, announced in the pre-dispatch line. An
explicit "supervised" / "unsupervised" lever always overrides. Native subagents
unavailable → controller orchestrates, announced.

**Doctrine (non-negotiable)**: adjudication and commits stay in the main thread. The
supervisor's "all green" is evidence to check — the controller re-reads the verdict
lines, spot-checks the porcelain/diff evidence against the report, re-runs covering
tests for write-lane work, and performs any commit itself. The supervisor appends
ledger and `model-attempt:` lines as it goes (job numbers allocated before launch), so
a killed supervisor loses no state.

**Ledger writes are append-only — say it explicitly, then verify it.** A supervisor told
merely to "append" has been observed recreating `ledger.md` with its own header,
destroying the controller's pre-launch `NNN allocated:` lines — the exact state the
pre-allocation exists to protect (2026-07-23). The supervisor's brief must say: append
with `>>` only; never create, truncate, reorder, or rewrite the ledger; never remove a
line you did not write. And because a brief is not enforcement, **the controller re-reads
the ledger when the supervisor returns and confirms its own pre-launch lines survived** —
if they did not, the ledger is reconstructed from the controller's job allocation before
anything is committed.

**Escalation**: NEEDS_CONTEXT, BLOCKED, quality failures, and lane-straddle ambiguity
are returned in the supervisor's report, never resolved by it. The controller answers
NEEDS_CONTEXT through the pack's resume channel directly (session id is in the ledger)
or hands the answer to a fresh supervisor cycle for the remaining batch.

## Workspace and ledger

```
.sdd-dispatch/delegate/
  implementer-contract.md      # copied once per session from <root>/contracts/
  task-reviewer-contract.md
  reader-contract.md
  ledger.md                    # append-only lifecycle events (below)
  NNN-prompt.md
  NNN-dispatch.log
  NNN-report.md
  NNN-review-package.md        # only when "with review" (write lane)
  NNN-review.md                # only when "with review"
  NNN-review-package-2.md      # re-review rounds: versioned, never overwritten
  NNN-reader2-report.md        # only when "with review" (read lane)
```

**Append semantics under retries**: `NNN-dispatch.log` and `NNN-report.md` are
append-only across attempts — each retry/resume first appends an attempt boundary
header (`=== attempt <n>: <provider>/<model> ===`), then its output, so the
channel-failure evidence that justified a fallback is never overwritten.

**Ledger = append-only lifecycle events**, one line each, written the moment each event
happens (never only at completion):

```
NNN allocated: role=<role> task="<summary, ≤10 words>" prompt=NNN-prompt.md
NNN dispatched: provider=<id> model=<id> attempt=<n>
NNN session: attempt=<n> <session-id>          # appended when observed (async);
                                               # attempt= disambiguates late arrivals
NNN review-dispatched: provider=<id> model=<id> round=<n> attempt=<n>
NNN review-session: round=<n> attempt=<n> <session-id>   # reviewer's own resume thread
NNN reader2-dispatched: provider=<id> model=<id> attempt=<n>
NNN reader2-session: attempt=<n> <session-id>
NNN resumed: target=<worker|review> session=<id> reason=<needs-context|fix|follow-up>
NNN complete: status=<DONE|...> outcome=<committed <sha7>|diff-left|answer-returned|blocked>
model-attempt: job=NNN phase=<worker|review|reader2> attempt=<n> role=<role> provider=<id> model=<id> class=<scope> outcome=<failed|ok>
```

Worker and reviewer session ids are BOTH recorded — fix rounds resume the worker's
thread, re-reviews resume the reviewer's. The `task=` summary plus the prompt path make
"ask that agent a follow-up" unambiguous after compaction or across a batch. Native
routing records `NNN dispatched: route=native` and, where the harness provides one,
`NNN native-ref: <harness ref>`. Never re-dispatch work the ledger records as complete.
