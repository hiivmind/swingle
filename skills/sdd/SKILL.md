---
name: swingle-sdd
description: >-
  Execute an implementation plan via subagent-driven development with
  external-CLI dispatch (codex/opencode/agy/grok/pi/claude). Use whenever executing a
  written plan with SDD — wraps superpowers:subagent-driven-development and
  applies the external-dispatch optimizations mechanically. Triggers: "run this
  plan with SDD", "/swingle-sdd", "/sdd", "execute the plan via subagents", the
  Standard Delivery Flow reaching its execute step.
---

# SDD with Provider Packs

**Controller**: identify your controller and read `<root>/controllers/<controller>.md`
(claude-code, codex, grok, opencode, pi, agy) before Step 0 — it maps skill-loading, native subagent
dispatch, task tracking, background jobs, and asset-root resolution. All paths below
are relative to the plugin tree root `<root>` (the directory containing `skills/`,
`controllers/`, `core/`, `providers/`).

This skill wraps **superpowers:subagent-driven-development**. Its process governs the
per-task loop, task briefs and review packages, statuses, two-verdict reviews, fix loops,
ledger, pre-flight scan, and final review. This skill replaces its dispatch mechanism with
the active provider pack or, when selected, controller-native subagents.

**Never dispatch from memory.** The documents below are read at Step 0, before the first
dispatch — not recalled. They change under you: packs are re-verified on every CLI version
bump, and tiering, roles, and dispatch templates move with them. A dispatch built from
remembered doctrine looks identical to a correct one and fails silently — a stale flag, a
superseded model id, a tier that no longer matches the role.

Read these plugin documents when their policy is needed:

- `<root>/core/playbook.md` — SDD process mapping, dispatch flavours, and controller gates
- `<root>/core/roles.md` — role, tier, and lane policy
- `<root>/core/liveness.md` — required background and stall protocol
- `<root>/core/safety-doctrine.md` — containment and controller-gate doctrine
- `<root>/core/verification-protocol.md` and `<root>/core/verification-log.md` — verification policy and history
- `<root>/providers/<id>/pack.md` (manifest) and the resolved registry body under `versions/` — validated provider behavior and canonical dispatch; `models.yaml` and `models.md` — model candidates (models.yaml is the table of record; models.md is narrative)

## Step 0 — Setup (once per session, before Task 1)

1. Use the controller adapter's skill-loading mechanism to invoke
   `superpowers:subagent-driven-development`, then follow its process except for its
   dispatch steps, which this skill overrides.
2. Run its `scripts/sdd-workspace`; copy the operating contracts into it from
   `<root>/contracts/`.
3. Check the ledger (`$WORKSPACE/progress.md`) — never re-dispatch a completed task.
4. Read `<root>/core/roles.md`, `<root>/core/playbook.md`,
   `<root>/core/safety-doctrine.md`, and `<root>/core/liveness.md`; determine the routing
   lever in effect: silent means “floor it”, “play it safe” moves implementers one tier up,
   and a provider or lane directive steers eligible work. The `native-subagents` lever
   uses the controller-native subagent mechanism; under Claude Code, “all Claude” is its
   alias; under Grok, “all Grok” is its alias.
4b. **Trust gate**: run `python3 <root>/scripts/validate-packs --root <root>` — refuse
   to proceed past a non-zero exit. THEN check `git -C <root> status --porcelain
   providers/` — any untracked or modified provider directory requires explicit user
   approval before its manifest or prose is used (git-tracked state is the trust anchor).
