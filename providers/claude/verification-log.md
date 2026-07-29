# SDD Dispatch Verification Log — claude

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-24 — claude 2.1.218 (trigger: new provider pack — initial verification)

Probed with `ANTHROPIC_API_KEY` set (nested `claude` authed via key; stderr banner noted).
Scratchpad dispatches, artifacts removed after. Authoring controller was itself Claude Code,
so the write/shell path (P6) and git-commit (P8) — which need `--dangerously-skip-permissions`
— were **blocked by the parent auto-mode classifier** from the authoring session. P6 was then
confirmed by the operator running it via a non-gated shell (write + shell landed on disk);
P8 is inferred from that plus `sandbox: none`.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version + surface | New | `claude --version` = 2.1.218; headless surface = `-p`/`--print`, `--model`, `--session-id`, `--resume`, `--fork-session`, `--permission-mode {acceptEdits,auto,bypassPermissions,manual,dontAsk,plan}`, `--effort`, `--output-format {text,json,stream-json}`, `--add-dir`. No `--sandbox` flag. |
| P2 | `claude -p --model <alias> "<prompt>"` dispatches | Confirmed | PONG, exit 0; clean stdout, banner on **stderr** only |
| P2 (json) | `--output-format json` shape | New | returns `{session_id:<uuid>, result:"PONG", is_error:false, num_turns:1}`; `modelUsage` keys carry the resolved snapshot id |
| P3 | Bogus model error path | New | `--model this-model-does-not-exist-99` → exit **1**, clean local error "It may not exist or you may not have access. Run --model to pick" — fails fast, not remote-only |
| P4 | stdin protection mandatory | Not run | every probe ran without a stdin redirect and none hung; explicit unclosed-pipe backstop deferred |
| P5 | Read, no flags | Confirmed | returned `XYZZY42` from readtest.txt, exit 0 — reads run headless ungated |
| P6 (default/acceptEdits/auto/dontAsk) | Write/shell **silently no-op** without bypass | Confirmed | across all four modes: agent narrates "need permission", **exit 0, file MISSING** on disk — the silent-write footgun; controller on-disk gate mandatory |
| P6 (bypass write/shell) | `--dangerously-skip-permissions` enables headless write + shell | Confirmed | operator ran outside the classifier: `writetest.txt`=HELLO and `cmdtest.txt`=P6CMD on disk, exit 0 |
| P7 | Sandbox escape | N/A | `sandbox: none` — no built-in OS sandbox; `--dangerously-skip-permissions` docs point to external containers |
| P8 | Git commit inside workspace | Inferred | not separately probed (bypass flag classifier-blocked from authoring session); shell execution Confirmed + `sandbox: none` ⇒ `.git` writable, unlike codex's by-design read-only `.git` |
| P9 | `--effort` knob | New | valid `low` → exit 0; invalid `bogus` → `Warning: Unknown --effort value 'bogus' — ignoring it and using the default effort. Valid values: low, medium, high, xhigh, max` then proceeds (exit 0) — locally validated, warned not silently ignored |
| P10 | Output contract | New | clean final message on stdout; banner on stderr; `--output-format json` carries full transcript metadata. `report-transport: report-file` (agent writes report with Write tool, needs bypass) |
| P11 | Argument-parsing footguns | New | prompt is a **trailing positional**; `-p "<prompt>" --model haiku` (flags after prompt) parsed correctly — no `-p`-eats-next-arg (agy) and no `-p`=password (opencode). `-p`/`--print` REQUIRED for headless |
| Session | Controller-assigned id: create-or-resume | New | `--session-id <uuid>` (must be valid UUID) created; `--resume <uuid>` recalled `4242` — `session-source: conversation-id`, no recovery step |
| Session | Read-only lane via plan mode | New | `--permission-mode plan` refused a dispatched workspace write (nothing on disk); wrote a planning doc under `~/.claude/plans/` instead — enforced read-only, but blocks the review-file write, so a plan-mode reviewer returns a captured verdict |
| P12 | Tier models dispatch | Confirmed | `haiku`→claude-haiku-4-5, `sonnet`→claude-sonnet-5, `opus`→claude-opus-4-8 (machine `ANTHROPIC_DEFAULT_OPUS_MODEL` observed repointing opus→claude-opus-4-7[1m]) → all PONG, exit 0 |
| P13 | Reviewer known-defect benchmark | Not run | required before trusting any claude model for the review lane in anger; review rows stamped `verified` for dispatch, not review quality |

