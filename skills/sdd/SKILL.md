---
name: sdd
description: Execute an implementation plan via subagent-driven development with external-CLI dispatch (codex/opencode/agy). Use whenever executing a written plan with SDD — wraps superpowers:subagent-driven-development and applies the external-dispatch optimizations mechanically. Triggers: "run this plan with SDD", "/sdd", "execute the plan via subagents", the Standard Delivery Flow reaching its execute step.
---

# SDD with External-CLI Dispatch

This skill wraps **superpowers:subagent-driven-development**: that skill's process governs
(per-task loop, task-brief/review-package scripts, statuses, two-verdict reviews, fix
loops, ledger, pre-flight scan, final review). This skill replaces its **dispatch
mechanism** with external CLIs.

Plugin references (read when a step needs detail):
- `${CLAUDE_PLUGIN_ROOT}/references/sdd-external-dispatch.md` — the playbook + rationale
- `${CLAUDE_PLUGIN_ROOT}/references/dispatch-reference.md` — verified per-CLI behavior, gotchas, liveness protocol
- `${CLAUDE_PLUGIN_ROOT}/references/model-catalog.md` — role→tier→model table (the authority for model choice)

## Step 0 — Setup (once per session, before Task 1)

1. Invoke `superpowers:subagent-driven-development` and follow its process EXCEPT the
   dispatch steps, which this skill overrides.
2. Run its `scripts/sdd-workspace`; copy the operating contracts into it:
   `cp "${CLAUDE_PLUGIN_ROOT}/contracts/"*.md "$WORKSPACE"/`
3. Check the ledger (`$WORKSPACE/progress.md`) — never re-dispatch a completed task.
4. Read the role→model table from `${CLAUDE_PLUGIN_ROOT}/references/model-catalog.md`
   and note the routing lever in effect: silent → "floor it" (cheapest model clearing
   each bar); "play it safe" → one tier up on implementers; "via agy" / "delegate
   mechanical to opencode" / "all Claude" reroute lanes. **"all Claude" = use the stock
   skill's Agent-tool dispatch and skip this skill's overrides.**

## Dispatch overrides (replace the skill's "dispatch subagent" steps)

**Implementer** (default lane codex; model from the catalog table — ALWAYS explicit):
```bash
BASE=$(git rev-parse HEAD)   # record BEFORE dispatch; never HEAD~1 later
LOG=$WORKSPACE/task-N.log
timeout --kill-after=30s <backstop≈4-5x estimate> \
codex exec -m <model> -C <repo> -s workspace-write -c approval_policy="never" \
  -c model_reasoning_effort=<effort> --skip-git-repo-check -o $WORKSPACE/task-N-status.md \
  "Read $WORKSPACE/implementer-contract.md — your operating contract. \
   Read $WORKSPACE/task-N-brief.md — your complete requirements. \
   Scene: <one line: where this task fits>. \
   Interfaces from prior tasks: <lines, or 'none'>. \
   Write your full report to $WORKSPACE/task-N-report.md. Begin." \
  > "$LOG" 2>&1 &
```
Run in background; apply the **liveness protocol** (~5-min evidence checks: pgrep + log
mtime/tail; stall evidence is the only kill criterion, never elapsed time — full rules in
dispatch-reference.md).

**Task reviewer** — same shape but **`-s read-only`** (enforced), reviewer-tier model,
prompt names: `task-reviewer-contract.md`, the brief, the report, the review-package
path, and the global constraints copied VERBATIM from the plan. Phrase the restriction
"review only, change nothing in the repo; writing your review file is allowed" — a bare
"modify nothing" makes obedient models skip the review file and answer inline (fine, but
then the verdicts live only in the log tail).

**Fix / NEEDS_CONTEXT** — never a cold dispatch: resume the implementer's session
(`codex exec resume --last "<answers or findings list>"`; opencode `run -s <id>`;
agy `--conversation <id>`), then re-review.

## Flavour choice (be explicit which "dispatch" you mean)

- **Inline** (no dispatch): task below the orchestration floor — a single-file mechanical
  fix the controller finishes in <~2k tokens. Batch several such tasks into one
  ext-dispatch instead of paying per-task cold starts.
- **Ext-dispatch** (this skill's default): Bash → external CLI, per the templates above.
- **Supervised ext-dispatch** (long plans, > ~8 tasks): spawn ONE cheap Claude subagent
  (haiku/sonnet, Agent tool) per task-cycle to run the ext-dispatch templates, liveness,
  mechanical gate, and reviewer dispatch, returning a single report with evidence paths.
  Adjudication and commits STILL happen here in the main thread.
- **Sub-dispatch** (Claude subagent does the work itself) = the "all Claude" lever.
Economics table: references/sdd-external-dispatch.md "Dispatch flavours & economics".

## Controller rules (the hard gate — never offloaded)

- Read back ONLY the status block, `git diff --stat`, and reviewer verdicts. Full diff
  only on findings, ⚠️ items, critical paths, or stat/report disagreement. Never let CLI
  stdout or full logs into context.
- On DONE: re-run the covering tests yourself (output to file, read tail), then
  **you commit** (implementers must not; codex cannot). Then `review-package $BASE HEAD`.
- Ledger line per completed task: `Task N: complete (commits <b7>..<h7>, review clean, session <id>)`.
- Adjudication stays yours: statuses, ⚠️ resolution, plan contradictions → batched to the
  human. Never parallel implementers. Never re-dispatch a ledgered task.
- Final whole-branch review: most-capable tier, `review-package MERGE_BASE HEAD` +
  Minor-findings list; ONE consolidated fix dispatch if findings.

## Gotcha quick-list (full detail: references/dispatch-reference.md)

`< /dev/null` on codex/agy always · agy `-p "<PROMPT>"` LAST · opencode prompt positional
(`-p`=password) · agy buffers (judge liveness by process, not log growth; brain-file sweep
if stdout empty) · only codex is sandboxed — clean tree before, diff after, on agy/opencode
· user asks "still running?" → check evidence immediately, never assert from belief
· in harness background tasks run the CLI foreground-in-wrapper (notification == CLI exit)
+ a stall-watcher; kill by recorded pid, never pkill-by-pattern from a dispatching shell
· opencode can hang at startup with a forever-0-byte log — stall rules apply from byte 0;
after 2 consecutive channel stalls on a small fix, do it inline
· opencode session ids come from `opencode session list`, not the run log.