5. **Session gate — run the Step-0 pipeline** (where the controller can run shell;
   otherwise execute the same table below in prose):
   Branch for `native-subagents` immediately after manifest pre-validation; it bypasses
   config discovery/loading and provider detection. For an external branch, discover the
   first config found at `$SWINGLE_CONFIG` → `<project>/.swingle.json` →
   `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json` (schema:
   [docs/config.md](../../docs/config.md)). A set-but-unreadable `$SWINGLE_CONFIG` is a
   STOP. No file found is normal — omit `--config` below.
   `python3 <root>/scripts/validate-packs --step0 --root <root> --project <repo>
   --role "<the plan's first task role>" [--config <found-layer>]
   [--task-provider <id> | --lever native-subagents]`
   The script is the single implementation of: manifest pre-validation → native bypass
   branch (when the `native-subagents` lever is set: print-and-proceed native; nothing
   else runs) → config loading and gating (malformed-config STOP cases:
   [docs/config.md](../../docs/config.md)
   “Dispatch STOP Conditions”; ACTIVE = installed − disabled (− incompatible iff
   require-verified-version)) → provider detection (INSTALLED iff `command -v -- "<cli>"`
   succeeds for the manifest's validated cli; data-only manifests — never execute
   manifest strings as shell) → drift advisory → routing precedence
   (per-task/session directive → config lanes/default
   → codex-if-active → sole-active → ask) → model resolution (role → tier/lane per
   `core/roles.md` → the provider's layered `models.yaml` candidates) → readiness (the
   pack's bounded version+auth probe). Outcome contract:
   | Output | Meaning | Action |
   | --- | --- | --- |
   | exit 0 | pipeline clean; `provider:`/`ready:` lines name the route | proceed |
   | unprefixed finding | invalid manifest/config (implicit STOP) | halt; fix or surface |
   | `STOP: …` | invalid input (e.g. unknown role) | halt; fix or surface |
   | `ASK: …` | a decision only the user can make | put the named question to the user; never guess |
   | `CHANNEL: …` | provider/environment failure | step 10's channel rules |
   | `warning: …` (exit 0) | drift or strict-mode removals with a valid route | note **drift is in effect** (step 10 finding semantics unchanged) |
   | exit 0; `native-subagents: bypass external dispatch (no provider selected)` | native bypass | proceed with controller-native subagents, no provider/model resolution |
   A divergence between the script and this table is a bug adjudicated against the
   table.
   Re-run `--step0` before a task's first dispatch whenever any effective routing input
   changes: its per-task provider directive, its per-task native directive, or a lane
   whose config routing differs for that task.
7. **Tier and model**: role → (tier, lane) via `core/roles.md`. Tier levers are
   policy, never script inputs: silent = "floor it" (base tier); "play it safe" =
   one tier up (most-capable is the ceiling — say so and proceed) — resolve the
   roles-table row at the effective tier in the same lane. Resolve candidates with
   `scripts/validate-packs --resolve "<role>" <provider> --project <repo>` (layered
   models.yaml walk; found-but-malformed override or unreadable `$SWINGLE_MODELS` =
   STOP; no candidates → ask, naming the winning file). When no override layer exists
   at all, mention ONCE per session to run `swingle-setup`; never create user config
   uninvited.
8. **Pack-specific preflight (prose)**: before the FIRST dispatch to the routed
   provider, run any preflight its pack defines beyond the generic probe (e.g. a
   persisted-permission baseline check) — a miss is a STOP with the pack's fix
   section.
9. Also read the routed provider's `providers/<id>/log/` (monthly shards; read newest-first, all shards are evidence) and, if present,
   the user's local record at `${XDG_CONFIG_HOME:-~/.config}/swingle/verification/<id>.md`
   (read additively — both are evidence).
   Take the installed version from the CLI's **raw version-output token**, accepting it
   only when it full-matches the closed dotted-numeric grammar; a suffixed token is
   unparseable — never resolve on a numeric prefix. Resolve the provider BODY from the
   registry `providers/<id>/versions/`: exact key match → that file; between keys →
   nearest at-or-below; above the manifest's `verified-version` → the current file
   (`versions/<verified-version>.md`, silence — a newer release is not a defect); below
   the oldest key, or unparseable → the current file plus the corresponding advisory; the
   current file missing → STOP and surface (broken pack). The manifest (frontmatter)
   always comes from `pack.md`; each registry file's first line declares its evidence
   class (`> Verified:` round truth vs `> Distilled…:` assembled history) — weigh it.
   Version comparison and edge rules are in `core/verification-protocol.md` Recording.
   Guidance still applies additively on top of whichever body resolves.
   If an entry at or below the installed version
   carries an operating instruction covering the lane about to be dispatched, **act on
   it** — apply prompt- and dispatch-shape restrictions directly and state what changed;
   version pins and provider changes are **recommended to the user**, never performed
   silently (cross-provider moves remain a user question, per step 10). An instruction
   applies from its version forward until a later entry lifts it. No applicable
   instruction ⇒ say nothing — a newer release is not a defect.
10. **Failure classes**: channel failures (auth, model-not-found, startup stall) may
    advance to the NEXT candidate in the resolution order (same provider; max 3 total
    attempts per (task, role)); cross-provider moves are ALWAYS a user question. Ledger
    line per attempt:
    `model-attempt: task=<N> role=<role> provider=<id> model=<id> class=<channel|quality> outcome=<failed|ok>`
    — channel-failed (provider, model) pairs are excluded session-wide and rebuilt from
    the ledger after compaction; quality failures (BLOCKED, repeated review rejection)
    create no exclusion and NEVER auto-fall-back — escalate tier or adjudicate.
    **Channel failure while version drift is in effect** (step 6 warned installed ≠
    `verified-version`) is also a verification finding — the pack may be stale on this CLI
    version. **Recommend** (do not auto-file) recording it via the existing recording
    ladder and dedup in `core/verification-protocol.md` Recording (search existing
    `verification` issues → 👍 / comment / new), capturing plugin version, installed CLI
    version vs `verified-version`, the controller + its version, and the failure
    signature. Quality failures are excluded — they are not drift evidence.

## Dispatch overrides (replace the stock skill's dispatch steps)

For every external implementer, reviewer, final reviewer, and resumed fix, use the active
pack's canonical dispatch template (the resolved registry body) inside the self-reaping wrapper
(`core/liveness.md`). The adapter specifies how that background work is started and
observed in the current controller. Keep stdout in the per-task log and record the provider
session identifier for continuation.

For native-subagent routing, use the adapter's native subagent mechanism instead. The
controller still supplies the applicable contract, brief, scene, interface list, and report
path; provider routing and model resolution do not apply.

### Worktree dispatch

Levers: `"in a worktree"` runs the plan isolated; `"in my tree"` forces
session-tree dispatch; both in one request = STOP and ask. When the session
tree is dirty and no lever was given, OFFER this lane (one question — never a
silent switch). Prerequisite: the routed provider's record under the
`superpowers` config key, read directly from the USER-layer config file;
`installed: true` → proceed, otherwise one-line warning and ask (dispatch
without isolation, or run the swingle-setup probe first).

One branch per plan run: `swingle/sdd-<plan-run-id>`, where `<plan-run-id>` is
the plan's workspace directory name (the basename the wrapped skill's
`scripts/sdd-workspace` derives from the plan file) — the branch carries the
same run identity as the ledger. The FIRST task dispatch
appends this block (substituting the branch):

