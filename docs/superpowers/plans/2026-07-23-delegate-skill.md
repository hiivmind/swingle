# Delegate Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `delegate` skill to the sdd-dispatch plugin: direct one-off dispatch of a self-contained job (or homogeneous batch) to an external CLI through the provider packs, without the SDD plan-execution machinery.

**Architecture:** One new skill directory (`skills/delegate/`) plus one new operating contract (`contracts/reader-contract.md`), reusing the engine untouched — `core/` doctrine, `providers/` packs, existing contracts, and the shared harness adapters at `skills/sdd/harnesses/`. Plus a playbook flavour row, README updates, structural pytest tests, and a version bump to 1.3.0.

**Tech Stack:** Markdown skill files; bash/python3 gates (`scripts/validate-packs`, `scripts/codex-smoke`); pytest for structural tests.

**Spec:** `docs/superpowers/specs/2026-07-23-delegate-skill-design.md` (revised after external design review) — the authority for all behavior described below.

## Global Constraints

- Work on branch `feature/delegate-skill`; never commit to `main`.
- Before EVERY commit: `python3 scripts/validate-packs --root .` AND `./scripts/codex-smoke` must exit 0.
- Purity boundary: `skills/delegate/SKILL.md` may name providers (codex/opencode/agy) but must contain NO model ids and NO invocation strings — those live only in `providers/<id>/`.
- Version 1.3.0 must appear in exactly three places, in sync: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, README `**Version:**` line.
- `skills/delegate/agents/openai.yaml` sets `allow_implicit_invocation: false` (the skill writes).
- No OPERATIONAL superpowers dependency in the delegate skill: it must not invoke superpowers skills or run `scripts/sdd-workspace`; exactly one negative-disclaimer mention each of `scripts/sdd-workspace` and `.superpowers/sdd` is required and allowed.
- Delegate workspace path is exactly `.sdd-dispatch/delegate/` at the repo root, ignored via the file resolved by `git rev-parse --git-path info/exclude` — NEVER by implicitly editing a tracked `.gitignore`.
- Statuses are exactly: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED.
- Supervision trigger formula: `cycles = planned initial worker dispatches + planned initial reviewer dispatches`, computed after batching; retries/resumes/fix rounds excluded; supervised iff cycles ≥ 3; explicit "supervised"/"unsupervised" overrides.
- Evidence gate: clean tree + recorded HEAD/branch before EVERY repository dispatch (both lanes); after — HEAD unchanged (both lanes), and for write lane staged+unstaged+untracked coverage (`git status --porcelain=v1 --untracked-files=all` + `git diff HEAD`).
- Pre-commit review containment: pre-commit reviewers ALWAYS run in an artifact-only scratch directory (review package + task text), never in the target repository, on every provider.

---

### Task 1: `contracts/reader-contract.md`

**Files:**
- Create: `contracts/reader-contract.md`

**Interfaces:**
- Consumes: the status vocabulary and report-file protocol established by `contracts/implementer-contract.md`.
- Produces: the contract file Task 2's SKILL.md references by name for explore/research/synthesis roles.

- [ ] **Step 1: Create `contracts/reader-contract.md`**

Exact content:

````markdown
# Reader Operating Contract (external-CLI edition)

