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
