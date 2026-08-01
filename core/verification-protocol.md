# Swingle Verification Protocol

The repeatable probe suite for (re)verifying provider-pack behavior. Run it for a pack when a
trigger fires (see README.md), then append results to the pack's verification log and update
its pack.md / models.yaml / models.md.

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
the findings against the pack's pack.md / models.yaml / models.md.

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
File-tool and command permissions are separately gated on some providers (see
the provider verification logs). Record the file-tool and command verdicts
separately.

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

**Record into the writable SOURCE tree only — never an installed plugin copy.** Installed
caches (Claude Code `~/.claude/plugins/cache/...`, Codex `~/.codex/plugins/cache/...` /
`~/.codex/.tmp/marketplaces/...`) are throwaway snapshots clobbered by the next upgrade.
If the running skill's root is an installed copy, resolve the git source checkout first
(swingle-verify Procedure step 0), write and commit there, then refresh installs.
This applies equally to mid-run incident notes appended by the `swingle-sdd` skill.

When no writable source exists (no checkout on the machine, or no push rights), **raise a
GitHub issue on the upstream project instead of dropping the finding** — one issue per
independent finding using the repository's "Verification finding" template
(`gh issue create --repo hiivmind/swingle --label verification`). The
recording ladder is: writable source → commit; clone-but-no-push → local commit + issue
or PR; no source tree → issue only. **Deduplicate before filing**: search existing
`verification` issues (open and closed) first — an equivalent open issue gets a 👍
reaction, not a duplicate; a new angle or wrinkle on an existing finding gets a comment
with only the new evidence; only a genuinely distinct finding gets a new issue.

**Operating guidance in log entries.** When a round or a field failure teaches an
*operating instruction* — something a future dispatcher must do differently on this
version and forward — write it in the log entry. House style:

`**Guidance[ (<lane>[, <lane>…])]:** <what to do on this version and forward>`

directly under the entry heading; lanes come from the packs' lane vocabulary, and
omitting the parenthetical means all lanes. Freeform prose is equally valid — the line
is for scannability, not for a parser, and nothing validates it. An instruction applies
from its version forward until a later entry says otherwise; a later entry lifting a
restriction is itself guidance. Publish instructions, never verdicts: between
discovering a failure and understanding it, the honest artifact is an open issue, and
*"pin the previous version for this lane / route the lane elsewhere, tracking #N"* is
always available as the instruction when no workaround exists, so a published entry is
never instruction-free. Example of the form:
`**Guidance (review, implement):** forbid shell for reviewers; restrict
implementers to single simple commands` — see the originating provider log entry
for its evidence.

**A user's local record.** A user who cannot write to the source records their own
operating instructions in `${XDG_CONFIG_HOME:-~/.config}/swingle/verification/<id>.md`
— same convention, on the user's own disk where a plugin upgrade cannot overwrite it,
read by the dispatch skills **in addition to** the pack's log (additive, never
precedence). A private note may record an undiagnosed state ("hit this on X, filed #N,
expect it"); the publish-instructions rule governs what ships in a pack, not what a
user tells themselves.

**Drift-triggered findings (the common real-world trigger).** The version gate is
advisory: the `swingle-sdd` / `swingle-delegate` skills warn on `installed ≠ verified-version` and proceed
— re-verification is maintenance, not a per-dispatch tax. When a dispatch then fails with a
**channel-class** signature (auth/permission failure, silent no-op = exit 0 + zero work +
missing/empty report, a rejected or unknown flag, a transport/startup failure surviving the
pack's retry) **while that drift is in effect**, the failure is evidence the pack is stale
on the running CLI version — an `anomaly` trigger. The controller does NOT file
automatically: it runs the dedup search above and **recommends** the appropriate action
(👍 / comment / new issue) to the user, with the fields below pre-filled — installed CLI
version vs `verified-version`, plugin version, the controlling harness + its version, and
the verbatim failure signature. **Quality failures are excluded** (a reviewer rejecting the
work is not drift evidence). The user decides whether to file.
The full user loop is: file upstream → solve it locally if possible → comment the
solution back on the issue → record it as a local operating instruction (see "A user's
local record" above) → continue operating, with dispatches now acting on the recorded
guidance instead of rediscovering it each session.

Append to the appropriate verification log:

```markdown
## YYYY-MM-DD — <provider> <version> (trigger: <version bump | model release | anomaly | quarterly>)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P4 | input protection mandatory | Confirmed | hung 60s, exit 143 |
| …  | | Confirmed / Refuted / Refined / New | one-line raw evidence |
```

Then:

1. Update the active pack's pack.md and models.yaml (models.md for narrative).
2. If findings change how SDD should dispatch, update the relevant harness adapter and
   contracts in the same round.
3. Clean up `$SCRATCH` artifacts, including any test writes outside the workspace.
4. Commit in the plugin repo; bump the plugin version for behavior-fact changes.

## Cost note

The full suite is ~10–12 cheap dispatches per pack (use the lowest eligible model; one-word
replies). P10 is the only multi-hundred-token probe. Total cost is negligible against a
single mis-dispatched implementer.