You are answering one self-contained read task — codebase exploration ("where/how is X
done"), external research, or synthesis/summarisation. Your dispatch message names the
task, the report file, and any source materials. This contract is how you operate.

## Ground rules

- **Read-only.** Do not mutate the working tree, index, or any git state, and do not
  write any file except your report file. (On providers with an enforced read-only
  sandbox this is enforced; elsewhere it is your contract.)
- **If your dispatch says you cannot write files** (enforced read-only lane): your
  final message is the FULL report — everything the Report section below describes —
  instead of the short status block. Begin it with the same STATUS/ANSWER lines.
- If the task is unclear or a source named in your dispatch is missing, **stop and
  ask**: status NEEDS_CONTEXT with your questions in the final message. Do not guess.
- Evidence discipline: every claim in your report carries its source — file:line for
  code, URL or document name for research. Distinguish what you verified from what you
  infer.
- Stay in scope: answer the question asked; note adjacent discoveries in one line each
  rather than pursuing them.

## Report

Write the FULL answer to the report file named in your dispatch:
- The direct answer to the task, first
- Evidence: file:line references / sources for each claim
- What you searched or read, and any dead ends that shape confidence
- Open questions or caveats

Then your **final message** is ONLY this status block (≤15 lines — detail lives in the
report file):

```
STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
ANSWER: <one-line version of the answer>
SOURCES: <one line, e.g. "6 files cited" or "4 documents">
CONCERNS: <one line each, or "none">
REPORT: <report file path>
```

If BLOCKED or NEEDS_CONTEXT, put the specifics in the final message itself — the
controller acts on it directly.

## Resumed session

If the controller resumes this session with follow-up questions: answer them, APPEND
the additions to the same report file, and reply with a fresh status block. If your
dispatch said you cannot write files, the same switch applies on every resumed turn:
your final message is the full addition itself, and the controller appends it to the
saved report.
````

- [ ] **Step 2: Run the gates**

Run: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`
Expected: exit 0 (the contract is new content; no validator rule covers it yet).

- [ ] **Step 3: Commit**

```bash
git add contracts/reader-contract.md
git commit -m "feat: reader operating contract for explore/research delegation"
```

---

### Task 2: `skills/delegate/SKILL.md` + Codex metadata + codex-smoke checks

**Files:**
- Create: `skills/delegate/SKILL.md`
- Create: `skills/delegate/agents/openai.yaml`
- Modify: `scripts/codex-smoke` (add existence checks)

**Interfaces:**
- Consumes: `contracts/reader-contract.md` (Task 1), `core/roles.md`, `core/playbook.md`, `core/liveness.md`, `core/safety-doctrine.md`, `providers/<id>/pack.md` + `models.md`, `contracts/implementer-contract.md`, `contracts/task-reviewer-contract.md`, `skills/sdd/harnesses/<harness>.md`.
- Produces: the `delegate` skill (referenced by Task 3's README/playbook edits and Task 4's tests).

- [ ] **Step 1: Add the failing codex-smoke checks**

In `scripts/codex-smoke`, insert after the existing `skills/sdd/harnesses/codex.md` check block (after its `fi`):

```bash
if [ -f skills/delegate/SKILL.md ]; then
  pass "skills/delegate/SKILL.md exists"
else
  fail "skills/delegate/SKILL.md exists"
fi

if [ -f skills/delegate/agents/openai.yaml ]; then
  pass "skills/delegate/agents/openai.yaml exists"
else
  fail "skills/delegate/agents/openai.yaml exists"
fi

if [ -f contracts/reader-contract.md ]; then
  pass "contracts/reader-contract.md exists"
else
  fail "contracts/reader-contract.md exists"
fi
```

- [ ] **Step 2: Run codex-smoke to verify it fails**

Run: `./scripts/codex-smoke`
Expected: `FAIL: skills/delegate/SKILL.md exists`, `FAIL: skills/delegate/agents/openai.yaml exists`, PASS for the reader contract (Task 1 created it); exit code 1.

- [ ] **Step 3: Create `skills/delegate/SKILL.md`**

Exact content:

````markdown
---
name: delegate
description: Directly delegate an explicitly requested, self-contained job or homogeneous batch to an external CLI (codex/opencode/agy) through validated provider packs — role inference, model tiering, liveness, evidence gates, and session resume — without a written implementation plan. Use the sdd skill for multi-task implementation plans; keep sub-triviality-floor tasks inline unless delegation was explicitly requested.
---

# Delegate — Direct One-Off Dispatch

**Harness**: identify your controlling harness and read
`<root>/skills/sdd/harnesses/<harness>.md` (claude-code, codex) before setup — it maps
skill-loading, native subagent dispatch, background jobs, completion observation, and
asset-root resolution. `<root>` is this skill directory's grandparent (the directory
containing `skills/`, `core/`, `providers/`, `contracts/`).

**Boundary (semantic, not transport-based)**: `sdd` = dependency-aware execution of a
multi-task implementation plan (task reviews, plan ledger, final review) — use it
whenever the work is a plan, whether it arrived as a file, a pasted numbered checklist,
or a structured message. `delegate` = an **explicitly requested**, self-contained job or
homogeneous batch, wherever its text originated. The playbook's triviality floor still
applies: work the controller can finish inline for less than the orchestration cycle
stays inline unless the caller explicitly asked for external delegation. This skill has
**no superpowers dependency**: it never invokes superpowers skills, never runs
`scripts/sdd-workspace`, and never reads or writes `.superpowers/sdd/`.

**v1 scope: git repositories.** In a non-repo working directory accept only read-only
research/synthesis: artifacts go to a fresh
`mktemp -d "${TMPDIR:-/tmp}/sdd-delegate.XXXXXX"` directory, no durable ledger exists,
and no resume promise is made — say so in the reply. Refuse write-lane work outside a
git repository.

Read these plugin documents when their policy is needed:

- `<root>/core/roles.md` — the role → tier → lane table (the classification authority)
- `<root>/core/playbook.md` — dispatch flavours, economics, and controller gates
- `<root>/core/liveness.md` — required background and stall protocol
- `<root>/core/safety-doctrine.md` — containment and controller-gate doctrine
- `<root>/providers/<id>/pack.md` and `models.md` — validated provider behavior,
  canonical dispatch, session source, recovery rules, and model candidates

## Levers (parsed from anywhere in the request)

- **Provider**: "via agy" / "via codex" / "via opencode".
- **Tier**: "floor it" (default when silent) = cheapest model clearing the role's bar;
  "play it safe" = one tier up (at most-capable that is already the ceiling — say so
  and proceed); an explicit model id must appear in the resolved role's eligible
  resolution sequence (the tier/lane candidate walk in the routed pack's models.md) —
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
   same malformed-config STOP conditions as the `sdd` skill. ACTIVE = installed −
   disabled (− incompatible iff require-verified-version).
4. **Compatibility**: compare `version-argv` output to `verified-version`; mismatch →
   warn and suggest `sdd-dispatch-verify <id>` (block iff config
   require-verified-version).
5. **Routing**: per-request provider directive → session lever → config
   `providers_by_lane[lane-of-role]` / `default_provider` → codex-if-active else
   sole-active-iff-exactly-one → ask. Inactive provider named anywhere → ask, never
   silently reroute.
6. **Model resolution**: role → (tier, lane) via `core/roles.md` → ordered candidates in
   the routed pack's models.md (statuses verified/experimental; exact-lane rows by
   priority, then (tier, any) rows by priority); take the first; none → ask.
7. **Readiness**: before the FIRST dispatch to a chosen provider, run its bounded
   preflight per its pack (version + auth/session probe; agy: the headless permission
   baseline check — on miss, STOP and hand the user the pack's baseline section).
8. **Workspace**: create `.sdd-dispatch/delegate/` at the repo root. Check
   `git check-ignore -q .sdd-dispatch/delegate/.probe` (a child sentinel, so negation
   rules cannot silently expose workspace files); if not ignored, append
   `.sdd-dispatch/` to the file resolved by `git rev-parse --git-path info/exclude`
   (repo-local, never tracked; a literal `.git/info/exclude` path breaks in linked
   worktrees) and tell the user — NEVER edit a tracked `.gitignore` implicitly (it
   dirties the tree right before a gate that requires it clean; a tracked entry is the
   user's separate commit). Copy
   `implementer-contract.md`, `task-reviewer-contract.md`, and `reader-contract.md`
   from `<root>/contracts/` into the workspace once per session.

## Role inference and the announcement line

Classify the task against the **full seven-row table in `core/roles.md`** —
transcription implementer, adaptation implementer, large-codebase / long-context
implementer, read-only explore, external research/synthesis, per-task reviewer,
final/design reviewer. The table is the authority — never work from a shortened
paraphrase (that under-tiers design reviews and long-context work). Then announce, in
ONE line before dispatching:

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

**Output capture is role- and lane-specific — never demand an in-sandbox file write
the lane forbids**: review-role dispatches use the reviewer contract's own output
protocol (final message IS the verdict report), not the four-status block. On an
enforced read-only lane the agent cannot write `NNN-report.md` — the FULL
report/answer is the captured final output, saved by the controller (or the pack's
host-side output mechanism) to the workspace path; the reader contract carries this
switch. Unsandboxed read-intent lanes keep the report-file + short-status protocol.

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
   the role's output protocol — branch by role and lane per the output-capture rules:
   implement and unsandboxed read roles → report-file path (`NNN-report.md`) + the
   four-status block (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) as the
   final message; review roles → the reviewer verdict protocol (controller saves it
   to `NNN-review.md`); enforced read-only lanes → full report as captured final
   output (controller saves to `NNN-report.md`), on initial AND resumed turns.
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
(the package is self-contained by construction). A pre-commit reviewer never enters
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
````

- [ ] **Step 4: Create `skills/delegate/agents/openai.yaml`**

Exact content:

```yaml
interface:
  display_name: "Delegate to External CLI"
  short_description: "Directly delegate an explicitly requested, self-contained job or homogeneous batch to an external CLI (codex/opencode/agy) through validated provider packs, without a written implementation plan."
  default_prompt: "Delegate this task with the delegate skill."

policy:
  allow_implicit_invocation: false
```

- [ ] **Step 5: Run the gates to verify they pass**

Run: `./scripts/codex-smoke && python3 scripts/validate-packs --root .`
Expected: all PASS lines including the three new checks; exit 0.

- [ ] **Step 6: Commit**

```bash
git add skills/delegate/ scripts/codex-smoke
git commit -m "feat: delegate skill — direct one-off pack dispatch, no plan machinery"
```

---

### Task 3: Playbook flavour row + mode-count prose + README

**Files:**
- Modify: `core/playbook.md` (flavour table + "Four execution modes" prose, ~lines 50–64)
- Modify: `README.md` (Layout block, Skills table, new section)

**Interfaces:**
- Consumes: the `delegate` skill name and behavior from Task 2.
- Produces: nothing downstream (docs only; Task 4 bumps versions).

- [ ] **Step 1: Update `core/playbook.md`**

Change the sentence `“Dispatch” is ambiguous. Four execution modes, three currencies.` to:

```markdown
“Dispatch” is ambiguous. Five execution modes, three currencies.
```

In the "Dispatch flavours & economics" table, insert after the **Supervised pack dispatch** row:

```markdown
| **Delegate** (one-off pack dispatch, no plan — the `delegate` skill) | ~1–2k/job | orchestration only | task cost | explicitly requested self-contained jobs or homogeneous batches arriving outside a plan; auto-supervised at ≥3 planned cycles |
```

- [ ] **Step 2: Update the README Layout block and Skills table**

In the `## Layout` code block, insert after the `skills/sdd/` line:

```
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
```

In the `## Skills` table, insert after the `sdd` row:

```markdown
| `delegate` | Directly dispatch an explicitly requested one-off job or homogeneous batch through the provider packs — no plan required |
```

- [ ] **Step 3: Add the README `delegate` section**

Insert after the `## Skills` table:

```markdown
## Direct delegation

`delegate <task>` dispatches a self-contained job (or homogeneous batch) to an external
CLI with the full pack doctrine — role inference from `core/roles.md`, model tiering,
liveness, hardened evidence gates (staged + untracked + HEAD-unchanged), controller
commits, and session resume — but none of the SDD plan-execution ceremony. Levers:
`via <provider>`, `floor it` / `play it safe` / explicit model, `with review`,
`read-only`, `supervised` / `unsupervised`. Jobs implying ≥3 planned dispatch cycles
run supervised automatically (announced). Artifacts and the lifecycle ledger live in
`.sdd-dispatch/delegate/` (ignored via `.git/info/exclude`). The boundary is semantic:
multi-task implementation plans go to the `sdd` skill regardless of how they arrived;
tasks below the triviality floor stay inline unless delegation was explicitly
requested.
```

- [ ] **Step 4: Run the gates**

Run: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`
Expected: exit 0. (README `**Version:**` unchanged in this task.)

- [ ] **Step 5: Commit**

```bash
git add core/playbook.md README.md
git commit -m "docs: delegate flavour row, five execution modes, README section"
```

---

### Task 4: Structural pytest tests + version bump to 1.3.0

**Files:**
- Create: `tests/test_delegate_skill.py`
- Modify: `.claude-plugin/plugin.json` (`"version": "1.2.5"` → `"1.3.0"`)
- Modify: `.codex-plugin/plugin.json` (`"version": "1.2.5"` → `"1.3.0"`)
- Modify: `README.md` (`**Version:** 1.2.5` → `**Version:** 1.3.0`)

**Interfaces:**
- Consumes: Tasks 1–3 complete (files exist with the specified content).
- Produces: release-ready branch state.

- [ ] **Step 1: Write the failing structural tests**

Create `tests/test_delegate_skill.py`:

```python
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "delegate" / "SKILL.md"
YAML = ROOT / "skills" / "delegate" / "agents" / "openai.yaml"
READER = ROOT / "contracts" / "reader-contract.md"

def _model_ids():
    """Every model id declared in any provider's models.md Resolvable table."""
    ids = set()
    for models in (ROOT / "providers").glob("*/models.md"):
        for line in models.read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Tier | Lane | Priority | Model id | Status | ...
            if len(cells) >= 5 and cells[2].isdigit():
                ids.add(cells[3].strip("`"))
    return ids

def _pack_clis():
    """The validated cli name from every provider pack manifest."""
    clis = set()
    for pack in (ROOT / "providers").glob("*/pack.md"):
        m = re.search(r"^cli: (\S+)", pack.read_text(), re.M)
        if m:
            clis.add(m.group(1))
    return clis

def test_skill_exists_with_frontmatter():
    text = SKILL.read_text()
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert re.search(r"^name: delegate$", front, re.M)
    assert re.search(r"^description: .{40,}", front, re.M)

def test_purity_no_model_ids_in_any_skill():
    ids = _model_ids()
    assert ids, "expected provider model tables to parse"
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text()
        leaked = {m for m in ids if m in text}
        assert not leaked, f"{skill}: model ids leaked: {leaked}"

def test_purity_no_cli_invocations_anywhere():
    # Invocation strings live in provider packs only. No line ANYWHERE in the skill
    # (fenced or prose) may be command-shaped for a pack cli: first token equal to a
    # cli name, followed by whitespace and an argument. Prose mentions like
    # "(codex/opencode/agy)" or "via codex" do not match.
    clis = _pack_clis()
    assert clis, "expected pack manifests to declare cli names"
    for line in SKILL.read_text().splitlines():
        stripped = line.strip()
        parts = stripped.split(None, 1)
        if len(parts) == 2 and parts[0] in clis:
            raise AssertionError(f"command-shaped cli line leaked into skill: {stripped}")

def test_superpowers_operational_independence():
    # Normative rule: no operational dependency or invocation. The skill NAMES
    # superpowers and its workspace exactly once each — in the negative disclaimer.
    text = SKILL.read_text()
    assert "no superpowers dependency" in text.lower()
    assert text.count("scripts/sdd-workspace") == 1
    assert text.count(".superpowers/sdd") == 1

def test_root_resolution_stated():
    assert "grandparent" in SKILL.read_text()

def test_status_vocabulary_present():
    text = SKILL.read_text()
    for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
        assert status in text

def test_openai_yaml_disables_implicit_invocation():
    assert "allow_implicit_invocation: false" in YAML.read_text()

def test_reader_contract_protocol():
    text = READER.read_text()
    for token in ("STATUS:", "ANSWER:", "REPORT:", "NEEDS_CONTEXT", "Read-only",
                  "cannot write files"):
        assert token in text
```


- [ ] **Step 2: Run the new tests**

Run: `uv run --with pytest pytest tests/test_delegate_skill.py -q`
Expected: all pass if Tasks 1–2 landed as specified (these tests gate content, not order — if any fail, the skill content drifted from this plan; fix the content, not the test).

- [ ] **Step 3: Bump all three version references**

Set the version to `1.3.0` in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and the README `**Version:**` line. No other fields change.

- [ ] **Step 4: Verify sync and run everything**

Run: `grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json && grep -n '\*\*Version:\*\*' README.md && python3 scripts/validate-packs --root . && ./scripts/codex-smoke && uv run --with pytest pytest tests/ -q`
Expected: `1.3.0` in all three lines; gates exit 0; full suite passes (37+ cases).

- [ ] **Step 5: Commit**

```bash
git add tests/test_delegate_skill.py .claude-plugin/plugin.json .codex-plugin/plugin.json README.md
git commit -m "chore: delegate structural tests + bump to v1.3.0"
```

---

## Post-plan verification (controller, not a plan task)

Live smokes per spec §8, run by the controller after the branch is complete (they
exercise real CLIs and cannot be delegated as plan tasks):

- **Smoke A (read lane)**: one explore-question delegate against this repo, cheapest
  tier — verifies inference → announcement → dispatch → report gate (freshness +
  answers-the-task) → answer returned → lifecycle ledger events, and the
  clean-tree/porcelain doctrine.
- **Smoke B (write lane)**: one small write task "with review" in a throwaway repo —
  verifies clean-tree requirement, BASE/branch snapshot, the strengthened evidence
  gate (staged + untracked + HEAD-unchanged), reviewer dispatch with untracked content
  in the package, resume-channel fix loop, versioned re-review package, controller
  commit.
- **Smoke C (supervised)**: a batch of ≥3 small mechanical tasks in a throwaway repo —
  verifies the cycle formula and announcement, supervisor cycle management,
  supervisor-written lifecycle ledger lines (allocated-before-launch), and the
  controller's independent re-check before commit.

Findings that surface pack facts append to the usual verification logs. Merge to `main`
and tag only on the owner's explicit instruction.
