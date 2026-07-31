# SDD Dispatch Verification Log

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-22 — opencode 1.17.18 (trigger: assertion review) (from archive/v1.1)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P2 | `opencode run --auto -m <model> --dir <repo> "prompt"` works | **Confirmed** | PONG, exit 0; small `build · model` banner |
| P4 | `< /dev/null` needed | **Refuted** | ran fine on open stdin under timeout 90 — no hang |
| P5/P6 | `--auto` required for writes | **Refuted** | with NO permission config and NO `--auto`: read, write, and shell `echo > file` all succeeded |
| P3 | Exit codes / validation | **New** | 0 success; bogus model → JSON error (`"ref": "err_…"`), exit 1 |
| P11 | `-p` collision | **New** | `-p` = basic-auth **password**; prompt is positional — agy habit crossover trap |
| P9 | `--variant` reasoning effort | **New** | `--variant high` accepted; `--variant bogusvariant` **silently ignored** (no error) — unvalidated |
| P12 | Tier-table model IDs | **Confirmed** | all six IDs exist under `opencode-go/`; new arrivals `kimi-k3`, `grok-4.5`, `qwen3.7-max`; `deepseek-v4-flash-free` only under `opencode/` |
| P12 | Gemini Flash-Lite reachability | **New** | `opencode/gemini-3.5-flash-lite` verified dispatching (LITETEST, exit 0); `opencode/gemini-3.6-flash` listed |

## 2026-07-22 — smoke run 2 (pkill-self-kill finding 2 — contains provider invocation strings) (from archive/v1.1)

2. **`pkill` self-kill from a dispatching shell**: a wrapper shell whose command line
   embeds the dispatch string (`bash -c '… opencode run …'`) matches
   `pkill -f '[o]pencode run'` — the bracket trick does not protect it. The shell killed
   itself before launching (observed exit 144/125 pair). Rule: from any shell that also
   dispatches, kill by RECORDED PID only, never by pattern.

## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (opencode findings 1 and 5) (from archive/v1.1)

1. **Intermittent zero-output startup hang on backgrounded `opencode run`** — process
   alive, log 0 bytes forever, exit codes useless. ~5 occurrences in a ~40-min window
   (22:46–23:18+), hitting `-s` resume, `--fork`, and cold dispatches alike; every
   FOREGROUND run in the same window (incl. `--dir`-scoped PONG probes) succeeded
   instantly. Eliminated: session-specific state, wedged daemon, per-project `--dir`
   state. Unresolved — suspect interaction between opencode startup and non-tty/piped
   stdio under the background harness. Mitigations now in the skill: 0-byte log past the
   5-min threshold = stall (kill/checkpoint/retry); after 2 consecutive channel stalls on
   a sub-2k-token fix, drop to inline (flavour rules already price this); foreground
   dispatch is the fallback lane for short tasks.

5. `opencode session list` is the session-id source — ids are NOT printed in plain-text
   run logs. Resume (`-s`) and `--fork` both function when the channel isn't hanging
   (finding 1); one resume hang recovered on plain retry.

## 2026-07-22 — smoke run 2 (What worked: NEEDS_CONTEXT-resume and reviewer-quality bullets — name opencode models, excluded from core by purity) (from archive/v1.1)

**What worked (verified in anger):**
- `NEEDS_CONTEXT` → resume channel: `qwen3.7-plus` refused to guess the missing format
  spec — STATUS: NEEDS_CONTEXT, zero tree writes, precise gap named. Controller committed
  the missing doc and resumed with `-s <id>`; implementation then matched the spec
  byte-for-byte (verified with `cat -A`).
- Reviewer quality at the deepseek-v4-pro tier: caught (1) a tie-breaking test whose input
  contained no tie — mandatory behavior untested while all tests passed; (2) traceback on
  directory/permission paths where the spec required stderr + exit 2. Both genuine, both
  file:line-cited. Re-reviews via reviewer-session resume worked.

## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (nemotron addendum context) (from archive/v1.1)

**Addendum (same day):** user flagged that during the nemotron implementer probe the
controller could neither answer "is it still running?" nor cut the stall early — the
foreground call blocked both, and prior watchers only notified rather than killed.
Doctrine upgraded (v1.1.3): SELF-REAPING wrapper is the standard dispatch shape — CLI
backgrounded inside the wrapper, `$!` recorded, wrapper runs the stall watch and kills at
threshold itself. Foreground reserved for sub-minute probes only.

## 2026-07-22 — model evaluation: `opencode/nemotron-3-ultra-free` (from archive/v1.1)

User-proposed for transcription + review lanes ("strong and completely free"). Probed
same-day on the smoke2 repo. **Rejected for both lanes.**

- Namespace: `opencode/` (ALL five `-free` tiers live there, not `opencode-go/`:
  deepseek-v4-flash-free, laguna-s-2.1-free, mimo-v2.5-free, nemotron-3-ultra-free,
  north-mini-code-free). PONG probe: dispatches fine, exit 0.
- **Reviewer probe (known-defect benchmark):** given the exact contract/brief/diff on
  which deepseek-v4-pro had flagged the path.exists() directory-traceback as Important,
  nemotron returned a clean "Approved" with one weak Minor — **missed the planted
  defect**. False-clean is the costliest reviewer failure; benchmark method (re-review a
  diff with a known caught defect) is cheap and now the standard for reviewer candidates.
- **Implementer probe:** Task-3 README (small, fully-briefed) — hit the 480s foreground
  backstop with ZERO output: no README, no report, clean tree. Same task class other
  models finish in 2–3 min.
- **Data caveat (Zen docs):** free tier is "trial use only"; prompts logged and may be
  used to improve NVIDIA products/services — disqualifying for proprietary code even if
  quality were good. Applies presumptively to all `-free` tiers.

