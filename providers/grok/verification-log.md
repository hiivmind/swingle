# SDD Dispatch Verification Log — grok

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

Primary docs for re-verify (read first on every CLI bump):
`~/.grok/docs/user-guide/14-headless-mode.md`, `17-sessions.md`, `18-sandbox.md`,
`22-permissions-and-safety.md`.

---

## 2026-07-23 — grok 0.2.111 (trigger: new provider pack; pre-design smokes)

Pre-pack smokes recorded in
`docs/superpowers/specs/2026-07-23-grok-provider-design.md` §Pre-design live smoke.
Pack authored 2026-07-24 from user-guide + those smokes; full P1–P13 suite follows
implementation (write-first, verify-after).

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 (partial) | version surface | **Confirmed** | `grok --version` → `0.2.111 (94172f2aa4) [stable]` |
| P2 (partial) | trivial `-p` | **Confirmed** | `QUOTA_OK` / PONG-class replies, exit 0 |
| P3 (partial) | bogus model | **Confirmed** | error text `unknown model id`; exit 0 (not a failure signal) |
| P4 (partial) | stdin hang | **Refuted** (not mandatory) | docs: headless does not read piped stdin; smoke completed under pipe |
| P6 (partial) | shell under `--always-approve` | **Confirmed** | `shell.txt` = `SHELL_OK` on disk |
| P6 (partial) | shell under acceptEdits+always-approve | **Confirmed** (failure mode) | silent no-op, exit 0, empty tree; matches user-guide 22 flag caveat |

Incomplete at pack authoring: full numbered suite (filled by next entry).

---

## 2026-07-24 — grok 0.2.111 (trigger: new provider; full suite after pack write)

Scratch: `/home/nathanielramm/.cache/claude-tmp/sdd-grok-verify.iKqDwY` (+ home-dir
read-only re-probe). Kernel 6.17.0-35-generic, Landlock enforced.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | version + models | **Confirmed** | `0.2.111 (94172f2aa4) [stable]`; inventory only `grok-4.5` |
| P2 | trivial success | **Confirmed** | stdout `PONG`, exit 0 |
| P3 | bogus model | **Confirmed** | stderr `unknown model id`; **exit 1** (docs-aligned) |
| P4 | stdin not required | **Confirmed** | piped stdin → `P4OK`, exit 0 |
| P5 | flagless read | **Confirmed** | `XYZZY42` from `readtest.txt` |
| P6 | flagless write | **Confirmed** | `writetest.txt` = `HELLO` |
| P6 | file+shell under `--always-approve` | **Confirmed** | `ftool.txt`=`FTOOL_OK`, `shell.txt`=`SHELL_OK` |
| P6 | write under `--sandbox workspace` | **Confirmed** | `ws.txt`=`WS_OK` |
| P7 | workspace blocks home escape | **Confirmed** | cwd+`/tmp` ok; home `Permission denied`; `FsViolation` in sandbox-events |
| P7 | read-only blocks project writes | **Confirmed** (after correct CWD) | under `$HOME/grok-ro-probe-*`: write blocked, `FsViolation`; under `/tmp` write **allowed by design** (profile write set includes `/tmp`) |
| P8 | git commit under workspace | **Confirmed** | commit landed (`test commit`); first attempt failed on `~/.gnupg` GPG write, retry `--no-gpg-sign` ok — **not** controller-commits structural |
| P9 | effort valid | **Confirmed** | `--reasoning-effort low` → `OK` |
| P9 | effort invalid | **Confirmed** | exit 1; accepted list `high, medium, low` for this model |
| P10 | report-file | **Confirmed** | `p10-report.md` 548 bytes; stdout short summary — `report-transport: report-file` |
| P11 | json `.sessionId` | **Confirmed** | `sessionId` UUID in json object |
| P11 | acceptEdits footgun | **Confirmed** | `--permission-mode acceptEdits` shell → exit 0, `ae.txt` MISSING |
| P11 | resume sandbox mismatch | **Confirmed** | exit 1: cannot resume under `read-only` if created with `off` |
| Resume | codeword continue | **Confirmed** | `ZEBRA42` after `--resume` |
| Fork | `--fork-session` | **Confirmed** | new `sessionId` + `FORKED_OK` |
| P12 | inventory | **Confirmed** | only `grok-4.5` |
| P13 | known-defect reviewer | **Confirmed** | Important finding on `path.exists()` insufficient guard matches `expected-findings.md` |

**Promotions:** models.md Status → `verified` for all three tier rows; pack facts above
recorded; `verified-version` remains `0.2.111`.

## 2026-07-24 — grok 0.2.111 (trigger: effort matrix re-check)

`--reasoning-effort` / `--effort` against `grok-4.5` (trivial `-p Reply:OK`, `--always-approve`):

