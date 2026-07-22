# Mapping superpowers:subagent-driven-development onto Provider Packs

> How the SDD skill actually operates, and the token-efficient way to run its subagent roles
> through provider packs instead of the harness's native subagent mechanism (see harness adapter).
> Companion to [core/roles.md](roles.md) and the active pack's models.md.
> Skill source: superpowers 6.1.1 `skills/subagent-driven-development/`.

## How the skill operates (compressed)

Controller loop, per task from a written plan:

1. `scripts/task-brief PLAN N` → extracts the task text to `.superpowers/sdd/task-N-brief.md`
   (bulk never enters controller context).
2. Record BASE (= current HEAD). Dispatch **implementer** with: brief path, one line of
   scene-setting, interfaces from prior tasks, report-file path, and the report contract
   (status ≤15 lines back; detail in `task-N-report.md`). Status ∈ DONE /
   DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED.
3. `scripts/review-package BASE HEAD` → commit list + stat + `-U10` diff in one file.
   Dispatch **task reviewer** (read-only) with brief + report + diff paths + verbatim
   global constraints. Two verdicts: spec compliance, code quality.
4. Critical/Important findings → **fix** dispatch (same report file, appends) → re-review.
   Minor findings → ledger, triaged by the final review.
5. Append to the progress ledger (`.superpowers/sdd/progress.md`) — the compaction-proof
   recovery map. Never re-dispatch a ledgered task.
6. After all tasks: **final whole-branch review** on `review-package MERGE_BASE HEAD`,
   most-capable tier; one consolidated fix dispatch if findings.

Controller-only judgment (never offloaded): pre-flight plan conflict scan, status
adjudication, ⚠️ cannot-verify-from-diff resolution, plan-contradiction escalation to the
human, ledger, and the hard gate (re-run test gates, inspect diffs).

**The key structural fact:** the skill is already file-centric — briefs, reports, and diffs
move as paths, not pasted text. That is exactly the shape a provider-pack dispatch needs, so
the mapping is natural; the wins below come from pushing the last pasted things (the prompt
templates, the dispatch stdout) out of controller context too.

## Role → dispatch mapping

| SDD role | Lane | Dispatch shape |
| --- | --- | --- |
| Implementer | `implement` | background, per-task log, brief+report paths, contract file |
| Task reviewer | `review` | background, brief+report+diff paths, constraints block, contract file |
| Fix subagent | same lane as implementer | resume the implementer session where possible |
| Final whole-branch review | `review`, most-capable tier | `review-package MERGE_BASE HEAD` path + Minor-findings ledger list |
| Pre-flight scan, adjudication, ledger, gates | **controller — never dispatched** | n/a |

Role tiers and lanes are in [core/roles.md](roles.md). Resolve the selected tier against the
active pack's models.md; apply [core/liveness.md](liveness.md).

## Dispatch flavours & economics — say which one you mean

