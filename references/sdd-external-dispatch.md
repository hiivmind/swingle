# Mapping superpowers:subagent-driven-development onto External CLIs

> How the SDD skill actually operates, and the token-efficient way to run its subagent
> roles on codex / opencode / agy instead of Claude subagents. Companion to
> [dispatch-reference.md](dispatch-reference.md) (CLI behavior) and
> [model-catalog.md](model-catalog.md) (which model per role).
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
   most-capable model; one consolidated fix dispatch if findings.

Controller-only judgment (never offloaded): pre-flight plan conflict scan, status
adjudication, ⚠️ cannot-verify-from-diff resolution, plan-contradiction escalation to the
human, ledger, and the hard gate (re-run test gates, inspect diffs).

**The key structural fact:** the skill is already file-centric — briefs, reports, and diffs
move as paths, not pasted text. That is exactly the shape an external CLI dispatch needs,
so the mapping is natural; the wins below come from pushing the last pasted things
(the prompt templates, the CLI's stdout) out of controller context too.

## Role → dispatch mapping

| SDD role | CLI lane | Dispatch shape |
| --- | --- | --- |
| Implementer | **codex** `-s workspace-write` (default lane: sandboxed, validated) — opencode/agy per routing levers | background, per-task log, brief+report paths, contract file |
| Task reviewer | **codex `-s read-only`** — the only *enforced* read-only lane of the three | background, brief+report+diff paths, constraints block, contract file |
| Fix subagent | same lane as implementer | resume the implementer session where possible (see below) |
| Final whole-branch review | most-capable tier (`gpt-5.6-sol` / `glm-5.2` / `gemini-3.1-pro-high`) | `review-package MERGE_BASE HEAD` path + Minor-findings ledger list |
| Pre-flight scan, adjudication, ledger, gates | **controller — never dispatched** | n/a |

Models per role: [model-catalog.md](model-catalog.md). Liveness rules apply to every
background dispatch: [dispatch-reference.md → Background dispatch & liveness](dispatch-reference.md).

## Dispatch flavours & economics — say which one you mean

"Dispatch" is ambiguous. Four execution modes, three currencies. The currencies, in order
of scarcity: **main-thread context** (multiplicative — resident tokens are re-sent every
turn and degrade the controller's judgment as they accumulate), **Claude token budget**
(our spend; disposable subagent contexts are one-shot), **external dollars** (near-free
at luna/flash rates — largely fixed by the task, ~7.5k cold-start overhead per exec).

| Mode | Main-ctx / task | Claude tokens | External | When |
| --- | --- | --- | --- | --- |
| **Inline** (controller does it) | 15–40k+, grows with task size | full task, premium | 0 | below the orchestration floor (~2k of work, single-file mechanical), or judgment-core work |
| **Sub-dispatch** (Claude subagent via Agent tool) | 1–3k (prompt + report) | full task, isolated context | 0 | judgment-heavy isolated work; the "all Claude" lever |
| **Ext-dispatch** (Bash → codex/opencode/agy) | ~2k + **6–8 controller turns** | orchestration only | task cost | the `/sdd` default for typical plans (≤ ~6–8 tasks) |
| **Supervised ext-dispatch** (cheap Claude subagent runs the ext cycle) | ~0.5k — one consolidated report | supervisor turns on haiku/sonnet | task cost | long plans where the controller's orchestration turns are the binding cost |

Rules that fall out:

- **The main game is conserving main-thread context.** External tokens are linear,
  one-shot, cheap; controller-resident tokens are re-billed every turn for the rest of
  the session and — worse — crowd the adjudicator's attention. Flat ~2k/task context is
  what lets a 20-task plan finish without compaction (whose observed failure mode is
  re-dispatching completed work).
- **The triviality floor**: if the controller could complete the task in fewer tokens
  than the orchestration cycle costs (~2k + 6–8 turns), do it inline. Batch several
  trivial tasks into ONE ext-dispatch rather than paying the ~7.5k cold start per task.
- **Supervised ext-dispatch** moves the orchestration turns (launch, liveness, mechanical
  gate, reviewer dispatch, verdict collection) into a disposable cheap-Claude context that
  returns one report with evidence *paths*. Non-negotiable: **adjudication and commits
  stay in the main thread** — the supervisor's "all green" is evidence to check, not a
  gate result; the controller still reads verdicts, spot-checks the stat, and commits.
- Fixed cost per external exec is real (~7.5k tokens before any work, measured) but paid
  in the cheap currency; never let it push a large task inline — task *size* is exactly
  what the flat-context property protects against.

## Token-efficiency playbook

The controller's context is the scarce resource; external agents' tokens are cheap.
Every rule below moves bytes from controller context to files or to the external agent.

**E1 — Contracts are files, written once per session, not pasted per dispatch.**
The skill's prompt templates (~140 and ~190 lines) are designed to be filled and pasted
into every dispatch — with external CLIs that is ~2–3k controller tokens *per dispatch*,
three dispatches per task. Instead: copy the adapted contracts from
[../contracts/](../contracts/) into the SDD workspace once
(`cp "${CLAUDE_PLUGIN_ROOT}/contracts/"*.md "$(scripts/sdd-workspace)"/`), then every dispatch prompt is
~10 lines: *"Read <workspace>/implementer-contract.md — your operating contract. Read
<brief> — your requirements. Scene: <one line>. Interfaces from prior tasks: <lines or
'none'>. Report to <report-file>. Begin."* The contract text never transits the
controller again.

**E2 — CLI stdout never enters controller context.**
Foreground dispatch streams every agent turn into the Bash tool result — tens of
thousands of tokens of someone else's thinking. Always background + redirect to the
per-task log (which the liveness protocol wants anyway). The controller reads back only:
the ≤15-line status block (codex `-o` file, or `tail -30` of the log), the report file
*when adjudication needs it*, and `git diff --stat`. Never `cat` a full log or diff into
context — the reviewer reads the diff file; the controller reads verdicts.

**E3 — Questions and fixes ride the resume channel, not fresh dispatches.**
The skill's Q&A loop ("ask before beginning", NEEDS_CONTEXT) maps onto session resume:
the agent exits with NEEDS_CONTEXT and its questions in the status block; the controller
answers via `codex exec resume --last "<answers>"` / `opencode run -s <id> "<answers>"` /
`agy --conversation <id> -p "<answers>"`. The agent keeps its loaded context — the brief,
the codebase exploration — so nobody re-pays for it. Same for the fix loop: resume the
implementer's session with the findings list instead of cold-starting a fix agent that
rebuilds context (the skill's own data: a final-review fix wave of cold fixers cost more
than all tasks combined — one resumed/consolidated fixer, always).

**E4 — codex implementers do not commit; the controller commits.**
codex's sandbox makes `.git` read-only by design, and the doctrine wants
controller-commits anyway. Adapted contract: implementer implements + tests + writes
report, does NOT commit. Controller sequence per task: record BASE → dispatch → gate
(tests re-run, stat read) → `git add -A && git commit` → `review-package BASE HEAD` →
reviewer. One commit per task instead of the implementer's own commit granularity — an
accepted trade for the sandbox. (agy/opencode *could* commit but must not — same contract.)

**E5 — Reviewers ride the enforced read-only lane.**
`codex exec -s read-only` is the only dispatch on any CLI where "review is read-only"
is enforced rather than requested. Default all per-task reviewers there. When a reviewer
must run on agy/opencode (perspective diversity), the clean-tree + diff-after rule is the
only protection — check `git status` before accepting its verdict.

**E6 — Gate depth scales with risk (controller's own token spend).**
The hard gate's expensive half is the controller reading diffs. Scale it: always read the
status block + `git diff --stat` + both reviewer verdicts; read the full review package
only when the reviewer reports findings, flags ⚠️ items, the task touches a critical
path, or the stat disagrees with the report. The reviewer — whose tokens are cheap — always
reads the full package; the controller reads it on demand. (This tightens "reads every
diff" into "reads every stat, every verdict, and every contested diff" — the gate that
actually catches lies at a fraction of the spend.)

**E7 — Ledger discipline unchanged, plus session ids.**
The ledger line gains the dispatch session id:
`Task N: complete (commits <base7>..<head7>, review clean, session <id>)` — so post-
compaction recovery can still resume a half-finished agent instead of restarting it.

### What a task costs the controller under this playbook

~10-line dispatch × 2–3, one status block × 2–3, one stat, two verdicts, one ledger line —
**≈ 1–2k controller tokens per task**, roughly independent of task size. The pasted-template,
foreground-stdout alternative runs 15–40k per task and grows with task size. The offload
target — controller as thin adjudicator, external CLIs as the working mass — is met.

## Divergences from the stock skill (deliberate)

| Stock skill | External-CLI adaptation | Why |
| --- | --- | --- |
| Implementer commits its own work | Controller commits after gating | codex `.git` read-only by design; controller-commits doctrine |
| Fix subagent = fresh dispatch | Resume implementer's session | context already paid for; skill's own cost data on fix waves |
| Templates pasted per dispatch | Contract files in workspace, referenced by path | E1 — the single largest controller saving |
| Subagent questions answered inline | NEEDS_CONTEXT status → resume with answers | one-shot CLIs; resume keeps agent context |
| "Controller reads every diff" | Stat + verdicts always; full diff on findings/risk/contest | E6 — gate power at a fraction of spend |

Everything else — pre-flight scan, two-verdict reviews, fix→re-review loops, ⚠️ handling,
ledger, never-parallel implementers, final most-capable review, plan contradictions go to
the human — carries over unchanged.