| Level | Exit | Notes |
| --- | --- | --- |
| (omit) | 0 | default menu value `high` |
| `low` | 0 | accepted |
| `medium` | 0 | accepted; `--effort` alias also 0 |
| `high` | 0 | accepted |

Matches `models_cache.json` `reasoning_efforts` menu for `grok-4.5`. Product docs list a wider canonical set; only the model menu is dispatchable.

## 2026-07-25 — plugin renamed to Swingle (v2.0.0)

The plugin `sdd-dispatch` is renamed `swingle` at v2.0.0 (`sdd-dispatch-marketplace` →
`swingle-marketplace`, skill `sdd-dispatch-verify` → `swingle-verify`, repository →
`discreteds/swingle`). Entries above predate the rename and keep the old names as
historical record. No pack facts or probe results changed in this release.

---

## 2026-07-31 — grok 0.2.117 (trigger: version bump from 0.2.111)

Run: drift-verify-grok-20260731-071645-3CB2C90C. macOS Darwin 25.4.0.
Scratch: `/tmp/grok-verify-JpkoZ`.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | version + models | **Confirmed** | `0.2.117 (f1c06093089f)`; inventory unchanged: only `grok-4.5` |
| P2 | trivial success | **Confirmed** | stdout `PONG`, exit 0 |
| P3 | bogus model | **Confirmed** | stderr `unknown model id`; exit 1 |
| P4 | stdin not required | **Confirmed** | piped stdin → `PONG`, exit 0 |
| P5 | flagless read | **Confirmed** | `XYZZY42` from `readtest.txt` |
| P6 | file write under `--always-approve` | **Confirmed** | `writetest.txt` = `HELLO` |
| P6 | shell under `--always-approve` | **Confirmed** | `cmdtest.txt` = `P6CMD` |
| P7 | workspace blocks home escape | **Confirmed** | cwd + `/tmp` ok; `$HOME` write blocked (`operation not permitted`) |
| P8 | git commit under workspace | **Confirmed** | commit landed on macOS without `--no-gpg-sign` (no GPG blocked); controller-commits still doctrine |
| P9 | effort valid (`low`, `medium`, `high`) | **Confirmed** | all accepted via `--reasoning-effort` and `--effort` alias; exit 0 |
| P9 | effort invalid | **Confirmed** | exit 1; accepted list `high, medium, low` (docs canonical set wider; model menu is binding) |
| P10 | report-file | **Confirmed** | `p10-report.md` 9562 bytes; stdout short summary — `report-transport: report-file` |
| P11 | json `.sessionId` | **Confirmed** | sessionId UUID in json object |
| P11 | acceptEdits footgun | **Confirmed** | `--permission-mode acceptEdits` shell → exit 0, `ae.txt` MISSING |
| P11 | resume sandbox mismatch | **Confirmed** | exit 1: "cannot resume this session under sandbox profile 'read-only' — it was created with 'workspace'" |
| P12 | inventory | **Confirmed** | only `grok-4.5`; no additions or removals |
| P13 | known-defect reviewer | **Confirmed** | `path.exists()` insufficient guard flagged at Important severity; matches expected-findings.md |

New capabilities confirmed (0.2.117):
- `streaming-messages-json` output format: Messages API JSONL, exit 0.
- `--resume` without value: resumes most recent session in cwd, exit 0.
- `--resume <title>` by name: documented (not probed separately — UUID paths tested).
- `--output-format streaming-json` `end` event carries `.sessionId` (confirmed; viable log-age-safe alternative to json).
- JSON output richer: `stopReason`, `usage`, `num_turns`, `total_cost_usd`, `total_cost_usd_ticks`, `requestId`, `thought`, `modelUsage` (key is CLI-internal name e.g. `grok-4.5-build` for dispatch model `grok-4.5`).
- `--max-turns`, `--tools`, `--disallowed-tools`, `--no-subagents`, `--no-plan`, `--worktree` flags: listed in docs; `--max-turns 1` accepted (exit 0); others not individually smoke-tested.
- Sandbox hook write-protection: `workspace`/`read-only`/`strict` now kernel-deny `~/.grok/hooks/` and `hooks-paths` writes.

**Issue #26 reconciliation:** `--output-format json` stdout-buffering confirmed on 0.2.117 (log-age stall signal fires prematurely on healthy runs). Resolution path confirmed: `--output-format streaming-json` streams line-by-line and carries `sessionId` on the `end` event. Pack updated with gotcha #10 and revised session-id guidance. Struct fix (manifest-level `stall-signal` transport-dependence) out of scope for this PR — proposal filed as comment on #26 for operator triage.

`verified-version` stamped `0.2.117` (matrix_green: all P1–P13 green; live dispatch included).
