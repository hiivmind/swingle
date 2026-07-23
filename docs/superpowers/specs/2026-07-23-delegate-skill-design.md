# `delegate` Skill Design — sdd-dispatch v1.3.0

> Approved 2026-07-23. Revised same day after external design review (codex /
> most-capable review tier, verdict NEEDS_CHANGES — all findings folded in, one
> partial: flat workspace layout retained over per-attempt directories).
> Direct one-off delegation to external CLIs through the provider packs — dispatch,
> liveness, safety gates, and resume — WITHOUT the SDD plan/brief/two-verdict
> machinery. The sibling of the `sdd` skill: same engine, no plan.

## Purpose and boundary

The boundary is **semantic, not transport-based**:

- **`sdd`** = dependency-aware execution of a multi-task implementation plan: task
  briefs, two-verdict reviews, fix loops, a plan-keyed ledger, final whole-branch
  review. If the work is a plan — whether it arrived as a file, a pasted numbered
  checklist, or a long structured message — use `sdd`.
- **`delegate`** = an **explicitly requested**, self-contained job or homogeneous batch,
  regardless of where its text originated: "port this file", "find where X is
  configured", "summarise these release notes", "review this diff". One deliverable, no
  cross-task dependency graph.
- **The playbook's triviality floor still applies**: a task the controller could finish
  inline in fewer tokens than the orchestration cycle costs stays inline — delegate it
  externally only when the caller explicitly asked for delegation.
- Delegation is always explicit (matching `allow_implicit_invocation: false` in the
  Codex metadata): the skill runs because the caller invoked it or asked for
  delegation, never because a request merely looked delegable.

`delegate` never reads or writes `.superpowers/sdd/` and has **no superpowers
dependency**.

**v1 scope: git repositories.** In a non-repo working directory only read-only
research/synthesis is accepted: artifacts go to the harness's temporary/job directory,
no durable ledger exists, and NO resume promise is made (say so in the reply).
Write-lane work in a non-repo directory is refused — there is no snapshot/delta
mechanism to gate it.

## 1. Invocation and role inference

Invocation: `delegate <task>` (skill argument or an explicit conversational request),
with optional levers anywhere in the request:

