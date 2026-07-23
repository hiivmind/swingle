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

Incomplete: full numbered suite, P7–P13, resume/fork live, json `.sessionId` capture,
review-lane P13.
