# Delegate Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `delegate` skill to the sdd-dispatch plugin: direct one-off dispatch of a task (or small batch) to an external CLI through the provider packs, without the SDD plan-execution machinery.

**Architecture:** One new skill directory (`skills/delegate/`) that reuses the existing engine untouched — `core/` doctrine, `providers/` packs, `contracts/`, and the shared harness adapters at `skills/sdd/harnesses/`. Plus a playbook flavour-table row, README updates, and a version bump to 1.3.0.

**Tech Stack:** Markdown skill files; bash/python3 gates (`scripts/validate-packs`, `scripts/codex-smoke`); pytest for the validator suite.

**Spec:** `docs/superpowers/specs/2026-07-23-delegate-skill-design.md` — the authority for all behavior described below.

## Global Constraints

- Work on branch `feature/delegate-skill`; never commit to `main`.
- Before EVERY commit: `python3 scripts/validate-packs --root .` AND `./scripts/codex-smoke` must exit 0.
- Purity boundary: `skills/delegate/SKILL.md` may name providers (codex/opencode/agy) but must contain NO model ids and NO invocation strings — those live only in `providers/<id>/`.
- Version 1.3.0 must appear in exactly three places, in sync: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, README `**Version:**` line.
- `skills/delegate/agents/openai.yaml` sets `allow_implicit_invocation: false` (the skill writes).
- No superpowers dependency anywhere in the delegate skill: it must not invoke superpowers skills, run `scripts/sdd-workspace`, or reference `.superpowers/sdd/`.
- Delegate workspace path is exactly `.sdd-dispatch/delegate/` at the repo root, git-ignored.
- Statuses are exactly: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED.
- Supervision trigger: automatic at ≥3 implied dispatch cycles; announced; overridable with explicit "supervised"/"unsupervised".

---

### Task 1: `skills/delegate/SKILL.md` + Codex metadata + codex-smoke check

**Files:**
- Create: `skills/delegate/SKILL.md`
- Create: `skills/delegate/agents/openai.yaml`
- Modify: `scripts/codex-smoke` (add existence checks for the two new files)