**verified-version stamped 2.1.218** on the live dispatch/read/session/model-validation
evidence above, plus the operator-confirmed P6 write/shell path — the implement lane is now
end-to-end verified. Still open: P13 (reviewer known-defect benchmark) before trusting claude
for adversarial review, and P4 (unclosed-stdin backstop).

---

## 2026-07-25 — claude 2.1.218 (trigger: P13 review-lane qualification)

Ran the P13 reviewer known-defect benchmark against `tests/fixtures/p13/defect.diff` with the
standard `task-reviewer-contract.md` and a realistic non-hinting Task-2 brief (the binding
constraint quoted verbatim: exit 2 + `error: <path> not found` on stderr when the file "does
not exist"). Read-only dispatch, verdict captured from stdout, `--effort high`. Two runs per
model.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P13 (sonnet) | required finding cited at ≥ Important | **Not passed** | 2/2 runs: found the `path.exists()`→`read_text()` directory/unreadable defect with file:line, but rated it **Minor** both times ("brief only specifies 'does not exist'") — below the ≥ Important bar |
| P13 (opus) | required finding cited at ≥ Important | **Not passed** | 2/2 runs: same — found it precisely, one run explicitly noting "exit code 1 instead of the spec's exit 2," yet rated **Minor** both times |

**Result: catches-but-under-severities, not a false-clean.** Neither model ever missed the
defect (4/4 runs cited it with file:line) — materially safer than the fixture's
`nemotron-3-ultra-free`, which false-cleaned it. But both consistently down-severity an
uncaught-exception / exit-contract violation to Minor by reading the brief's "does not exist"
literally, so neither clears the ≥ Important gate. Stable across two runs each (n=4, all Minor).

**Operational implication.** The P13 disqualifier is specifically a *false-clean*; Claude does
not false-clean, so it is usable in the review lane **as a finder** — but the controller must
not read a Claude reviewer's severities as final. This lands inside the existing
adjudication-stays-in-the-controller doctrine (`core/playbook.md`): treat Claude review
findings as candidates and re-grade any Minor that is actually a violated binding constraint
up to Important before merge-gating. Do **not** hand a Claude reviewer sole, unadjudicated
authority over merge severity on this defect class.

**Candidate follow-up (not applied here):** a one-line calibration nudge in
`task-reviewer-contract.md` — "an uncaught exception on plausible user input is Important, not
Minor, even when the brief names only the happy-path failure" — might lift this class to the
right severity, but it touches the shared contract for every provider and needs its own
before/after evidence, so it is filed as a follow-up rather than slipped in on one fixture.

Review-lane rows in `models.yaml` remain `verified` for **dispatch** (unchanged); they are
**not** stamped for review quality. P4 (unclosed-stdin backstop) still open.

---

## 2026-07-25 (follow-up) — P13 re-run with the task-reviewer calibration nudge

The 2026-07-25 miss above motivated a severity-floor nudge in the shared
`contracts/task-reviewer-contract.md` (see core/verification-log.md, same date): an uncaught
exception on plausible user input is Important, not Minor, even when the brief names only the
happy path. Re-ran the identical P13 dispatch (same fixture, brief, `--effort high`, 2 runs
per model) with the nudged contract.

| Probe | Model | Verdict | Evidence |
| --- | --- | --- | --- |
| P13 | sonnet | **Passed** | 2/2 runs cited the `path.exists()`→`read_text()` defect under **Important** (generalizing to `PermissionError`/`UnicodeDecodeError`), assessment flipped to Needs fixes |
| P13 | opus | **Passed** | 2/2 runs same — defect under **Important**, Needs fixes |

Before/after is clean and stable: 4/4 **Minor** (Approved) without the nudge → 4/4 **Important**
(Needs fixes) with it. **The `claude` review lane now clears P13** and is qualified for review
quality, *provided the nudged contract (≥ v1.9.2) is in force*. This is a prompt mitigation, so
keep the standing rule that severity adjudication stays in the controller — the nudge raises
the floor reliably here, it does not remove the need to adjudicate. P4 (unclosed-stdin
backstop) still open.

## 2026-07-25 — plugin renamed to Swingle (v2.0.0)

The plugin `sdd-dispatch` is renamed `swingle` at v2.0.0 (`sdd-dispatch-marketplace` →
`swingle-marketplace`, skill `sdd-dispatch-verify` → `swingle-verify`, repository →
`discreteds/swingle`). Entries above predate the rename and keep the old names as
historical record. No pack facts or probe results changed in this release.

## 2026-07-29 — claude 2.1.220 (trigger: version bump, drift from stamped 2.1.218)

Vendor changelog (2.1.218→2.1.220, https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
read first: 2.1.219 added Claude Opus 5 (`claude-opus-5`) as "now the default Opus model"
and a `sandbox.network.strictAllowlist` setting (opt-in, not exercised — pack stays
`sandbox: none` by default); 2.1.220 is "bug fixes and reliability improvements" with no
itemized entries. Probed from a Claude Code controller session; self-dispatch trap
(`--dangerously-skip-permissions` blocked by the parent auto-mode Bash classifier,
documented in pack.md) did **not** trigger this round even with `CLAUDECODE=1` set —
the nested bypass dispatch ran unblocked under this session's permission mode. Recorded
as a refinement, not a refutation: the block is permission-mode-dependent, not universal.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version + surface | Confirmed | `claude --version` = 2.1.220; all headless flags exercised below still present, no new/removed flags observed |
| P2 | Trivial dispatch | Confirmed | PONG, exit 0 |
| P3 | Bogus model error path | Confirmed | same clean local error text, exit 1 |
| P4 | stdin protection mandatory | **Refined** | fed from a never-closing named pipe under a manual 60s backstop: did **not** hang — completed in 10s with `Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly...`, then PONG, exit 0. The CLI has its own built-in ~3s stdin-absence timeout; an adapter-side end-of-input protection is confirmed **not mandatory** (closes the item left open since 2026-07-24) |
| P5 | Read, no flags | Confirmed | XYZZY42 returned, exit 0 |
| P6 (no flags, write) | Silent no-op without bypass | Confirmed | narrated "need your permission... please approve", exit 0, file MISSING on disk |
| P6 (no flags, shell) | Silent no-op without bypass | **Refined** | narrated "🟢 Echo command executed successfully" with the command's stdout shown — **falsely claiming success** — while `cmdtest.txt` was MISSING on disk. More deceptive than the write-path narration (which at least asks for permission); sharpens the controller-must-verify-on-disk doctrine for the shell sub-case specifically |
| P6 (bypass, write) | `--dangerously-skip-permissions` enables headless write | Confirmed directly | `writetest.txt`=HELLO on disk, exit 0 — first direct (non-operator-relayed) confirmation |
| P6 (bypass, shell) | `--dangerously-skip-permissions` enables headless shell | Confirmed directly | `cmdtest.txt`=P6CMD on disk, exit 0 |
| P8 | Git commit inside workspace | **Confirmed directly** (was Inferred 2026-07-24) | throwaway repo, seed commit present; dispatched create+add+commit; `git log` shows `test commit` on top of `seed commit`, file content correct |
| P9 | `--effort` knob | Confirmed | valid `low` → PONG exit 0; invalid `bogus` → same warning text, proceeds, exit 0 |
| P11 | Argument-parsing footguns | Confirmed | `-p "<prompt>" --model haiku` (flags after prompt) still parses correctly |
| P12 | Tier models dispatch | **Refuted (opus only)** | `--output-format json` `modelUsage` keys: `haiku`→`claude-haiku-4-5-20251001` (unchanged), `sonnet`→`claude-sonnet-5` (unchanged), `opus`→**`claude-opus-5`** (was `claude-opus-4-8`) — matches the changelog's Opus 5 default-model change |
| P13 | Reviewer known-defect benchmark | Not re-run | `opus`'s underlying snapshot changed generation (4.8→5) via the same alias; the fixture requires reconstructing a faithful Task-2 brief/report pair not preserved in this checkout. Flagged as a follow-up below rather than re-run on a low-fidelity reconstruction |

**verified-version stamped 2.1.220.** All facts confirmed except the opus alias resolution,
which is corrected below and in `models.yaml`/`models.md`. P4 closed as non-mandatory
(CLI self-recovers from absent stdin after ~3s). P6 shell no-op narration sharpened per
above. P8 upgraded from Inferred to Confirmed.

**Follow-up (not applied here):** re-run P13 for `opus` now that it resolves to
`claude-opus-5` rather than the `claude-opus-4-8` snapshot the 2026-07-25 qualification
ran against — a full generation bump on the same alias warrants re-confirming the review
lane still clears the ≥ v1.9.2 contract before leaning on it for adversarial review of
opus's own generation.