## 2026-07-25 — plugin renamed to Swingle (v2.0.0)

The plugin `sdd-dispatch` is renamed `swingle` at v2.0.0 (`sdd-dispatch-marketplace` →
`swingle-marketplace`, skill `sdd-dispatch-verify` → `swingle-verify`, repository →
`discreteds/swingle`). Entries above predate the rename and keep the old names as
historical record. No pack facts or probe results changed in this release.

## 2026-07-31 — opencode 1.18.10 (trigger: automated drift-verify, version bump from stamped 1.17.18)

Changelog reviewed: https://github.com/sst/opencode/releases, entries v1.18.9–v1.18.10.
Both are almost entirely Desktop-app / MCP-client-compat / Modal-model-discovery
changes; no entry touches headless CLI dispatch, stdin/TTY handling, permission
defaults, or argument parsing. `develop`'s pack.md was still on the pre-refutation
1.17.18 text at the start of this round (the 1.18.9 re-verification — PR #49 — targets
`main` and had not merged), so this round independently re-confirms and carries the P4
and P11 corrections forward for `develop`.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version/surface | New | 1.17.18 → 1.18.10; `opencode models` lists 17 `opencode-go/*` ids (new since 2026-07-29: `gpt-5.6-luna`) and 7 `opencode/*` free-tier ids (new: `big-pickle`, `ling-3.0-flash-free`) |
| P2 | Trivial dispatch | Confirmed | `opencode-go/deepseek-v4-flash` → PONG, exit 0, `build · deepseek-v4-flash` banner (after one-time China-hosting workspace opt-in — see P2-gate finding below) |
| **P2-gate** | **`opencode-go/deepseek-v4-flash` dispatch prerequisite** | **New** | on this workspace, first dispatch errored immediately: `Error: The latest version of this model is only available hosted in China and requires explicit opt in: <workspace>/go`, exit 1, zero work. Reproduced identically on retry before opt-in; resolved after the workspace owner opted in at that URL — model then dispatched normally. Not a code defect or billing issue (a separate `Insufficient balance` error was seen and resolved independently mid-round via account top-up, confirming the two are distinct failure modes). **Guidance (transcription/explore):** confirm this opt-in is granted before relying on unattended automated dispatch of this model on a new workspace. |
| P3 | Bogus model | Confirmed | `{"name":"UnknownError","data":{"message":"Unexpected server error...","ref":"err_b4bf35fe"}}`, exit 1 |
| P4 | `< /dev/null` mandatory (2026-07-29 refutation) | Confirmed | a TRUE never-closing stdin (mkfifo, held open) hung 60s+ with zero output; control run with `< /dev/null` completed normally (PONG, exit 0) in the same session. Persists two patch versions later; see issue #45 reconciliation comment. |
| P5 | Read, no flags | Confirmed | read `readtest.txt`, reported XYZZY42, exit 0 |
| P6 | Write (file tool), no flags | Confirmed | `writetest.txt` = `HELLO` on disk, exit 0, narration accurate |
| P6 | Write (shell command), no flags | Confirmed | `cmdtest.txt` = `P6CMD` on disk, exit 0, narration accurate |
| P8 | Git commit in sandbox | Confirmed | `git log` shows `test commit` (2cba4c8) on top of the seeded initial commit, exit 0 |
| P9 | `--variant` reasoning knob | Confirmed | `minimax-m3` accepted `--variant high` (exit 0) and silently accepted `--variant bogusvariantxyz` alike (exit 0, no warning) — never assume a variant took effect |
| P10 | Output contract (report-file) | Confirmed | task-specified `REPORT.md` held the full 6-line content; stdout stayed to banner + `DONE` (102 bytes total) — matches `report-transport: report-file` |
| P11 | `-p` collision (2026-07-29 refinement) | Confirmed | `-p "<prompt>"` still fails loudly — `Error: You must provide a message or a command`, exit 1 — not a silent misfire |
| P12 | Tier-table model dispatch | Confirmed | all 6 current table models (`deepseek-v4-flash`, `minimax-m3`, `qwen3.7-plus`, `deepseek-v4-pro`, `kimi-k2.7-code`, `glm-5.2`) dispatched PONG, exit 0. `kimi-k2.7-code` hit one zero-output stall (60s backstop) then succeeded on immediate retry with the identical prompt — consistent with the existing "intermittent zero-output startup hang" doctrine (2026-07-22), not a new/distinct signature (see issue #51 reconciliation comment) |
| P12 | New-model dispatch check | Confirmed | `opencode-go/gpt-5.6-luna`, `opencode/big-pickle`, `opencode/ling-3.0-flash-free` all dispatched PONG, exit 0 (listed → verified) |
| P13 | Reviewer known-defect benchmark | Not run | trigger was a version bump, not a model release; review-lane models (`deepseek-v4-pro`, `glm-5.2`) are provider-pinned ids, not CLI-version-dependent aliases, so this bump does not put their P13 qualification (2026-07-22) in question |
| P7 | Sandbox escape | N/A | pack declares `sandbox: none` — no sandbox claimed to test |

**Net**: pack re-stamped to 1.18.10. No new regressions beyond the already-standing P4
probe (which already covers stdin-hang regressions on every future round — no new
probe proposal needed). One new prerequisite documented (P2-gate: China-hosting
opt-in for `deepseek-v4-flash`) as operating guidance, not a bug. Three new models
confirmed dispatching, added to the watch list. Issues #45 and #51 (both "Awaiting
verifier") reconciled: #45 reproduced and corroborated at 1.18.10; #51 left
inconclusive — the specific triggering prompt wasn't available to re-test.

