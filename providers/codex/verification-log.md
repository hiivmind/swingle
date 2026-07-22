# SDD Dispatch Verification Log

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-22 — codex 0.144.3 (trigger: assertion review) (from archive/v1.1)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P4 | `< /dev/null>` mandatory | **Confirmed** | open pipe → "Reading additional input from stdin…", hung until killed (143). Help text: piped stdin is appended to prompt, read to EOF |
| P7 | `workspace-write` sandbox contains writes | **Confirmed + refined** | `~/` write blocked ("read-only file system"); **`/tmp` writable by design**; workspace writable |
| P8 | `.git` read-only "intermittently" | **Refined** (by design) | fresh repo: working-tree file created, `git commit` failed deterministically on `.git/index.lock: Read-only file system` |
| P10 | `-o <file>` = last message only | **Confirmed** | report file contained exactly the final reply |
| P3 | Exit codes / validation | **New** | 0/1 normal; bogus model → HTTP 400 (server-side, ChatGPT account), exit 1 |
| P9 | `model_reasoning_effort` validated | **New** | `low` accepted; `bogus` → HTTP 400, exit 1 — validated, unlike opencode `--variant` |
| P12 | Model IDs | **Confirmed** | `gpt-5.6-luna`/`terra`/`sol` all verified dispatching |

Not tested: `--dangerously-bypass-approvals-and-sandbox` blocked by auto-mode classifier
(a harness-side claim, not a codex behavior).

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
  archived dispatch reference liveness section updated.

---

## 2026-07-23 — reviewer-thread continuity via exec resume (v1.2.0 execution run)

Re-reviews resumed on the original reviewer's session worked across five rounds in one
run: two task-review fix loops and a three-round final review (findings → consolidated
fix → verify → residual finding → verify), each round citing its own prior findings.
Session id from exec output; overrides passed as `-c` keys only (see resume prose above).
Verdict continuity held — the resumed reviewer confirmed or narrowed its own findings
rather than re-deriving the review.
