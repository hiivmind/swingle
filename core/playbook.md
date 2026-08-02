# Mapping superpowers:subagent-driven-development onto Provider Packs

> The token-efficient way to run the SDD skill's subagent roles through provider packs
> instead of the controller's native subagent mechanism (see controller adapter).
> Companion to [core/roles.md](roles.md) and the active provider's resolved models.yaml.

## Process authority: the invoked skill, not this document

The wrapped skill — `superpowers:subagent-driven-development`, invoked at Step 0 of the
`swingle-sdd` skill — is the **sole authority on process**: the task loop, briefs and
review packages, status vocabulary and its handling, fix rounds and their caps, review
verdicts, the ledger, the pre-flight scan, and the final review. This document never
restates that content, and it binds to whatever version of the skill is installed at run
time. A summary here would be a staleness footgun: it drifts silently the moment
superpowers ships a change, and a controller trusting the summary would follow a process
the skill no longer runs. Read the skill itself; this document adds only what swingle
owns — dispatch mechanics, economics, and the controller gates below.

**Why the mapping works:** the stock skill moves its bulk artifacts (briefs, reports,
diffs) as file paths, which is exactly the shape a provider-pack dispatch needs. The wins
below come from pushing the remaining pasted things (prompt templates, dispatch stdout)
out of controller context too.

## Role → dispatch mapping

| SDD role | Lane | Dispatch shape |
| --- | --- | --- |
| Implementer | `implement` | background, per-task log, brief+report paths, contract file |
| Task reviewer | `review` | background, brief+report+diff paths, constraints block, contract file |
| Fix subagent | same lane as implementer | resume the implementer session where possible |
| Final whole-branch review | `review`, most-capable tier | `review-package MERGE_BASE HEAD` path + Minor-findings ledger list |
| Pre-flight scan, adjudication, ledger, gates | **controller — never dispatched** | n/a |

Role tiers and lanes are in [core/roles.md](roles.md). Resolve the selected tier against the
provider's layered models.yaml; apply [core/liveness.md](liveness.md).

## Dispatch flavours & economics — say which one you mean

“Dispatch” is ambiguous. Five execution modes, three currencies. The currencies, in order
of scarcity: **main-thread context** (multiplicative — resident tokens are re-sent every
turn and degrade the controller's judgment as they accumulate), **controller token budget**
(our spend; disposable subagent contexts are one-shot), **provider cost** (largely fixed by
the task, with cold-start overhead per execution).

| Mode | Main-ctx / task | Controller tokens | Provider cost | When |
| --- | --- | --- | --- | --- |
| **Inline** (controller does it) | 15–40k+, grows with task size | full task, premium | 0 | below the orchestration floor (~2k of work, single-file mechanical), or judgment-core work |
| **Sub-dispatch** (native subagent) | 1–3k (prompt + report) | full task, isolated context | 0 | judgment-heavy isolated work; the `native-subagents` lever |
| **Pack dispatch** | ~2k + **6–8 controller turns** | orchestration only | task cost | the SDD default for typical plans (≤ ~6–8 tasks) |
| **Supervised pack dispatch** (cheap native subagent runs the pack cycle) | ~0.5k — one consolidated report | supervisor turns | task cost | long plans where the controller's orchestration turns are the binding cost |
| **Delegate** (one-off pack dispatch, no plan — the `swingle-delegate` skill) | ~1–2k/job | orchestration only | task cost | explicitly requested self-contained jobs or homogeneous batches arriving outside a plan; auto-supervised at ≥3 planned cycles |

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

**E1a — the status vocabulary is the one exception: state it inline in every dispatch
prompt.** E1 moves contract text out of the prompt; the four-token status line stays in it.
Cheapest-tier conformance depends on the requirement sitting inline in the dispatch prompt
rather than only in the referenced contract (see core/verification-log.md, "2026-07-23 —
inline status instruction promoted from lead to playbook rule (E1a)" entry). Append to
the dispatch prompt verbatim:

> *“End with a status block whose first line is exactly one of: STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED.”*

The contract file keeps the full semantics of each token; the prompt carries only the four
words and where to put them. This changes what a *missing* block means not at all — see the
safety doctrine: absent or non-conforming is UNKNOWN, and on-disk evidence, never a raised
tier, is what settles whether the work is sound.

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

## Deliberate overrides (swingle's rules, stated as swingle's rules)

These are the only places swingle substitutes its own mechanism for the stock skill's.
Each is stated as a swingle rule with its rationale — never as a claim about what the
stock skill currently does, which this document does not track:

- **In session-tree dispatch, the controller commits; external agents never
  commit there** (safety doctrine; on sandbox-enforced packs a session-tree
  agent commit is structurally blocked when the workspace excludes the gitdir).
  In worktree dispatch, the agent's commits on the named run branch ARE the
  deliverable; landing remains controller-only. This replaces any stock
  commit-ownership arrangement.
- **Questions, fixes, and re-reviews ride the provider resume channel** (E3) — the
  pack's validated continuation mechanism against the recorded session id — in place of
  whatever dispatch mechanics the stock skill uses for its fix and question flows. The
  stock skill's *cadence* rules (rounds, caps, escalation, adjudication) still govern;
  only the transport is swingle's.
- **Swingle's operating contracts, copied to the workspace and referenced by path** (E1),
  replace the stock skill's dispatch prompt templates — the contracts carry the
  pack-dispatch specifics (report transport, status protocol, containment) the stock
  templates cannot know.
- **Gate depth scales with risk** (E6): stat + verdicts always, full package on
  findings/risk/contest — swingle's controller-spend rule for its own gate reads.

Everything not overridden here is governed by the invoked skill as it ships at run
time — read it there, never from a summary.
