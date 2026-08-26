# Provider liveness

Liveness supervision is a controller policy for one provider attempt. It diagnoses an
attempt; it does not certify a provider, model, account, or result.

## Policy terms

- **Check interval** is the cadence at which the controller observes the retained attempt.
- **Startup grace** is the time allowed before the controller diagnoses the absence of a
  first output or other progress signal.
- **Silence warning** is the allowed silence after a progress signal before the controller
  diagnoses the attempt again.
- **Hard timeout** is an explicit total runtime deadline. A null hard timeout never
  terminates a process automatically.
- **Progress signal** is observable output, a process-state transition, a report-file
  change, or a provider-specific event that shows the attempt is active.

These are policy fields, not provider capabilities. Resolve them before launch from the
selected dispatch policy. A controller retains one policy and one observation record for
the attempt.

## Supervision flow

1. Launch with a retained process, job, task, or session handle.
2. Observe at the configured check interval.
3. Apply startup-grace and silence-warning diagnosis thresholds.
4. Inspect process state and provider progress signals.
5. Continue, diagnose, or terminate according to the resolved policy.
6. Record one `liveness-warning` for each threshold crossing or controller action.
7. Retry only after the controller makes an explicit retry decision.

Routine observations do not create warning events. A warning starts diagnosis; it is not a
failure verdict. Silence alone never proves a stall. An alive process with no recent output
can still be computing, buffering, waiting on a provider, or waiting on an unavailable
interactive approval.

If the hard timeout is null, the controller never terminates the process for elapsed time.
An explicit hard timeout is the only elapsed-time termination condition. Termination does
not imply retry; the controller must decide whether and how to retry after recording the
outcome.

## Progress interpretation

Use the provider's observed signal without treating it as final text or completion unless
its contract says so:

- A buffered terminal object is a completion signal, not an incremental progress stream.
- A JSONL or streaming event is progress when events arrive, and its documented terminal
  event is completion only after the event is observed.
- A report-file change is progress, but an unchanged report file does not prove a stall.
- A process-state change is evidence to inspect, not evidence that the task succeeded.
- A process that remains alive, emits no visible output, and has an unavailable interactive
  approval is a hidden permission-prompt stall. Diagnose the missing approval path instead
  of treating silence as completion or as proof of a compute stall.

Provider notes supply only behavioral interpretation of these signals. They do not replace
this controller policy or set global thresholds.