- **Provider**: "via agy" / "via codex" / "via opencode" — same semantics as `sdd`.
- **Tier**: "floor it" (default when silent), "play it safe" (one tier up; at
  most-capable it is already the ceiling — say so and proceed), or an explicit model
  id. An explicit model must appear in the **resolved role's eligible resolution
  sequence** (the tier/lane candidate walk in the routed pack's models.md) — a model
  that exists in models.md but is not eligible for this role's tier/lane → ask, never
  silently accept or substitute.
- **Review**: "with review" — write lane: adds the reviewer dispatch (§4). Read lane:
  adds a second independent reader on the same task; the controller compares the two
  reports (no new contract needed).
- **Lane pin**: "read-only" — forces the read lane. If the task text simultaneously
  demands writes ("fix this, read-only"), that is a contradiction: ask which governs,
  never silently convert requested write work into analysis.
- **Supervision**: "supervised" / "unsupervised" — overrides the automatic trigger (§5).
- **Native**: the `native-subagents` lever ("all Claude" under Claude Code) bypasses
  external dispatch per the harness adapter; provider routing and model resolution do
  not apply and supervision is moot (the native subagent IS the worker). Native routing
  has its own announcement and ledger forms (§6). If the harness's native subagent
  mechanism is unavailable when explicitly requested → stop and ask; if unavailable
  when merely auto-selected (supervision) → fall back to controller orchestration with
  an announcement.

**Role inference (hybrid).** Classify the task against the **full seven-row table in
`core/roles.md`** — transcription implementer, adaptation implementer, large-codebase /
long-context implementer, read-only explore, external research/synthesis, per-task
reviewer, final/design reviewer. The table is the authority; do not work from a
shortened paraphrase (under-tiering design reviews and long-context work is exactly the
failure this rule prevents). Announce the resolution in ONE line before dispatching:

```
delegate: job=NNN role=<roles.md row> tier=<tier> lane=<lane> provider=<id> model=<model> supervised=<yes: N cycles|no>[ review=yes]
```

The announcement is the caller's override point. When a task genuinely straddles lanes
("look into X and fix it"), ask ONE question (investigate-only vs investigate-and-fix)
before dispatching; never guess a write when a read was plausible.

**Batching.** A homogeneous batch (near-identical mechanical items) is ONE job = one
dispatch (triviality-floor doctrine — never pay a cold start per trivial item).
Heterogeneous tasks are separate jobs, run sequentially. Never parallel write-lane
dispatches. Parallel read-lane dispatches are permitted ONLY when ALL hold: the routed
provider has an **enforced** read-only lane (read-only is intent, not enforcement, on
unsandboxed packs — two concurrent "readers" there can both write and conflict), output
paths are distinct, and the pack's `session-source` attributes sessions
deterministically under concurrency (exec/conversation-scoped output yes; a
newest-first session list races — serialize those).

## 2. Setup — Step-0-lite

Once per session, before the first delegate dispatch — identical to `sdd` Step 0 minus
every superpowers-specific step:

1. Identify the controlling harness; read `skills/sdd/harnesses/<harness>.md` (the
   adapters are shared, not duplicated).
2. **Trust gate**: `python3 <root>/scripts/validate-packs --root <root>` — refuse to
   proceed on non-zero exit. Then `git -C <root> status --porcelain providers/` — any
   untracked/modified provider directory requires explicit user approval.
3. **Detection**: read each `providers/*/pack.md` manifest; INSTALLED iff
   `command -v -- "<cli>"` succeeds (data-only manifests; argv[0]==cli is
   validator-enforced).
4. **Layered config** (first found): `$SDD_DISPATCH_CONFIG` →
   `<project>/.sdd-dispatch.json` → `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/config.json`.
   Same validation and STOP conditions as `sdd`. ACTIVE = installed − disabled
   (− incompatible iff require-verified-version).
5. **Compatibility**: `version-argv` output vs `verified-version`; mismatch → warn and
   suggest `sdd-dispatch-verify <id>` (block iff config requires it).
6. **Routing**: per-request provider directive → session lever → config
   `providers_by_lane[lane]` / `default_provider` → codex-if-active else
   sole-active-iff-exactly-one → ask. Inactive provider named anywhere → ask.
7. **Model resolution**: role → (tier, lane) via `core/roles.md` → ordered candidates in
   the routed pack's models.md (verified/experimental; exact-lane rows by priority, then
   (tier, any) rows). None → ask.
8. **Readiness**: the pack's bounded preflight before the FIRST dispatch to a provider
   (agy: the settings.json permission-baseline probe from its pack — on miss, STOP and
   hand the user the pack's baseline section).
9. **Workspace**: create `.sdd-dispatch/delegate/` (§6). Ignore handling: check with
   `git check-ignore -q .sdd-dispatch` — if not ignored, append `.sdd-dispatch/` to
   `.git/info/exclude` (repo-local, never tracked) and tell the user. **Never edit a
   tracked `.gitignore` implicitly** — that dirties the tree immediately before a gate
   that requires it clean; if the user wants the entry tracked, that is their separate
   commit. Copy the three operating contracts from `<root>/contracts/`
   (implementer, task-reviewer, reader) into the workspace once per session.

Explicitly absent: superpowers:subagent-driven-development invocation,
`scripts/sdd-workspace`, plan reading, pre-flight plan scan, task briefs.

## 3. Dispatch cycle

Each **job** gets the next number `NNN` (001, 002, …), **allocated durably in the
ledger before launch** (§6) — a killed supervisor or compaction never loses the
number→task mapping.

**Contract by role class:**

- Implement roles → `implementer-contract.md`.
- Explore / research / synthesis → `reader-contract.md` (new in this design): read-only
  ground rules, evidence discipline (every claim carries file:line or source), the same
  status vocabulary, and an ANSWER line in the status block.
- Primary review jobs ("review this diff/PR/document") → `task-reviewer-contract.md`,
  with the controller generating the review inputs the contract expects: the artifact
  under review as a package file (for a diff: commit list + stat + `-U10`), plus
  whatever requirements text the caller supplied in place of a brief.

**Cycle:**

1. Write the prompt to `.sdd-dispatch/delegate/NNN-prompt.md`: contract path (per role
   class above), the task text verbatim, scene (one line: repo, branch, relevant
   paths), the report-file path (`NNN-report.md`), and the report contract — status
   ≤15 lines back (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED), detail in the
   report file.
2. **Write lane pre-dispatch snapshot**: the tree must be CLEAN — `git status
   --porcelain=v1 --untracked-files=all` empty, no exceptions on any pack (on
   unsandboxed packs a dirty tree destroys change attribution; doctrine forbids it).
   Record BASE (= HEAD) and the current branch.
3. Dispatch with the active pack's canonical template inside the self-reaping wrapper
   (`core/liveness.md`), stdout to `NNN-dispatch.log`. Completion is observed via the
   **harness adapter's declared mechanism** (background-task notification, polling, or
   the detached marker-file form — whichever the adapter specifies for the mode in
   use); never foreground stdout. **Session capture is asynchronous and
   provider-specific**: obtain the session id per the pack's `session-source` and
   append it to the ledger the moment it is observed — do not assume it exists at
   launch time.
