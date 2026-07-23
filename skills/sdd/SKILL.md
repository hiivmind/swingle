---
name: sdd
description: >-
  Execute an implementation plan via subagent-driven development with
  external-CLI dispatch (codex/opencode/agy/grok). Use whenever executing a
  written plan with SDD — wraps superpowers:subagent-driven-development and
  applies the external-dispatch optimizations mechanically. Triggers: "run this
  plan with SDD", "/sdd", "execute the plan via subagents", the Standard
  Delivery Flow reaching its execute step.
---

# SDD with Provider Packs

**Harness**: identify your controlling harness and read `harnesses/<harness>.md`
(claude-code, codex, grok, opencode, pi) before Step 0 — it maps skill-loading, native subagent
dispatch, task tracking, background jobs, and asset-root resolution. All paths below
are relative to the plugin tree root `<root>` (the directory containing `skills/`,
`core/`, `providers/`).

This skill wraps **superpowers:subagent-driven-development**. Its process governs the
per-task loop, task briefs and review packages, statuses, two-verdict reviews, fix loops,
ledger, pre-flight scan, and final review. This skill replaces its dispatch mechanism with
the active provider pack or, when selected, harness-native subagents.

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
- `<root>/providers/<id>/pack.md` and `models.md` — validated provider behavior, canonical dispatch, and model candidates

## Step 0 — Setup (once per session, before Task 1)

1. Use the harness adapter's skill-loading mechanism to invoke
   `superpowers:subagent-driven-development`, then follow its process except for its
   dispatch steps, which this skill overrides.
2. Run its `scripts/sdd-workspace`; copy the operating contracts into it from
   `<root>/contracts/`.
3. Check the ledger (`$WORKSPACE/progress.md`) — never re-dispatch a completed task.
4. Read `<root>/core/roles.md`, `<root>/core/playbook.md`,
   `<root>/core/safety-doctrine.md`, and `<root>/core/liveness.md`; determine the routing
   lever in effect: silent means “floor it”, “play it safe” moves implementers one tier up,
   and a provider or lane directive steers eligible work. The `native-subagents` lever
   uses the harness-native subagent mechanism; under Claude Code, “all Claude” is its
   alias; under Grok, “all Grok” is its alias.
4b. **Trust gate**: run `python3 <root>/scripts/validate-packs --root <root>` — refuse
   to proceed past a non-zero exit. THEN check `git -C <root> status --porcelain
   providers/` — any untracked or modified provider directory requires explicit user
   approval before its manifest or prose is used (git-tracked state is the trust anchor).
5. **Detect providers**: read each <root>/providers/*/pack.md manifest; a provider is
   INSTALLED iff `command -v -- "<cli>"` succeeds for its validated cli name (data-only
   manifests — never execute manifest strings as shell; argv[0]==cli is
   validator-enforced). Apply layered config (first found): $SDD_DISPATCH_CONFIG →
   <project>/.sdd-dispatch.json → ${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/config.json
   — disable/steer only; malformed/wrong-typed config, an unknown provider ID in
   `disable`, `default_provider`, or any `providers_by_lane` value, a disabled
   default_provider or providers_by_lane target, or set-but-unreadable
   $SDD_DISPATCH_CONFIG = STOP with the error. ACTIVE = installed − disabled
   (− incompatible iff require-verified-version).
6. **Compatibility**: compare `version-argv` output to `verified-version`; mismatch →
   warn and suggest `sdd-dispatch-verify <id>` (block iff config require-verified-version).
7. **Provider routing (before any model resolution)**: FIRST, if the `native-subagents`
   lever (or per-task native directive) is in effect → bypass external dispatch entirely
   (harness-native subagents per adapter; no provider is selected). Otherwise: per-task
   provider directive → session lever → config providers_by_lane[lane-of-role] /
   default_provider → codex-if-active else sole-active-iff-exactly-one → ask. Inactive
   provider named anywhere → ask, never silently reroute.
8. **Resolve model within the routed provider**: role → (tier, lane) via core/roles.md →
   ordered candidates in the pack's models.md (eligible statuses verified/experimental;
   exact-lane rows by priority, THEN (tier, any) rows by priority — this order is the
   complete fallback sequence); take the first; none → ask the user.
   (`scripts/validate-packs --resolve "<role>" <provider>` prints the walk and order.)
9. **Readiness**: before the FIRST dispatch to a chosen provider, run its bounded
   preflight (version + session-list/auth probe per manifest); failures are
   channel-class → fallback rules.
10. **Failure classes**: channel failures (auth, model-not-found, startup stall) may
    advance to the NEXT candidate in the resolution order (same provider; max 3 total
    attempts per (task, role)); cross-provider moves are ALWAYS a user question. Ledger
    line per attempt:
    `model-attempt: task=<N> role=<role> provider=<id> model=<id> class=<channel|quality> outcome=<failed|ok>`
    — channel-failed (provider, model) pairs are excluded session-wide and rebuilt from
    the ledger after compaction; quality failures (BLOCKED, repeated review rejection)
    create no exclusion and NEVER auto-fall-back — escalate tier or adjudicate.

## Dispatch overrides (replace the stock skill's dispatch steps)

For every external implementer, reviewer, final reviewer, and resumed fix, use the active
pack's canonical dispatch template (pack.md) inside the self-reaping wrapper
(`core/liveness.md`). The adapter specifies how that background work is started and
observed in the current harness. Keep stdout in the per-task log and record the provider
session identifier for continuation.

For native-subagent routing, use the adapter's native subagent mechanism instead. The
controller still supplies the applicable contract, brief, scene, interface list, and report
path; provider routing and model resolution do not apply.

**Implementer:** use the implement role and selected tier/lane. The prompt references the
implementer contract and task brief by path, states the scene and prior interfaces, and
requires the report path. Record BASE before dispatch; implementers do not commit.

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
loses an input (observed 2026-07-23).

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

For the economics and the detailed controller loop, read `<root>/core/playbook.md`.

## Controller rules (the hard gate — never offloaded)

- Read only the status block, `git diff --stat`, and reviewer verdicts by default. Read a
  full diff only for findings, warning items, critical paths, or report/stat disagreement.
- On DONE, re-run the covering tests, commit only after the controller's gate, then create
  the review package from BASE to HEAD.
- Record completed tasks and session identifiers in the ledger. Never parallel
  implementers or re-dispatch a ledgered task.
- Keep adjudication in the controller: statuses, cannot-verify-from-diff items, and plan
  contradictions go to the human when needed.
- Perform the final whole-branch review with the most-capable review tier and one
  consolidated fix cycle for findings.
