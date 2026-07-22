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
