# Background Dispatch and Liveness Protocol

Two rules are mandatory for every background dispatch. The failure mode they
guard against: a background agent hangs or dies early while the controller
continues to report it as running (see core/verification-log.md, "2026-07-23 — harness-kill of backgrounded wrappers (v1.2.0 execution run)" entry).

## Rule 1 — Observable launch, stall-based judgment, backstop cap

**Wall-clock time is not evidence of a hang — activity is.** A fixed timeout kills a
healthy long run that is merely slow: the *stall check* (Rule 2) is
the primary kill criterion, and the wall-clock cap is only a **last-resort backstop** for
when nobody is watching (session ended, controller distracted).

At launch, record a per-task log file, apply a generous backstop cap (4–5× estimate, or
omit it for a known-long run that will be actively monitored), and record the session or
conversation id. Its job is orphan cleanup, not progress policing — if a backstop ever
fires on a healthy run, the estimate was wrong: raise it and resume.

Working-tree progress survives a kill too (agents write as they go) — inspect the diff
before resuming to see what's already landed. A kill is a checkpoint, not a restart: resume
the recorded session or conversation after a backstop or hang-kill where partial progress is
real.

## Rule 2 — Evidence-first liveness check

**“It is still running” may only be claimed after running a liveness check in the current
turn.** Never from memory, never from the fact that no completion notification has arrived.

Check whether the recorded process is alive, then inspect the log's modification time, size,
and tail when the active pack declares `stall-signal: log-age`. A plain process-name pattern
can match the checking shell itself and long-lived daemons, producing false alives; use the
recorded PID for both checks and kills.

| Process | Log activity | Verdict | Action |
| --- | --- | --- | --- |
| absent | any | **Dead** — regardless of expectations | Read log tail and classify the failure; a channel failure advances to the next candidate in this provider's resolution order (max 3 attempts), otherwise ask the user |
| alive | mtime fresh (< stall threshold) | Running | Leave it alone; re-check at the next threshold |
| alive | mtime stale (> stall threshold) | **Presumed hung** | Kill it, capture the log, and classify the failure; a channel failure advances to the next candidate in this provider's resolution order (max 3 attempts), otherwise ask the user |

Thresholds are keyed to the manifest's `stall-signal`:

- `log-age`: 300s for low/medium effort; 600–900s for high/xhigh effort. A hard thinking
  step can legitimately emit nothing for over five minutes, so select the threshold at
  dispatch time.
- `process+print-timeout`: process existence plus the pack's print-timeout are the signals.
  Log age is **not** a signal.

## Operating rules

- **Elapsed wall-clock alone is never grounds to kill** — a slow healthy run and a hung run
  look identical on a clock and completely different in the log. Kill only on stall
  evidence (or let the generous backstop reap a genuinely orphaned process).
- **Check on cadence, not on suspicion**: after launching background dispatches, check
  liveness at the first stall threshold — don't wait for the user to ask.
- **A user asking whether a dispatch is still running triggers the liveness check
  immediately; never answer from belief.**
- **Kill by recorded PID, never by pattern, from any shell that also dispatches.** A wrapper
  shell can embed the dispatch string in its own command line and a pattern kill can kill the
  wrapper itself. Capture `$!` at dispatch time; pattern-kill only from a shell that
  dispatches nothing.
- Use the self-reaping wrapper below for harness background tasks. It makes the harness
  notification mean “finished or stall-killed”, executes the stall rule with zero controller
  turns, and leaves the controller responsive throughout. A bare `&` + wrapper exit reports
  completion long before the dispatched process finishes; a watcher that only notifies adds
  controller turns before a kill; a foreground dispatch prevents the controller from serving
  the user and prevents the stall rule from firing.
- **The wrapper must survive its supervisor.** Where the harness's background
  mechanism can reap its own tasks, a supervisor event can kill a healthy
  backgrounded wrapper (see core/verification-log.md, "2026-07-23 — harness-kill of backgrounded wrappers (v1.2.0 execution run)" entry). Detached form: write the dispatch
  script to a file; launch it with `setsid nohup <script> >/dev/null 2>&1 < /dev/null &`
  plus `disown`; record the CLI pid to a pid file; the wrapper appends its terminal line
  ("cli exit=N" or the stall-kill message) to a marker file; a separate lightweight watcher
  watches that marker (see harness adapter for the mechanism). Notification still
  means finished-or-reaped, and no supervisor event can orphan-kill the dispatch. Two
  consecutive supervisor kills of the same dispatch = switch to the detached form.
- On any early exit, the log tail is the diagnosis. Record any new hang/early-exit signature
  in the active pack and append the incident to the verification log.
- Automatic recovery stays within the current provider and its ordered candidates only.
  Tier escalation or a provider change is always user adjudication.

## Self-reaping wrapper

```bash
<pack dispatch template> > "$LOG" 2>&1 &
PROCESS=$!
while kill -0 "$PROCESS" 2>/dev/null; do
  age=$(( $(date +%s) - $(stat -c %Y "$LOG") ))
  [ "$age" -gt <stall-threshold> ] && { kill "$PROCESS"; echo "STALL-KILLED after \${age}s log silence"; break; }
  sleep 10
done
wait "$PROCESS" 2>/dev/null; echo "process exit=$?"
```

Use this template only when the active pack's `stall-signal` is `log-age`. For
`process+print-timeout`, use process existence plus the pack's print-timeout instead; a
log-age watcher would kill healthy runs.