“Dispatch” is ambiguous. Four execution modes, three currencies. The currencies, in order
of scarcity: **main-thread context** (multiplicative — resident tokens are re-sent every
turn and degrade the controller's judgment as they accumulate), **harness token budget**
(our spend; disposable subagent contexts are one-shot), **provider cost** (largely fixed by
the task, with cold-start overhead per execution).

| Mode | Main-ctx / task | Harness tokens | Provider cost | When |
| --- | --- | --- | --- | --- |
| **Inline** (controller does it) | 15–40k+, grows with task size | full task, premium | 0 | below the orchestration floor (~2k of work, single-file mechanical), or judgment-core work |
| **Sub-dispatch** (native subagent) | 1–3k (prompt + report) | full task, isolated context | 0 | judgment-heavy isolated work; the `native-subagents` lever |
| **Pack dispatch** | ~2k + **6–8 controller turns** | orchestration only | task cost | the SDD default for typical plans (≤ ~6–8 tasks) |
| **Supervised pack dispatch** (cheap native subagent runs the pack cycle) | ~0.5k — one consolidated report | supervisor turns | task cost | long plans where the controller's orchestration turns are the binding cost |

Rules that fall out:

- **The main game is conserving main-thread context.** Provider tokens are linear,
  one-shot, cheap; controller-resident tokens are re-billed every turn for the rest of the
  session and — worse — crowd the adjudicator's attention. Flat ~2k/task context is what
  lets a 20-task plan finish without compaction (whose observed failure mode is
  re-dispatching completed work).
- **The triviality floor**: if the controller could complete the task in fewer tokens than
  the orchestration cycle costs (~2k + 6–8 turns), do it inline. Batch several trivial tasks
  into one pack dispatch rather than paying the cold start per task.
- **Supervised pack dispatch** moves the orchestration turns (launch, liveness, mechanical
  gate, reviewer dispatch, verdict collection) into a disposable cheap-subagent context
  that returns one report with evidence *paths*. Non-negotiable: **adjudication and commits
  stay in the main thread** — the supervisor's “all green” is evidence to check, not a gate
  result; the controller still reads verdicts, spot-checks the stat, and commits.
- Fixed cost per provider execution is real but paid in the cheap currency; never let it
  push a large task inline — task *size* is exactly what the flat-context property protects.

## Token-efficiency playbook

The controller's context is the scarce resource; provider-agent tokens are cheap. Every rule
below moves bytes from controller context to files or to the dispatched agent.

**E1 — Contracts are files, written once per session, not pasted per dispatch.** Copy the
adapted contracts into the SDD workspace once, then every dispatch prompt is a short path
reference: *“Read <workspace>/implementer-contract.md — your operating contract. Read
<brief> — your requirements. Scene: <one line>. Interfaces from prior tasks: <lines or
'none'>. Report to <report-file>. Begin.”* The contract text never transits the controller
again.

**E2 — Dispatch stdout never enters controller context.** Always background and redirect to
the per-task log. The controller reads back only the ≤15-line status block, the report when
adjudication needs it, and `git diff --stat`. Never read a full log or diff into context —
the reviewer reads the diff file; the controller reads verdicts.

**E3 — Questions and fixes ride the resume channel, not fresh dispatches.** The agent exits
with NEEDS_CONTEXT and its questions in the status block; the controller answers through the
active pack's continuation mechanism. The agent keeps its loaded context — the brief and
codebase exploration — so nobody re-pays for it. The same applies to the fix loop: resume
the implementer's session with the findings list instead of cold-starting a fixer.
Re-reviews ride the same channel on the reviewer side: resume the original reviewer's
session with the fix summary and updated package (default), so the reviewer verifies its
own findings rather than re-deriving the review; cold re-dispatch (prior review attached
verbatim) is the fallback when the continuation channel fails. Record both session ids in
the ledger so post-compaction recovery can resume either thread.

**E4 — Implementers do not commit; the controller commits.** The doctrine requires
controller commits. Controller sequence per task: record BASE → dispatch → gate (tests
re-run, stat read) → commit → `review-package BASE HEAD` → reviewer.

**E5 — Reviewers use an enforced read-only lane when available.** Otherwise clean-tree +
diff-after is the only protection — check status before accepting the verdict.

**E6 — Gate depth scales with risk (controller's own token spend).** Always read the status
block + `git diff --stat` + both reviewer verdicts; read the full review package only when
the reviewer reports findings, flags ⚠️ items, the task touches a critical path, or the stat
disagrees with the report. The reviewer always reads the full package; the controller reads
it on demand.

**E7 — Ledger discipline unchanged, plus session ids.** The ledger line gains the dispatch
session id: `Task N: complete (commits <base7>..<head7>, review clean, session <id>)` — so
post-compaction recovery can still resume a half-finished agent instead of restarting it.

### What a task costs the controller under this playbook

~10-line dispatch × 2–3, one status block × 2–3, one stat, two verdicts, one ledger line —
**≈ 1–2k controller tokens per task**, roughly independent of task size. The pasted-template,
foreground-stdout alternative runs 15–40k per task and grows with task size. The offload
target — controller as thin adjudicator, provider agents as the working mass — is met.

## Divergences from the stock skill (deliberate)

| Stock skill | Provider-pack adaptation | Why |
| --- | --- | --- |
| Implementer commits its own work | Controller commits after gating | Controller-commits doctrine |
| Fix subagent = fresh dispatch | Resume implementer's session | context already paid for; the efficient fix path |
| Templates pasted per dispatch | Contract files in workspace, referenced by path | E1 — the single largest controller saving |
| Subagent questions answered inline | NEEDS_CONTEXT status → resume with answers | continuation keeps agent context |
| “Controller reads every diff” | Stat + verdicts always; full diff on findings/risk/contest | E6 — gate power at a fraction of the spend |

Everything else — pre-flight scan, two-verdict reviews, fix→re-review loops, ⚠️ handling,
ledger, never-parallel implementers, final most-capable review, plan contradictions go to
the human — carries over unchanged.
