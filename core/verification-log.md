# SDD Dispatch Verification Log

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](verification-protocol.md).

Per-provider rounds: providers/<id>/verification-log.md. Pre-split history: archive/v1.1/verification-log.md.

---

**Cross-CLI synthesis (2026-07-22) (from archive/v1.1):** codex fails loud and is contained (real sandbox,
server-validated knobs); agy and opencode fail quiet and are unconstrained (flag-free
read/write, silent knob failures, agy's silent `-p`/auth/brain-file traps). Codex is the
default lane for writes and structured reviews; the controller hard gate is the only real
safety boundary on all three.

---

## 2026-07-22 — incident notes from first live /sdd run (smoke test) (from archive/v1.1)

- (Two incident bullets from this entry — the stdin-hang and the pgrep self-match —
  contain provider invocation strings and live in providers/codex/verification-log.md
  per the migration manifest.)
- Full pipeline otherwise green end-to-end: contract compliance (no implementer commits,
  ≤15-line status blocks), enforced read-only reviewer, two-verdict reviews with
  file:line evidence, controller gate + commits, ledger, Sol final review READY TO MERGE.

---

## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (from archive/v1.1)

**What worked (verified in anger):**
- 5-minute stall watchers caught every hang at threshold. Both times the user asked
  "is it still running?" the evidence said no — the prior holds.
- (Two further "what worked" bullets from this entry name provider models and live in
  providers/opencode/verification-log.md per the migration manifest.)

**New findings (all opencode v1.17.18 / Zen, this machine):**
2. (The pkill-self-kill finding contains provider invocation strings and lives in
   providers/opencode/verification-log.md per the migration manifest. Its controller
   rule — from any shell that also dispatches, kill by RECORDED PID only, never by
   pattern — is doctrine in core/liveness.md.)
3. **Harness wrapper notifications ≠ CLI completion**: backgrounding the CLI with `&`
   inside a backgrounded harness command makes the harness report "completed" when the
   wrapper exits, seconds after launch. Rule: in harness background tasks run the CLI in
   the wrapper's foreground so notification == CLI exit; pair with a stall watcher.
4. **Reviewer prompt phrasing**: "you are READ-ONLY: modify nothing" made the reviewer
   (correctly) skip writing its review file — it reviewed inline to stdout instead.
   Verdicts were still delivered; phrase as "review only, change nothing in the repo;
   writing your review file is allowed".

**Cost note:** the productive path (2 tasks, 2 reviews, 2 fix loops, resume Q&A) was
~35 min wall-clock; the hang windows added ~40 min of detection/retry. Detection cost is
bounded by the 5-min threshold — the protocol worked; the channel was the problem.

---

## Release history (from archive/v1.1)

- (Release-history entries name provider models; each lives in the pertinent pack's
  models.md History section per the migration manifest — the 2026-07-21 Google release
  entry is primary in providers/agy/models.md, mirrored in providers/opencode/models.md.
  Pre-split original: the archived v1.1 model catalog.)

---

## Change history (from archive/v1.1)

- **2026-07-22** — Initial reference from full three-CLI verification round
  (see verification-log.md entry 2026-07-22). Major refutations vs prior notes:
  agy permission model flipped open in 1.1.4; agy exit codes normalized;
  codex `.git` read-only reclassified from "intermittent" to by-design;
  opencode confirmed sandbox-free and stdin-safe.

---

## 2026-07-23 — v1.2.0 provider-pack migration (release gate)

Migration map: docs/migration-1.2.0.md. Executed via /sdd (codex lane: luna/terra),
10 tasks, per-task two-verdict reviews — doubling as smoke test 3 of the machinery.

Gate results (controller-run):
- `scripts/validate-packs --root .` → CLEAN (manifest grammar, argv safety, model
  tables, purity, links, version sync).
- `pytest tests/` → 25 passed.
- `scripts/codex-smoke` → 4/4 PASS, repeated from a fresh `git clone` → 4/4 PASS.
- Config fail-closed fixtures (malformed, disabled default) → exit 1 each.
- Environment detection (this machine, non-blocking): agy installed, codex installed,
  opencode installed.
- Claude Code install/load smoke: deferred to the post-release user step (reinstall
  plugin + confirm the sdd skill's Step 0 reaches the trust gate) — a live session
  cannot reinstall itself mid-plan; recorded in the run ledger.

Resolution walks (all three resolved to their pack's P1 row; model ids live in the
pack tables — reproduce with `scripts/validate-packs --root . --resolve "<role>" <id>`):
- per-task reviewer → (standard, review) → opencode P1 (verified)
- transcription implementer → (cheapest, implement) → codex P1 (verified)
- adaptation implementer → (standard, implement) → agy P1 (experimental)

Post-gate final review (whole branch, most-capable tier): round 1 — 1 Critical
(step0 executed argv despite validation findings) + 9 Important; consolidated fix
commit addressed 8 (Claude smoke deferral accepted under Task 10 Step 3c). Round 2 —
one ordering regression (native bypass vs config load); fixed with regression test.
Round 3 verdict: READY TO MERGE. Final gates: pytest 31/31, validate-packs CLEAN,
codex-smoke 4/4 (incl. fresh clone).

---

## 2026-07-23 — harness-kill of backgrounded wrappers (v1.2.0 execution run)

During Task 7 of the migration run, the controlling harness killed the backgrounded
dispatch wrapper twice, ~40–60s after launch (harness "stopped" notifications; log
frozen at CLI startup; zero tree writes; no CLI process remaining). The CLI itself was
healthy both times. Mitigation verified in the same run and used for all remaining
dispatches: detach the wrapper (`setsid nohup` + pid file + terminal marker file) and
watch the marker from a separate lightweight watcher. Doctrine added to core/liveness.md
("the wrapper must survive its supervisor"); harness mechanism noted in the claude-code
adapter. Also verified this run: the provider resume surface accepts only config-override
flags (recorded in the codex pack, 2026-07-23).

---

## 2026-07-23 — v1.2.0 smoke: Claude install/load + first agy-lane run

- The deferred Claude Code install/load smoke is COMPLETE: after user plugin reload, the
  v1.2.0 sdd skill loaded from the new tree and drove Step 0 end-to-end — trust gate
  passed live (validate-packs exit 0; `git status --porcelain providers/` clean),
  detection/config/compat/routing/resolution all ran from the packs, and
  `validate-packs --resolve` matched the documented walks.
- Compatibility step earned its keep on its first outing: it caught agy 1.1.5 (pack
  stamp 1.1.4) before dispatch, and the mismatch was real — 1.1.5 flips the headless
  permission model again (provider details in providers/agy/verification-log.md).
- Controller-gate doctrine validated against a silent no-op: a permission-starved run
  exited 0 with no work; diff-after + report-exists caught it (exit codes are not
  evidence of work).
- Detached-wrapper doctrine (liveness.md) held on its first deliberate use: wrapper
  survived, marker file fired, no supervisor kill.

---

## 2026-07-23 — Codex plugin distribution verified (v1.2.3)

The repository is now a Codex plugin (`.codex-plugin/plugin.json`, official schema per
learn.chatgpt.com/docs/build-plugins) with a self-hosted marketplace
(`.agents/plugins/marketplace.json`, plugin source `local ./` — the marketplace snapshot
IS the repo clone; a `git-subdir` self-reference fails with "plugin not found").
Verified end-to-end on codex 0.144.3 against the public GitHub repo:
`codex plugin marketplace add discreteds/sdd-dispatch-plugin` →
`codex plugin add sdd-dispatch@sdd-dispatch-marketplace` → installed+enabled at
`~/.codex/plugins/cache/…/sdd-dispatch/1.2.3/` with the complete sibling layout
(core/, providers/, contracts/ beside skills/), so skill root resolution is intact.
Note: `codex plugin add` works headlessly — the docs' /plugins-browser flow is optional.
Skills-only fallback (`.agents/skills` symlinks) documented as Route B; the previously
documented `~/.codex/skills` location is NOT in the official scan list.

## 2026-07-23 — supervised delegate: a native supervisor truncated the append-only ledger (v1.3.0)

Smoke C exercised the supervised delegate flavour (3 mechanical jobs = 3 planned cycles,
at the ≥3 auto-supervision trigger) with a cheap harness-native subagent running the
mechanical cycle. The cycle itself worked — three sequential agy dispatches, HEAD unchanged
throughout, all work left uncommitted for the controller, correct evidence reads returned
with paths.

**Finding: the supervisor REWROTE `ledger.md` instead of appending to it**, destroying the
`NNN allocated:` lines the controller had written before launch — precisely the durable
job-number→task mapping that exists so a killed supervisor loses no state. The dispatch
instruction said "append", which was not enough; the subagent recreated the file with its
own header. **Rule for supervised dispatch: instruct the supervisor to append with `>>`
only, never to create, truncate, or rewrite the ledger, and have the controller re-read the
ledger after the supervisor returns to confirm its pre-launch allocations survived.**

**Second, smaller finding: the supervisor's summary paraphrased worker statuses.** It
reported `status=COMPLETED` for all three jobs — a token outside the four-status vocabulary
— because the cheapest-tier workers never emitted a real status block (see the agy log,
same date). The controller's independent re-check (HEAD, porcelain, stat, full diff, and
its own test run: 7/7) is what established the work was actually sound. This is the
doctrine working as designed: **the supervisor's "all green" is evidence to check, not a
gate result.**

## 2026-07-23 — supervised-delegate rules verified behaviorally (v1.4.0)

The two rules added earlier this day (append-only ledger; missing status block = UNKNOWN)
were prose that nothing had exercised. Both are now tested against live supervised cycles
with cheap native supervisors and `gemini-3.6-flash-low` workers.

**RULE 1 — append-only ledger: PASSES.** A 3-job supervised batch was launched over a
ledger the controller had pre-seeded with a header, a `SENTINEL-…-DO-NOT-REMOVE` line, and
three `NNN allocated:` lines. After the run the original five lines survived as an exact
byte-for-byte prefix (diffed, sentinel count 1) with six appended lines beneath. Repeated
on a second single-job cycle — prefix intact again. The earlier truncation is not
reproducible once the brief explicitly forbids `>`, heredoc overwrite, reorder, and
"tidying" instead of merely saying "append".

**RULE 2 — missing status block: PASSES, escalation path included.** The first batch did
NOT exercise it: all three workers emitted literal `STATUS: DONE`, so the supervisor was
never tempted to infer. A second cycle forced the failing case with a worker prompt that
deliberately omitted any status instruction. Ground truth: zero occurrences of any of the
four tokens anywhere in the dispatch log. The supervisor reported `status=UNKNOWN`, quoted
the agent's prose verbatim, stated it was escalating, and wrote
`006 worker-finished: status=UNKNOWN` to the ledger. Contrast the pre-rule run, which
reported the invented token `status=COMPLETED` for prose-only output.

**Incidental finding worth acting on — inline beats by-reference for cheap models.** In
the 3-job batch the status-block instruction sat *inline in the dispatch prompt* and got
3/3 conformance from `gemini-3.6-flash-low`. In the earlier pre-rule batch the same
requirement reached the same model only *by reference to the contract file* and got 0/3.
One line in the prompt appears to be worth more than a contract citation at the cheapest
tier. This is n=3 vs n=3 and not statistically established — recorded as a lead, not a
law.

**Controller adjudication still earned its keep**: the escalation-case worker also added an
unrequested docstring to the pre-existing `inc()`, visible only by reading the diff. Both
runs left HEAD unchanged and the controller's own test runs were green (4/4 and 2/2).
