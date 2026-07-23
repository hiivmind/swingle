# `delegate` Skill Design — sdd-dispatch v1.3.0

> Approved 2026-07-23. Direct one-off delegation to external CLIs through the provider
> packs — dispatch, liveness, safety gates, and resume — WITHOUT the SDD plan/brief/
> two-verdict machinery. The sibling of the `sdd` skill: same engine, no plan.

## Purpose and boundary

`sdd` executes a written implementation plan: task briefs, two-verdict reviews, fix
loops, a progress ledger keyed to plan tasks, and a final whole-branch review. `delegate`
covers everything below that: a single task (or a small batch) the controller wants done
by a cheap external agent right now — "port this file", "find where X is configured",
"summarise these release notes", "review this diff" — with the full safety doctrine but
none of the plan-execution ceremony.

Boundary rule: if the work arrives as a plan file with numbered tasks, use `sdd`. If it
arrives as a request in conversation, `delegate` handles it. `delegate` never reads or
writes `.superpowers/sdd/` and has **no superpowers dependency**.

## 1. Invocation and role inference

Invocation: `delegate <task>` (skill argument or conversational request), with optional
levers anywhere in the request:

- **Provider**: "via agy" / "via codex" / "via opencode" — same semantics as `sdd`.
- **Tier**: "floor it" (default when silent), "play it safe" (one tier up), or an
  explicit model id (must still resolve inside the routed provider's models.md).
- **Review**: "with review" — adds the opt-in reviewer dispatch (§4).
- **Lane pin**: "read-only" — forces the review/read lane even if the task text sounds
  writable; the dispatched prompt then carries the read-only instruction and the
  clean-tree/diff-after check treats ANY diff as a violation.
- **Native**: the `native-subagents` lever (or "all Claude" under Claude Code) bypasses
  external dispatch entirely, per the harness adapter.

**Role inference (hybrid).** The controller classifies the task against the existing
`core/roles.md` role table — transcription implement, adaptation implement, explore,
research/synthesis, review — and **announces the resolved role → tier → lane →
provider → model — plus the supervision decision (§5) — in one line before
dispatching**. That announcement is the caller's override point. When a task genuinely straddles lanes (e.g. "look into X and fix it"),
ask ONE question (investigate-only vs investigate-and-fix) before dispatching; never
guess a write when a read was plausible. No new role vocabulary is introduced: the
roles.md table is the authority, exactly as for `sdd`.

**Batching.** Several near-identical mechanical tasks go into ONE dispatch (playbook
triviality-floor doctrine — don't pay a cold start per trivial item). Heterogeneous
tasks run as sequential dispatches. Never parallel write-lane dispatches; parallel
read-lane dispatches are permitted (they cannot conflict).

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
9. **Workspace**: create `.sdd-dispatch/delegate/` (§6) and copy the operating contracts
   from `<root>/contracts/` into it once per session.

Explicitly absent: superpowers:subagent-driven-development invocation,
`scripts/sdd-workspace`, plan reading, pre-flight plan scan, task briefs.

## 3. Dispatch cycle

Per dispatch, numbered `NNN` (001, 002, … within the workspace ledger):

1. Write the prompt to `.sdd-dispatch/delegate/NNN-prompt.md`. Prompt contents: contract
   path (implementer or task-reviewer contract, matching the lane), the task text
   verbatim, scene (one line: repo, branch, relevant paths), the report-file path
   (`NNN-report.md`), and the report contract — status ≤15 lines back, detail in the
   report file. Statuses reuse the SDD vocabulary: DONE / DONE_WITH_CONCERNS /
   NEEDS_CONTEXT / BLOCKED.
2. Write-lane only: record BASE (= current HEAD) and require a clean tree (or explicit
   user acknowledgement of the dirty state) before dispatching.
3. Dispatch with the active pack's canonical template inside the self-reaping wrapper
   (`core/liveness.md`), stdout to `NNN-dispatch.log`, observed per the harness adapter
   (marker file, never foreground stdout). Record the provider session id
   (pack `session-source`) in the ledger at dispatch time.
4. Read back ONLY the status block and (write lane) `git diff --stat`. Exit codes are
   never evidence of work: the gate is diff-after (write lane) or report-file-exists
   with responsive content (read lane).
5. **NEEDS_CONTEXT / follow-ups / fixes ride the resume channel** — the pack's validated
   continuation mechanism against the recorded session id. Cold re-dispatch only when
   the resume channel fails, with the prior report attached.
6. **Failure classes**: channel failures (auth, model-not-found, startup stall) advance
   to the next candidate in the resolution order (same provider, max 3 attempts total);
   cross-provider moves are always a user question. Quality failures never auto-fallback
   — escalate tier or adjudicate. Every attempt appends a ledger line:
   `model-attempt: dispatch=NNN role=<role> provider=<id> model=<id> class=<channel|quality> outcome=<failed|ok>`.

## 4. Gate and opt-in review

**Controller hard gate — always, both lanes:**

- Verify on disk, never from prose: diff-after for write lane; report existence and
  responsiveness for read lane.
- Read-intent dispatches (explore, research, review): clean tree before, `git status
  --porcelain` after — any diff is a doctrine violation to surface, not silently reset.
- Write lane: re-run the covering tests named in the task (or the project's default
  gate) in the controller, not trusting the agent's claimed results.
- **The controller commits** — and only when the user asked for a commit; otherwise
  leave the working tree for the user with a diff --stat summary. External agents never
  commit (the agy pack's deny-rules enforce this mechanically; elsewhere it is prompt
  doctrine + gate).

**Opt-in review ("with review").** One external reviewer dispatch before any commit:
review role, standard tier (scaled up if the diff is large/risky), routed through the
review lane, task-reviewer contract, given the task text, the report, and a
`review-package`-style diff file (BASE→current, `-U10`, generated by the controller).
Critical/Important findings ride the implementer's resume channel; the re-review resumes
the ORIGINAL reviewer's thread with the fix summary — the same rules as `sdd`. One
fix/re-review round by default; further rounds are a user decision.

## 5. Supervised delegate (auto by cost, announced)

The playbook's supervised-pack-dispatch flavour, applied to delegate: one cheap
harness-native subagent (per the harness adapter) runs the mechanical dispatch cycle —
prompt-file writing, pack dispatch inside the liveness wrapper, marker watching, the
mechanical gate reads (status block, `git diff --stat`, report existence), reviewer
dispatch when "with review", and verdict collection — and returns ONE concise report
with evidence *paths* (prompt, log, report, review files) plus the ledger lines it
appended.

**Trigger — automatic by cycle count, always announced, lever-overridable:**

- 1–2 dispatch cycles → controller orchestrates directly (a supervisor would cost more
  than it saves).
- ≥3 cycles implied by the invocation (a heterogeneous batch; or a batch "with review",
  where each item's review doubles its cycles) → supervised, announced in the
  pre-dispatch line (e.g. `supervised: yes — 4 cycles`).
- Explicit "supervised" / "unsupervised" in the request always overrides the automatic
  rule. `native-subagents` routing is orthogonal: it replaces the EXTERNAL dispatch, at
  which point supervision is moot (the native subagent IS the worker).

**Non-negotiable doctrine (unchanged from the playbook):** adjudication and commits stay
in the main thread. The supervisor's "all green" is evidence to check, not a gate
result — the controller re-reads the verdict lines, spot-checks `git diff --stat`
against the report, re-runs the covering tests for write-lane work, and performs any
commit itself. The supervisor writes ledger and `model-attempt:` lines as it goes, so a
killed supervisor loses no state.

**Escalation paths out of the supervisor:** NEEDS_CONTEXT, BLOCKED, quality failures,
and lane-straddle ambiguity are returned in the supervisor's report, never resolved by
it. The controller answers NEEDS_CONTEXT through the pack's resume channel directly
(the session id is already in the ledger) or hands the answer to a fresh supervisor
cycle for the remaining batch; quality failures follow §3's no-auto-fallback rule.

## 6. Workspace and ledger-lite

`.sdd-dispatch/delegate/` at the repo root, git-ignored (on first use, if the repo's
.gitignore lacks an entry, add `.sdd-dispatch/` and tell the user). Supervised runs use
the same workspace and numbering — the supervisor appends to the same ledger. Contents:

```
.sdd-dispatch/delegate/
  implementer-contract.md      # copied once per session from <root>/contracts/
  task-reviewer-contract.md
  ledger.md                    # append-only, one line per dispatch + model-attempt lines
  NNN-prompt.md
  NNN-dispatch.log
  NNN-report.md
  NNN-review.md                # only when "with review"
```

Ledger line per completed dispatch:

```
NNN: <role> provider=<id> model=<id> session=<session-id> status=<DONE|...> outcome=<committed <sha7>|diff-left|report|blocked>
```

The ledger is the compaction-proof resume map: after compaction (or days later, if the
CLI retains sessions) "ask that agent a follow-up" resolves through the recorded session
id. Non-repo working directories (pure research questions with no repo): fall back to
the harness session scratchpad for artifacts and note in the reply that no durable
ledger exists.

## 7. Deliverables

| Change | File(s) |
| --- | --- |
| New skill | `skills/delegate/SKILL.md` |
| Codex metadata | `skills/delegate/agents/openai.yaml` (implicit invocation FALSE — it writes) |
| Flavour table entry | `core/playbook.md` — fifth row: one-off pack dispatch, no plan |
| Docs | `README.md` skills table + a short `delegate` section |
| Version → **1.3.0** | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, README `**Version:**` |

Untouched: `core/` doctrine files (except the playbook row), `providers/`, `contracts/`,
`skills/sdd/` — zero pack changes. The delegate skill reads the shared harness adapters
at `skills/sdd/harnesses/<harness>.md`; if a future round promotes those to a shared
location, both skills move together.

Purity boundary holds: `skills/delegate/SKILL.md` may name providers but carries no
model ids or invocation strings — those stay in the packs.

## 8. Testing

- Static gates: `python3 scripts/validate-packs --root .` and `./scripts/codex-smoke`
  (extend codex-smoke's layout expectations to include `skills/delegate/` if it
  enumerates skills).
- Live smoke A (read lane): one explore-question delegate against this repo on the
  cheapest tier — verifies inference→announcement→dispatch→report gate→ledger, and the
  clean-tree/diff-after doctrine.
- Live smoke B (write lane): one small write task "with review" in a throwaway repo —
  verifies BASE recording, diff gate, reviewer dispatch, resume-channel fix loop, and
  controller commit.
- Live smoke C (supervised): a batch of ≥3 small mechanical tasks in a throwaway repo —
  verifies the automatic trigger and announcement, supervisor cycle management, ledger
  lines written by the supervisor, and the controller's independent re-check of the
  supervisor's "all green" before commit.
- All smokes run on an active pack lane (agy or codex) and their findings append to the
  usual verification logs if they surface pack facts.

## Out of scope (backlog)

- Cross-repo delegate (dispatching into a different repo than the CWD).
- A shared `skills/_shared/harnesses/` promotion for the adapters.
