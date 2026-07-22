# SDD Dispatch Verification Protocol

The repeatable probe suite for (re)verifying dispatch-CLI behavior. Run it per CLI when a
trigger fires (see README.md), then append results to [verification-log.md](verification-log.md)
and update [dispatch-reference.md](dispatch-reference.md) / [model-catalog.md](model-catalog.md).

The invocable form of this process is this plugin's `sdd-dispatch-verify` skill
(`${CLAUDE_PLUGIN_ROOT}/skills/sdd-dispatch-verify/SKILL.md`).

## Ground rules

- **Work in a scratchpad directory**, never a real repo. Clean up all artifacts afterward.
- **Never mask exit codes with pipes.** `cmd | head; echo $?` reports `head`'s exit code —
  use `cmd > out.txt 2>&1; echo $?` or `${PIPESTATUS[0]}`.
- Capture the **version first**; every recorded fact is version-stamped.
- Confirm side effects **on disk** (`ls`, `cat`), never from the agent's prose.
- Bound every probe with a `timeout` — hang detection is a first-class result
  (exit 124/143 = hung).
- A refuted prior fact is recorded as a refutation, not silently overwritten.

## Probe suite

Run per CLI. `$SCRATCH` = a session scratchpad dir.

### P1 — Version & surface
```bash
which <cli>; <cli> --version
<cli> <run-subcommand> --help        # diff flags against dispatch-reference.md
<cli> models                          # where supported; diff against model-catalog.md
```

### P2 — Trivial dispatch + exit code (success path)
Prompt: `Reply with exactly the word PONG and nothing else. Do not use any tools.`
Expect: PONG on stdout, exit 0. Record any banner noise around it.

### P3 — Bogus model (error path + validation)
Dispatch with `-m totally-bogus-model-xyz` (unpiped, capture raw `$?`).
Expect: clean error + nonzero exit. Record whether validation is client- or server-side
and whether the error lists valid models.

### P4 — Stdin hang
Run P2's command **without** `< /dev/null`, fed from a never-closing pipe, under `timeout 60`:
```bash
tail -f /dev/null | timeout 60 <cli> <dispatch…> "Reply STDINTEST"
```
Exit 124/143 ⇒ hangs (redirect mandatory). Completion ⇒ redirect optional.

### P5 — Read permission (no flags)
Seed `$SCRATCH/readtest.txt` with a sentinel (`the secret word is XYZZY42`), dispatch
**without any permission flags**: `Read the file readtest.txt and tell me the secret word.`
Record whether the read succeeded, was denied, or hung waiting for approval.

### P6 — Write permission (no flags, then with flags)
Dispatch without permission flags: `Create a file named writetest.txt containing exactly HELLO.`
Verify **on disk**. If denied, repeat with the CLI's permission flags and record the minimum
flag set that permits writes.

### P7 — Sandbox escape (only if a sandbox is claimed)
Ask the agent to write **inside** the workspace, to **/tmp**, and to **$HOME** in one task,
reporting per-path results. Verify each on disk. Records the sandbox's true boundary.

### P8 — Git commit inside sandbox
`git init` a throwaway repo in `$SCRATCH`, seed one commit, then dispatch:
`Create gitfile.txt, git add it, git commit with message 'test commit'. Report any git errors verbatim.`
Verify with `git log`. Records whether `.git` is writable (controller-commits rationale).

### P9 — Reasoning-effort knob
Dispatch with the CLI's effort mechanism at a valid value, then with a **bogus** value.
Record: accepted / errored / **silently ignored** (the dangerous case), and any
constraints (e.g. agy: `--effort` errors when combined with an effort-suffixed model name).

### P10 — Output contract / artifact diversion
Dispatch a document-shaped task: `Produce a well-structured 500-word design document titled '<X>' covering …`
Compare stdout size vs. content. If stdout is banner-only, hunt for the artifact
(agy: `find ~/.gemini/antigravity-cli/brain -name '*.md' -mmin -10 -not -path '*/.system_generated/*'`).
Also verify any report-file flag (codex `-o`): does it hold the full transcript or last message only?

### P11 — Argument-parsing footguns
Probe known traps and candidates from `--help` diffs:
- agy: flag placed immediately after `-p` (does it become the prompt? is the model dropped?)
- opencode: `-p` collision (password vs prompt habit)
- any new short-flag ambiguities the help text suggests

### P12 — New-model dispatch check
For each model newly present in P1's list: one P2-style probe to confirm it actually
dispatches (catalog "listed" → "verified"). For each model in the catalog now *absent*:
record the removal.

## Recording

Append to [verification-log.md](verification-log.md):

```markdown
## YYYY-MM-DD — <cli> <version> (trigger: <version bump | model release | anomaly | quarterly>)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P4 | `< /dev/null` mandatory | Confirmed | hung 60s, exit 143, "Reading additional input…" |
| …  | | Confirmed / Refuted / Refined / New | one-line raw evidence |
```

Then:
1. Update dispatch-reference.md (facts + version stamps) and model-catalog.md (inventory, watch list).
2. If findings change how the `sdd` skill should dispatch, update `skills/sdd/SKILL.md`
   and `contracts/` in the same round.
3. Clean up `$SCRATCH` artifacts (including throwaway git repos and any `/tmp` escapes from P7).
4. Commit in the plugin repo; bump the plugin version for behavior-fact changes.

## Cost note

The full suite is ~10–12 cheap dispatches per CLI (use each CLI's cheapest model;
one-word replies). P10 is the only multi-hundred-token probe. Total cost is negligible
against a single mis-dispatched implementer.
