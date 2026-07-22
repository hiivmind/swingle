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

- **Stdin-hang gotcha fired in production shape**: a Task-2 dispatch composed inside a
  compound command omitted `< /dev/null` → codex hung with the documented signature
  ("Reading additional input from stdin…", log frozen at 39 bytes). Caught by the
  evidence-first liveness check (triggered by the user asking "is it still running?"),
  killed, re-dispatched with the redirect — clean DONE. The redirect is easy to drop when
  the dispatch is embedded in a larger shell line: putting it LAST after the redirections
  is the safe habit.
- **pgrep self-match false-alive**: `pgrep -f 'codex exec'` matches the checking shell's
  own command string and unrelated `codex app-server` daemons; a naive `pkill` then kills
  the checker itself. Fixed pattern: bracket the first letter (`'[b]in/codex exec'`).
  dispatch-reference liveness section updated.
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
2. **`pkill` self-kill from a dispatching shell**: a wrapper shell whose command line
   embeds the dispatch string (`bash -c '… opencode run …'`) matches
   `pkill -f '[o]pencode run'` — the bracket trick does not protect it. The shell killed
   itself before launching (observed exit 144/125 pair). Rule: from any shell that also
   dispatches, kill by RECORDED PID only, never by pattern.
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

- **2026-07-21 — Google**: Gemini **3.6 Flash** (new workhorse), **3.5 Flash-Lite**
  (cheap/fast; *3.5-class — there is no "3.6 Lite"*), **3.5 Flash Cyber** (restricted).
  Source: blog.google announcement. Table moved all agy Flash rows 3.5 → 3.6 same week.

---

## Change history (from archive/v1.1)

- **2026-07-22** — Initial reference from full three-CLI verification round
  (see verification-log.md entry 2026-07-22). Major refutations vs prior notes:
  agy permission model flipped open in 1.1.4; agy exit codes normalized;
  codex `.git` read-only reclassified from "intermittent" to by-design;
  opencode confirmed sandbox-free and stdin-safe.