4. **Post-dispatch evidence gate** (exit codes are never evidence of work):
   - Write lane: HEAD must be UNCHANGED (an agent-created commit is a doctrine
     violation to surface, not absorb); then read `git status --porcelain=v1
     --untracked-files=all` and `git diff HEAD --stat` — together these cover
     unstaged, staged, AND untracked changes (bare `git diff` misses staged; `status`
     alone misses content). Untracked files created by the agent are part of the
     change: list them and include their content in any review package.
   - Read lane: `git status --porcelain=v1 --untracked-files=all` must be EMPTY (any
     mutation is a doctrine violation to surface, not silently reset), and the report
     file must exist, postdate the dispatch, and answer the task.
5. **NEEDS_CONTEXT, follow-ups, and fixes ride the resume channel** — the pack's
   validated continuation mechanism against the recorded session id. Cold re-dispatch
   only when the resume channel fails, with the prior report attached.
6. **Failure handling — classify by scope, apply pack-specific recovery FIRST:**
   - *Provider-wide* (auth expired, CLI misconfigured, permission baseline missing) →
     STOP; fix the environment or ask. Never advance the model candidate — every
     candidate would fail identically.
   - *Candidate-specific rejection* (model-not-found, model-level 4xx) → advance to the
     next candidate in the resolution order (same provider, max 3 attempts per job);
     cross-provider moves are always a user question.
   - *Transient transport/startup* → the pack's own documented recovery first (e.g. a
     pack's retry-once rule); only then treat as candidate-specific.
   - *Stall/kill with partial progress* → RESUME the session (a kill is a checkpoint,
     not a restart); check `git diff HEAD` for work already landed before resuming.
   - *Task/context blocker* (BLOCKED, NEEDS_CONTEXT) → controller adjudication:
     these are statements about the task or environment, not the model — answer,
     unblock, or escalate to the user. No automatic anything.
   - *Quality failure* (wrong/poor work, review rejection) → never auto-fallback;
     escalate tier or adjudicate with the user.
   - Every attempt appends:
     `model-attempt: job=NNN role=<role> provider=<id> model=<id> class=<scope> outcome=<failed|ok>`.

## 4. Gate, results, and opt-in review

**Controller hard gate — always, both lanes** (the on-disk checks are specified in
§3 step 4):

- Write lane, no review requested: the controller **inspects the actual diff**
  (`git diff HEAD` plus untracked-file content), not just the stat — an unreviewed
  change's contents must pass controller eyes before tests/commit. With review
  requested, the reviewer reads the full package and the controller may gate on stat +
  verdicts (E6 economics).