> Workspace isolation: your harness has the superpowers skill set installed.
> Before touching any file, use superpowers:using-git-worktrees to create an
> isolated worktree on a new branch named `<branch>`, and do ALL work there,
> following your normal process — committing as your skills direct. Do not
> modify the main checkout. Your report must state the branch name and the
> final commit SHA.

Every LATER task dispatch (and every fix-round resume) appends the
continuation form instead — the branch already exists:

> Workspace isolation: continue on the existing branch `<branch>` in its
> existing worktree (created by an earlier task via
> superpowers:using-git-worktrees — do not create a new worktree or branch).
> Do ALL work there, committing as your skills direct; do not modify the main
> checkout. Your report must state the final commit SHA.

Gates move to the session tree: after each dispatch, the session checkout's
HEAD and porcelain must be unchanged; the task's evidence is its commits on
the branch (report SHA verified present). In this lane implementer commits on
the branch ARE the deliverable — the controller-commits-after-gating rule
applies to LANDING only. Task review packages come from the branch
(`git diff` of the task's commit range); the final review targets the full
branch diff before landing. Landing is a controller act via
superpowers:finishing-a-development-branch. On NEEDS_CONTEXT/BLOCKED the
branch and worktree are retention; resume rides the pack's resume channel.
The wrapped skill's process (task loop, reviews, fix rounds, ledger) is
otherwise unchanged and unrestated.

**Implementer:** use the implement role and selected tier/lane. The prompt references the
implementer contract and task brief by path, states the scene and prior interfaces, and
requires the report path. Record BASE before dispatch; implementers do not commit
(session-tree dispatch only; in worktree dispatch, task commits land on the run branch
and the controller commits nothing until landing).

**Every dispatch prompt states the status vocabulary inline** — contracts move by path
(playbook E1), the four status tokens do not (E1a). Append verbatim: “End with a status
block whose first line is exactly one of: STATUS: DONE | DONE_WITH_CONCERNS |
NEEDS_CONTEXT | BLOCKED.” One line in the prompt buys conformance the contract citation
alone did not get at the cheapest tier; a missing block still means UNKNOWN, never DONE.

**Report transport:** honor the routed pack's `report-transport`. On `report-file` (the
default when the field is absent) the agent writes `task-N-report.md` itself. On
`captured-output` the provider cannot reliably write an agent-authored file to a workspace
path, so ask for NO file: the FULL report is the captured final message and the controller
saves it to the report path — on initial and resumed turns alike. Getting this wrong is
not cosmetic: on a `captured-output` provider a report-file request fails intermittently
while the exit code stays 0, so the report is simply missing and the reviewer silently
loses an input (see the provider verification logs).

