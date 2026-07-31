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

## 2026-07-25 — plugin renamed to Swingle (v2.0.0)

The plugin `sdd-dispatch` is renamed `swingle` at v2.0.0 (`sdd-dispatch-marketplace` →
`swingle-marketplace`, skill `sdd-dispatch-verify` → `swingle-verify`, repository →
`discreteds/swingle`). Entries above predate the rename and keep the old names as
historical record. No pack facts or probe results changed in this release.

---

## 2026-07-31 — codex 0.146.0 (trigger: version bump from 0.144.4; second drift run after npm dependency refresh)

**Guidance:** `"Reading additional input from stdin..."` is now a startup banner regardless of stdin state. Do not treat its presence as evidence of an open stdin or imminent hang — the message is unconditional in 0.146.0+. `< /dev/null` remains mandatory; without it the process still hangs (P4 confirmed). See issue #58.

**Guidance (sdd, delegate, drift):** an in-sandbox `git commit` success is an **environment signal, not sandbox drift**: user execpolicy rules (`~/.codex/rules/*.rules`, `prefix_rule(..., decision="allow")` accumulated from interactive "always allow" approvals) run matching commands outside the sandbox, and matching is argv-prefix-shaped (`git commit` escapes; `git -C <path> commit` does not), so results vary with the argv the agent emits. Before treating any P8 result as a finding, record the machine's git-related allow rules. Controller-commits remains structural doctrine. See issue #75.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version & surface | **Confirmed** | codex-cli 0.146.0; models gpt-5.6-luna/terra/sol listed and dispatching; exec/review/resume subcommands present |
| P2 | Trivial dispatch / exit 0 | **Confirmed** | PONG, exit 0; unconditional stdin banner + hook lifecycle lines in stdout; final message PONG |
| P3 | Bogus model → HTTP 400 exit 1 | **Confirmed + refined** | `gpt-99-bogus-model` → `warning: Model metadata not found` + HTTP 400 exit 1; validation server-side |
| P4 | `< /dev/null` mandatory | **Confirmed** | without redirect: hung 30s (exit 124); banner printed then stalled on stdin read |
| P5 | Read without permission flags | **Confirmed** | secret word XYZZY42 returned; no approval prompt with workspace-write |
| P6-file | Write with workspace-write | **Confirmed** | writetest.txt created on disk (HELLO) |
| P6-cmd | Shell command with workspace-write | **Confirmed** | `echo P6CMD > cmdtest.txt` executed; cmdtest.txt verified on disk |
| P7 | Sandbox boundary | **Confirmed** | workspace ✓, `/tmp` ✓, `~/` BLOCKED ("patch rejected: writing outside of the project") |
| P8 | `.git` read-only by design | **Confirmed — apparent refutation was environment** | run 104507 observed git commit succeeding in both /tmp and non-/tmp workspaces and initially recorded a refutation (filed #75). Controller bisect (2026-07-31, same day): pristine `CODEX_HOME` (auth only) → commit fails on `.git/index.lock: Operation not permitted`; + project trust entries → fails; + full `config.toml` → fails; + `~/.codex/rules/` only → **succeeds**. Cause: `prefix_rule(pattern=["git", "commit"], decision="allow")` runs the command outside the sandbox. Argv-prefix matching explains the run-022733 vs run-104507 discrepancy (npm dep refresh exonerated). Default-environment claim stands. |
| P9 | `model_reasoning_effort` validated | **Confirmed** | `xhigh` accepted (new valid value); `bogus-effort` → HTTP 400 exit 1; enum confirmed: none, minimal, low, medium, high, xhigh, max |
| P10 | `-o <file>` = last message only | **Confirmed** | report file held final message only (1861 bytes for a multi-sentence response); stdout includes banner + hook lines + message |
| P11 | Argument footguns | **Confirmed** | prompt before flags handled correctly; hook lifecycle lines do not affect `-o <file>` contract |
| P12 | Model IDs | **Confirmed** | gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol all dispatching on 0.146.0 |
| P13 | Reviewer benchmark (terra) | **Green** | gpt-5.6-terra cited `path.exists()` insufficient guard + traceback instead of exit 2 at Important severity — passes qualification |

Pack updated: `verified-version` → 0.146.0, stdin banner description refined, reasoning effort enum updated (none/minimal/xhigh added), hook-lines note added, P8 `.git` read-only claim retained with a machine-local execpolicy-rules exception documented (controller bisect superseded this run's initial refutation before merge).

