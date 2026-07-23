# SDD Dispatch Verification Protocol

The repeatable probe suite for (re)verifying provider-pack behavior. Run it for a pack when a
trigger fires (see README.md), then append results to the pack's verification log and update
its pack.md / models.md.

The invocable form of this process is the plugin's verification skill; the active harness
adapter supplies the command details.

## Ground rules

- **Work in a scratchpad directory**, never a real repo. Clean up all artifacts afterward.
- **Never mask exit codes with pipes.** Capture raw exit status rather than the status of a
  downstream formatter.
- Capture the **version first**; every recorded fact is version-stamped.
- Confirm side effects **on disk**, never from the agent's prose.
- Bound every probe with a backstop — hang detection is a first-class result.
- A refuted prior fact is recorded as a refutation, not silently overwritten.

## Probe suite

Run per pack. `$SCRATCH` = a session scratchpad dir. The harness adapter provides the
pack-specific dispatch template and command surface.

### P1 — Version & surface

Record the pack version and inspect its supported dispatch surface and model inventory. Diff
the findings against the pack's pack.md and models.md.

### P2 — Trivial dispatch + exit code (success path)

Prompt: `Reply with exactly the word PONG and nothing else. Do not use any tools.`
Expect: PONG on stdout, exit 0. Record any banner noise around it.

### P3 — Bogus model (error path + validation)

Dispatch with a deliberately nonexistent model value, unpiped, and capture raw exit status.
Expect: clean error + nonzero exit. Record whether validation is local or remote and whether
the error lists valid models.

### P4 — Stdin hang

Run P2's command without the adapter's end-of-input protection, fed from a never-closing
input, under a 60-second backstop. A hang means the protection is mandatory; completion means
it is optional.

### P5 — Read permission (no flags)

Seed `$SCRATCH/readtest.txt` with a sentinel (`the secret word is XYZZY42`), then dispatch
without permission flags: `Read the file readtest.txt and tell me the secret word.` Record
whether the read succeeded, was denied, or hung waiting for approval.

### P6 — Write permission (no flags, then with flags)

Dispatch without permission flags: `Create a file named writetest.txt containing exactly
HELLO.` Verify **on disk**. If denied, repeat with the pack's permission settings and record
the minimum setting that permits writes.

**P6 must also probe shell-command execution, not only file tools**: dispatch `Run the
shell command 'echo P6CMD > cmdtest.txt' and report its output.` and verify on disk.
File-tool and command permissions are separately gated on some providers (agy ≥1.1.4
allows file read/write under default persisted policy but auto-denies the `command`
permission headless — a gap the file-only probe missed for two verification rounds).
Record the file-tool and command verdicts separately.

### P7 — Sandbox escape (only if a sandbox is claimed)

Ask the agent to write **inside** the workspace, to a temporary location, and to a location
outside the workspace in one task, reporting per-path results. Verify each on disk. Record
the sandbox's true boundary.

### P8 — Git commit inside sandbox

Create a throwaway repository in `$SCRATCH`, seed one commit, then ask the agent to create
a file, stage it, and commit it with message `test commit`. Verify with the repository log.
Record whether metadata is writable (the controller-commits rationale).

### P9 — Reasoning-effort knob

Dispatch with the pack's reasoning mechanism at a valid value, then with a deliberately
invalid value. Record: accepted / errored / **silently ignored** (the dangerous case), and
any constraints.

### P10 — Output contract / artifact diversion

Dispatch a document-shaped task and compare stdout size with content. If stdout is banner-only,
locate the artifact using the active pack's adapter. Also verify any report-file setting: does
it hold the full transcript or last message only?

### P11 — Argument-parsing footguns

Probe known traps and candidates from the adapter's command-surface diff. Record positional,
short-option, and option-order ambiguities that could silently replace a prompt or selection.

### P12 — New-model dispatch check

For each newly present model in P1's list: one P2-style probe to confirm it actually
dispatches (catalog `listed` → `verified`). For each model in the catalog now absent:
record the removal.

### P13 — Reviewer known-defect benchmark

Dispatch the candidate reviewer with the standard task-reviewer contract against
`tests/fixtures/p13/defect.diff` (+ its brief context in README). PASS iff every finding
in expected-findings.md is cited at equal-or-higher severity. A false-clean disqualifies
the candidate for review lanes.

## Recording

Append to the appropriate verification log:

```markdown
## YYYY-MM-DD — <provider> <version> (trigger: <version bump | model release | anomaly | quarterly>)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P4 | input protection mandatory | Confirmed | hung 60s, exit 143 |
| …  | | Confirmed / Refuted / Refined / New | one-line raw evidence |
```

Then:

1. Update the active pack's pack.md and models.md.
2. If findings change how SDD should dispatch, update the relevant harness adapter and
   contracts in the same round.
3. Clean up `$SCRATCH` artifacts, including any test writes outside the workspace.
4. Commit in the plugin repo; bump the plugin version for behavior-fact changes.

## Cost note

The full suite is ~10–12 cheap dispatches per pack (use the lowest eligible model; one-word
replies). P10 is the only multi-hundred-token probe. Total cost is negligible against a
single mis-dispatched implementer.