**Interfaces:**
- Consumes: `core/roles.md` role table, `core/playbook.md`, `core/liveness.md`, `core/safety-doctrine.md`, `providers/<id>/pack.md` + `models.md`, `contracts/implementer-contract.md`, `contracts/task-reviewer-contract.md`, `skills/sdd/harnesses/<harness>.md`, `scripts/validate-packs`.
- Produces: the `delegate` skill (referenced by name in Task 2's README and playbook edits).

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
```

- [ ] **Step 2: Run codex-smoke to verify it fails**

Run: `./scripts/codex-smoke`
Expected: `FAIL: skills/delegate/SKILL.md exists`, `FAIL: skills/delegate/agents/openai.yaml exists`, exit code 1.

- [ ] **Step 3: Create `skills/delegate/SKILL.md`**

Exact content:

````markdown
---
name: delegate
description: Directly delegate a one-off task or small batch to an external CLI (codex/opencode/agy) through validated provider packs — role inference, model tiering, liveness, safety gates, and session resume — without a written implementation plan. Use for ad-hoc implement/explore/research/review requests; use the sdd skill when work arrives as a plan file with numbered tasks.
---

# Delegate — Direct One-Off Dispatch

**Harness**: identify your controlling harness and read
`<root>/skills/sdd/harnesses/<harness>.md` (claude-code, codex) before setup — it maps
skill-loading, native subagent dispatch, background jobs, and asset-root resolution.
`<root>` is this skill directory's grandparent (the directory containing `skills/`,
`core/`, `providers/`, `contracts/`).

**Boundary**: work arriving as a plan file with numbered tasks → use the `sdd` skill.
Work arriving as a conversational request → this skill. This skill has **no superpowers
dependency**: it never invokes superpowers skills, never runs `scripts/sdd-workspace`,
and never reads or writes `.superpowers/sdd/`.

Read these plugin documents when their policy is needed:

- `<root>/core/roles.md` — the role → tier → lane table (the classification authority)
- `<root>/core/playbook.md` — dispatch flavours, economics, and controller gates
- `<root>/core/liveness.md` — required background and stall protocol
- `<root>/core/safety-doctrine.md` — containment and controller-gate doctrine
- `<root>/providers/<id>/pack.md` and `models.md` — validated provider behavior,
  canonical dispatch, and model candidates

## Levers (parsed from anywhere in the request)

- **Provider**: "via agy" / "via codex" / "via opencode".
- **Tier**: "floor it" (default when silent) = cheapest model clearing the role's bar;
  "play it safe" = one tier up; an explicit model id must still resolve inside the
  routed provider's models.md.
- **Review**: "with review" — adds the opt-in reviewer dispatch (see Gate).
- **Lane pin**: "read-only" — forces the review/read lane regardless of task wording;
  the dispatched prompt carries the read-only instruction and ANY resulting diff is a
  doctrine violation to surface.
- **Supervision**: "supervised" / "unsupervised" — overrides the automatic trigger.
- **Native**: the `native-subagents` lever ("all Claude" under Claude Code) bypasses
  external dispatch entirely per the harness adapter; provider routing and model
  resolution do not apply, and supervision is moot (the native subagent IS the worker).

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
8. **Workspace**: create `.sdd-dispatch/delegate/` at the repo root; if the repo's
   .gitignore lacks an entry, add `.sdd-dispatch/` and tell the user. Copy
   `<root>/contracts/implementer-contract.md` and
   `<root>/contracts/task-reviewer-contract.md` into it once per session. In a non-repo
   working directory, fall back to the harness session scratchpad and note in the reply
   that no durable ledger exists.

## Role inference and the announcement line

Classify the task against the `core/roles.md` table — transcription implement,
adaptation implement, read-only explore, research/synthesis, review. Then announce, in
ONE line before dispatching:

```
delegate: role=<role> tier=<tier> lane=<lane> provider=<id> model=<model> supervised=<yes: N cycles|no>[ review=yes]
```

The announcement is the caller's override point. When a task genuinely straddles lanes
("look into X and fix it"), ask ONE question (investigate-only vs investigate-and-fix)
before dispatching — never guess a write when a read was plausible.

**Batching**: several near-identical mechanical tasks go into ONE dispatch (the
playbook's triviality-floor doctrine). Heterogeneous tasks run as sequential dispatches.
Never parallel write-lane dispatches; parallel read-lane dispatches are permitted.

## Dispatch cycle

Each dispatch gets the next number `NNN` (001, 002, …) from the workspace ledger.

1. Write the prompt to `.sdd-dispatch/delegate/NNN-prompt.md`: contract path (implementer
   or task-reviewer contract, matching the lane), the task text verbatim, scene (one
   line: repo, branch, relevant paths), the report-file path (`NNN-report.md`), and the
   report contract — status ≤15 lines back (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT /
   BLOCKED), detail in the report file.
2. Write lane only: record BASE (= current HEAD) and require a clean tree (or explicit
   user acknowledgement of the dirty state) before dispatching.
3. Dispatch with the active pack's canonical template inside the self-reaping wrapper
   (`core/liveness.md`), stdout to `NNN-dispatch.log`, observed per the harness adapter
   (marker file — never foreground stdout). Record the provider session id (pack
   `session-source`) in the ledger at dispatch time.
4. Read back ONLY the status block and (write lane) `git diff --stat`. **Exit codes are
   never evidence of work**: the gate is diff-after (write lane) or
   report-file-exists-with-responsive-content (read lane).
5. **NEEDS_CONTEXT, follow-ups, and fixes ride the resume channel** — the pack's
   validated continuation mechanism against the recorded session id. Cold re-dispatch
   only when the resume channel fails, with the prior report attached.
6. **Failure classes**: channel failures (auth, model-not-found, startup stall) advance
   to the next candidate in the resolution order (same provider, max 3 attempts total
   per dispatch); cross-provider moves are always a user question. Quality failures
   never auto-fallback — escalate tier or adjudicate. Every attempt appends:
   `model-attempt: dispatch=NNN role=<role> provider=<id> model=<id> class=<channel|quality> outcome=<failed|ok>`.

## Gate and opt-in review

**Controller hard gate — always, both lanes:**

- Verify on disk, never from prose: diff-after for the write lane; report existence and
  responsiveness for the read lane.
- Read-intent dispatches: clean tree before, `git status --porcelain` after — any diff
  is a doctrine violation to surface, not silently reset.
- Write lane: the controller re-runs the covering tests named in the task (or the
  project's default gate) itself, never trusting the agent's claimed results.
- **The controller commits** — and only when the user asked for a commit; otherwise
  leave the working tree for the user with a `git diff --stat` summary. External agents
  never commit.

**Opt-in review ("with review")**: one external reviewer dispatch before any commit —
review role, standard tier (scaled up for large/risky diffs), review lane, task-reviewer
contract, given the task text, the report, and a diff file (BASE→current, commit list +
stat + `-U10`, generated by the controller into `NNN-review-package.md`; reviewer output
to `NNN-review.md`). Critical/Important findings ride the implementer's resume channel;
the re-review resumes the ORIGINAL reviewer's thread with the fix summary. One
fix/re-review round by default; further rounds are a user decision.

## Supervised delegate (auto by cost, announced)

One cheap harness-native subagent (per the harness adapter) runs the mechanical cycle —
prompt files, pack dispatch inside the liveness wrapper, marker watching, mechanical
gate reads (status block, `git diff --stat`, report existence), reviewer dispatch when
"with review", verdict collection — and returns ONE concise report with evidence paths
plus the ledger lines it appended.

**Trigger**: 1–2 implied dispatch cycles → the controller orchestrates directly.
≥3 cycles (a heterogeneous batch, or a batch "with review" — each item's review doubles
its cycles) → supervised, announced in the pre-dispatch line. An explicit "supervised" /
"unsupervised" lever always overrides.

**Doctrine (non-negotiable)**: adjudication and commits stay in the main thread. The
supervisor's "all green" is evidence to check — the controller re-reads the verdict
lines, spot-checks `git diff --stat` against the report, re-runs covering tests for
write-lane work, and performs any commit itself. The supervisor writes ledger and
`model-attempt:` lines as it goes, so a killed supervisor loses no state.

**Escalation**: NEEDS_CONTEXT, BLOCKED, quality failures, and lane-straddle ambiguity
are returned in the supervisor's report, never resolved by it. The controller answers
NEEDS_CONTEXT through the pack's resume channel directly (session id is in the ledger)
or hands the answer to a fresh supervisor cycle for the remaining batch.

## Workspace and ledger

```
.sdd-dispatch/delegate/
  implementer-contract.md      # copied once per session from <root>/contracts/
  task-reviewer-contract.md
  ledger.md                    # append-only: dispatch lines + model-attempt lines
  NNN-prompt.md
  NNN-dispatch.log
  NNN-report.md
  NNN-review-package.md        # only when "with review"
  NNN-review.md                # only when "with review"
```

Ledger line per completed dispatch:

```
NNN: <role> provider=<id> model=<id> session=<session-id> status=<DONE|...> outcome=<committed <sha7>|diff-left|report|blocked>
```

The ledger is the compaction-proof resume map: after compaction — or days later, if the
CLI retains sessions — a follow-up to a prior dispatch resolves through its recorded
session id. Never re-dispatch work the ledger records as complete.
````

- [ ] **Step 4: Create `skills/delegate/agents/openai.yaml`**

Exact content:

```yaml
interface:
  display_name: "Delegate to External CLI"
  short_description: "Directly delegate a one-off task or small batch to an external CLI (codex/opencode/agy) through validated provider packs, without a written implementation plan."
  default_prompt: "Delegate this task with the delegate skill."

policy:
  allow_implicit_invocation: false
```

- [ ] **Step 5: Run the gates to verify they pass**

Run: `./scripts/codex-smoke && python3 scripts/validate-packs --root .`
Expected: all PASS lines including the two new checks; exit 0.

- [ ] **Step 6: Purity check**

Run: `grep -nE 'gemini|gpt-5|--model|--print-timeout|-p "' skills/delegate/SKILL.md; echo "exit=$?"`
Expected: no matches, `exit=1` (no model ids or invocation strings in the skill).

- [ ] **Step 7: Commit**

```bash
git add skills/delegate/ scripts/codex-smoke
git commit -m "feat: delegate skill — direct one-off pack dispatch, no plan machinery"
```

---

### Task 2: Playbook flavour row + README

**Files:**
- Modify: `core/playbook.md` (flavour table, ~line 58–64)
- Modify: `README.md` (Layout block, Skills table, new section)

**Interfaces:**
- Consumes: the `delegate` skill name and behavior from Task 1.
- Produces: nothing downstream (docs only; Task 3 bumps versions).

- [ ] **Step 1: Add the flavour-table row to `core/playbook.md`**

In the "Dispatch flavours & economics" table, insert after the **Supervised pack dispatch** row:

```markdown
| **Delegate** (one-off pack dispatch, no plan — the `delegate` skill) | ~1–2k/dispatch | orchestration only | task cost | ad-hoc tasks or small batches arriving in conversation, not as a plan; auto-supervised at ≥3 cycles |
```

- [ ] **Step 2: Update the README Layout block and Skills table**

In the `## Layout` code block, insert after the `skills/sdd/` line:

```
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
```

In the `## Skills` table, insert after the `sdd` row:

```markdown
| `delegate` | Directly dispatch a one-off task or small batch through the provider packs — no plan required |
```

- [ ] **Step 3: Add the README `delegate` section**

Insert after the `## Skills` table:

```markdown
## Direct delegation

`delegate <task>` dispatches a single task (or small batch) to an external CLI with the
full pack doctrine — role inference from `core/roles.md`, model tiering, liveness,
diff-after gates, controller commits, and session resume — but none of the SDD
plan-execution ceremony. Levers: `via <provider>`, `floor it` / `play it safe` /
explicit model, `with review`, `read-only`, `supervised` / `unsupervised`. Batches
implying ≥3 dispatch cycles run supervised automatically (announced). Artifacts and the
resume ledger live in `.sdd-dispatch/delegate/` (git-ignored). If the work arrives as a
plan file with numbered tasks, use the `sdd` skill instead.
```

- [ ] **Step 4: Run the gates**

Run: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`
Expected: exit 0. (Version check still passes — README `**Version:**` unchanged in this task.)

- [ ] **Step 5: Commit**

```bash
git add core/playbook.md README.md
git commit -m "docs: delegate flavour row + README section"
```

---

### Task 3: Version bump to 1.3.0 + full test suite

**Files:**
- Modify: `.claude-plugin/plugin.json` (`"version": "1.2.5"` → `"1.3.0"`)
- Modify: `.codex-plugin/plugin.json` (`"version": "1.2.5"` → `"1.3.0"`)
- Modify: `README.md` (`**Version:** 1.2.5` → `**Version:** 1.3.0`)

**Interfaces:**
- Consumes: Tasks 1–2 complete.
- Produces: release-ready branch state.

- [ ] **Step 1: Bump all three version references**

Set the version to `1.3.0` in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and the README `**Version:**` line. No other fields change.

- [ ] **Step 2: Verify sync**

Run: `grep -n '"version"' .claude-plugin/plugin.json .codex-plugin/plugin.json && grep -n '\*\*Version:\*\*' README.md`
Expected: `1.3.0` in all three lines.

- [ ] **Step 3: Run the full gate + test suite**

Run: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && uv run --with pytest pytest tests/ -q`
Expected: gates exit 0; all pytest cases pass (31+).

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json .codex-plugin/plugin.json README.md
git commit -m "chore: bump to v1.3.0 — delegate skill"
```

---

## Post-plan verification (controller, not a plan task)

Live smokes per spec §8, run by the controller after the branch is complete (they
exercise real CLIs and cannot be delegated as plan tasks):

- **Smoke A (read lane)**: one explore-question delegate against this repo, cheapest
  tier — verifies inference → announcement → dispatch → report gate → ledger, and
  clean-tree/diff-after.
- **Smoke B (write lane)**: one small write task "with review" in a throwaway repo —
  verifies BASE recording, diff gate, reviewer dispatch, resume-channel fix loop,
  controller commit.
- **Smoke C (supervised)**: a batch of ≥3 small mechanical tasks in a throwaway repo —
  verifies the automatic trigger, supervisor cycle management, supervisor-written
  ledger lines, and the controller's independent re-check before commit.

Findings that surface pack facts append to the usual verification logs. Merge to `main`
and tag only on the owner's explicit instruction.