- Write lane: the controller re-runs the covering tests named in the task (or the
  project's default gate) itself, never trusting the agent's claimed results.
- **The controller commits** — and only when the user asked for a commit; otherwise
  leave the working tree for the user with a `git diff --stat` summary. External agents
  never commit.
- **Read lane — the report IS the deliverable**: the controller reads the report,
  checks it is fresh (postdates the dispatch) and actually answers the task, then
  returns the substantive answer (or a faithful summary plus the report path) to the
  user. Report-exists is the floor, not the gate: an empty, stale, or off-task report
  fails.

**Opt-in review ("with review", write lane)**: one external reviewer dispatch before
any commit — review role, standard tier (scaled up for large/risky diffs), review lane,
task-reviewer contract, given the task text, the report, and a review package
(BASE→current: commit list + stat + `-U10` diff of tracked changes + full content of
agent-created untracked files) written to `NNN-review-package.md`; reviewer output to
`NNN-review.md`. Critical/Important findings ride the implementer's resume channel; the
re-review resumes the ORIGINAL reviewer's thread with the fix summary and a fresh
versioned package (`NNN-review-package-2.md`). One fix/re-review round by default;
further rounds are a user decision.

**"with review" on a read-lane job**: a second independent reader (same contract, same
inputs, different session — different model or provider when eligible); the controller
compares the two reports and reconciles disagreements before answering.

## 5. Supervised delegate (auto by cost, announced)

The playbook's supervised-pack-dispatch flavour, applied to delegate: one cheap
harness-native subagent (per the harness adapter) runs the mechanical cycle — prompt
files, pack dispatch inside the liveness wrapper, completion watching, the mechanical
gate reads (status block, porcelain/diff checks, report existence), reviewer dispatch
when "with review", verdict collection — and returns ONE concise report with evidence
*paths* plus the ledger lines it appended.

**Trigger — a precise formula, computed AFTER batching:**

```
cycles = (planned initial worker dispatches) + (planned initial reviewer dispatches)
```

A homogeneous batch is one job = 1 cycle (2 "with review"). Retries, resumes, fix
rounds, and re-reviews are NOT counted — they are unplanned. `cycles ≤ 2` → the
controller orchestrates directly (a supervisor would cost more than it saves).
`cycles ≥ 3` → supervised, announced in the pre-dispatch line
(`supervised: yes — 4 cycles`). An explicit "supervised" / "unsupervised" lever always
overrides. If the harness's native subagent mechanism is unavailable, auto-supervision
falls back to controller orchestration with an announcement.

**Non-negotiable doctrine (unchanged from the playbook):** adjudication and commits stay
in the main thread. The supervisor's "all green" is evidence to check, not a gate
result — the controller re-reads the verdict lines, spot-checks the porcelain/diff
evidence against the report, re-runs the covering tests for write-lane work, and
performs any commit itself. The supervisor appends ledger and `model-attempt:` lines as
it goes, so a killed supervisor loses no state (job numbers are allocated in the ledger
before launch).

**Escalation paths out of the supervisor:** NEEDS_CONTEXT, BLOCKED, quality failures,
and lane-straddle ambiguity are returned in the supervisor's report, never resolved by
it. The controller answers NEEDS_CONTEXT through the pack's resume channel directly
(the session id is already in the ledger) or hands the answer to a fresh supervisor
cycle for the remaining batch; quality failures follow §3's no-auto-fallback rule.

## 6. Workspace and ledger

`.sdd-dispatch/delegate/` at the repo root, ignored via `.git/info/exclude` (§2 step 9).
Supervised runs use the same workspace and numbering — the supervisor appends to the
same ledger. Flat layout (per-attempt subdirectories were considered and rejected as
more structure than a one-off skill warrants — attempts are distinguished in the ledger,
not the filesystem). Contents:

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
```

**Ledger = append-only lifecycle events**, one line each, written at the moment the
event happens (never only at completion — a crash between launch and completion must
not lose the number→task→session mapping):

```
NNN allocated: role=<role> task="<summary, ≤10 words>" prompt=NNN-prompt.md
NNN dispatched: provider=<id> model=<id> attempt=<n>
NNN session: <session-id>                      # appended when observed (async, §3.3)
NNN review-dispatched: provider=<id> model=<id>
NNN review-session: <session-id>               # reviewer's own resume thread
NNN resumed: <reason: needs-context|fix|follow-up>
NNN complete: status=<DONE|...> outcome=<committed <sha7>|diff-left|answer-returned|blocked>
model-attempt: job=NNN role=<role> provider=<id> model=<id> class=<scope> outcome=<failed|ok>
```

Worker and reviewer session ids are BOTH recorded (playbook E3/E7: fix rounds resume
the worker's thread, re-reviews resume the reviewer's). The `task=` summary plus the
prompt path make "ask that agent a follow-up" unambiguous after compaction or across a
batch.

**Native routing forms**: announcement
`delegate: job=NNN role=<role> tier=<tier> lane=<lane> route=native supervised=no` and
ledger `NNN dispatched: route=native` (no provider/model/session fields — continuation
follows the harness's native mechanism, recorded as `NNN native-ref: <harness ref>`
where the harness provides one). Workspace, evidence gates, and controller commits are
unchanged — native routing changes the worker, not the doctrine.

## 7. Deliverables

| Change | File(s) |
| --- | --- |
| New skill | `skills/delegate/SKILL.md` |
| New contract | `contracts/reader-contract.md` |
| Codex metadata | `skills/delegate/agents/openai.yaml` (implicit invocation FALSE — it writes) |
| Flavour table entry | `core/playbook.md` — fifth row: one-off pack dispatch, no plan; prose "Four execution modes" → "Five execution modes" |
| Docs | `README.md` skills table + a short `delegate` section |
| Tests | `tests/` — delegate-skill structural tests (see §8) |
| Version → **1.3.0** | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, README `**Version:**` |

Untouched: `core/` doctrine files (except the playbook row + mode-count prose),
`providers/`, existing `contracts/`, `skills/sdd/` — zero pack changes. The delegate
skill reads the shared harness adapters at `skills/sdd/harnesses/<harness>.md`; if a
future round promotes those to a shared location, both skills move together.

Purity boundary holds: `skills/delegate/SKILL.md` may name providers but carries no
model ids or invocation strings — those stay in the packs.

## 8. Testing

- Static gates: `python3 scripts/validate-packs --root .` and `./scripts/codex-smoke`
  (extended with existence checks for the new skill files and reader contract).
- **New pytest structural tests** (not a fragile deny-list grep): (a) purity by
  provider-data comparison — collect every model id from `providers/*/models.md` tables
  and assert none appears in any `skills/*/SKILL.md`; (b) delegate SKILL.md has valid
  frontmatter (name, description); (c) no `superpowers` or `.superpowers/` references
  in the delegate skill; (d) the four status words all present; (e)
  `skills/delegate/agents/openai.yaml` declares `allow_implicit_invocation: false`.
- Live smoke A (read lane): one explore-question delegate against this repo on the
  cheapest tier — verifies inference → announcement → dispatch → report gate (freshness
  + answers-the-task) → answer returned → ledger events, and the clean-tree/porcelain
  doctrine.
- Live smoke B (write lane): one small write task "with review" in a throwaway repo —
  verifies clean-tree requirement, BASE/branch snapshot, the strengthened evidence gate
  (staged + untracked + HEAD-unchanged), reviewer dispatch with untracked content in
  the package, resume-channel fix loop, versioned re-review package, controller commit.
- Live smoke C (supervised): a batch of ≥3 small mechanical tasks in a throwaway repo —
  verifies the cycle formula and announcement, supervisor cycle management,
  supervisor-written lifecycle ledger lines (allocated-before-launch), and the
  controller's independent re-check of the supervisor's "all green" before commit.
- All smokes run on an active pack lane (agy or codex) and their findings append to the
  usual verification logs if they surface pack facts.

## Out of scope (backlog)

- Cross-repo delegate (dispatching into a different repo than the CWD).
- Non-repo write-lane support (needs a snapshot/delta mechanism).
- A dedicated report-review contract for read-lane output (v1 uses a second independent
  reader instead).
- A shared `skills/_shared/harnesses/` promotion for the adapters.