**Task reviewer:** use the review role and selected tier/lane. Provide the task reviewer
contract, brief, report, review-package path, and global constraints verbatim. Say:
“review only, change nothing in the repo; writing your review file is allowed.” Apply an
enforced read-only lane where the pack provides one; otherwise obey
`core/safety-doctrine.md`.

**Design / plan reviewer:** when the review target is an artifact that has not been
implemented yet — the plan itself, a spec it derives from, an architecture document —
dispatch the final/design reviewer row with `design-reviewer-contract.md`, not the task
reviewer contract. This is the shape of a pre-flight plan review and of any review the
caller frames as design-stage; `specs/*-design.md` and `plans/*.md` are the usual paths.
The task reviewer contract is built around a diff, so pointing it at an unimplemented
design yields findings that restate the design's absence. Say explicitly in the prompt:
“this is a design review — the work is not yet implemented; judge whether it would be
correct if built, and do not check whether code implements it.”

**Fix / NEEDS_CONTEXT:** do not cold-dispatch. Resume the implementer through the active
pack's validated continuation mechanism with the answers or findings list, then re-review.

**Re-reviews (default: same thread):** resume the ORIGINAL reviewer's session with the fix
summary and the updated review package — the reviewer keeps its own findings in context, so
the re-review verifies fixes instead of re-deriving the review, and verdict continuity is
explicit ("your Important finding is fixed" beats a cold reviewer guessing severity anew).
Capture the reviewer's session id at first dispatch (per the pack's `session-source`) and
record it in the ledger beside the task. If the resume channel fails or the pack lacks one,
fall back to a cold re-review dispatch that attaches the prior review verbatim plus the fix
report. The same applies to multi-round final reviews.

## Flavour choice (be explicit which “dispatch” you mean)

- **Inline** (no dispatch): task below the orchestration floor — a single-file mechanical
  fix the controller finishes in roughly 2k tokens. Batch several such tasks into one pack
  dispatch rather than paying per-task cold starts.
- **Pack dispatch** (default): external provider dispatch through the active pack.
- **Supervised pack dispatch** (long plans, more than about eight tasks): one cheap native
  subagent (see adapter) per task cycle manages pack dispatch, liveness, the mechanical
  gate, and reviewer dispatch, returning a concise report with evidence paths.
  Adjudication and commits remain in the main thread.
- **Sub-dispatch** (native subagent does the work itself): the `native-subagents` lever.

For the economics and dispatch mechanics, read `<root>/core/playbook.md`; the task
loop and controller process live in the invoked superpowers skill, not the playbook.

## Controller rules (the hard gate — never offloaded)

- Read only the status block, `git diff --stat`, and reviewer verdicts by default. Read a
  full diff only for findings, warning items, critical paths, or report/stat disagreement.
- On DONE, re-run the covering tests, commit only after the controller's gate, then create
  the review package from BASE to HEAD.
- Record completed tasks and session identifiers in the ledger. Never parallel
  implementers or re-dispatch a ledgered task.
- Keep adjudication in the controller: statuses, cannot-verify-from-diff items, and plan
  contradictions go to the human when needed.
- Perform the final whole-branch review with the most-capable review tier; the wrapped
  skill's final-review policy governs the fix cadence.
