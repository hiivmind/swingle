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

## 2026-07-29 — opencode 1.18.9 (trigger: version bump, drift from stamped 1.17.18)

Changelog reviewed: https://github.com/sst/opencode/releases, all entries 1.17.19–1.18.9.
Relevant Core entries: v1.18.2 "stopped subagents from launching nested subagents by
default"; v1.18.4 "respect provider-defined reasoning options instead of falling back to
the wrong reasoning controls"; v1.18.5 "fix MiniMax M3 thinking variant selection". No
entry touches stdin/TTY handling, permission defaults, or `-p`/positional argument
parsing. Auth mode this round: OpenCode Go (not Zen) — all six table models are already
`opencode-go/`-namespaced, so the table needed no auth-mode migration.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version/surface | New | 1.17.18 → 1.18.9; `opencode models` lists 16 `opencode-go/*` ids, up from 6 known-tracked; new since 2026-07-22: `glm-5.1`, `hy3`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m2.7`, `qwen3.6-plus` (watch-list candidates, not benchmarked this round — trigger was version bump, not model release) |
| P2 | Trivial dispatch | Confirmed | `opencode-go/deepseek-v4-flash` → PONG, exit 0, `build · deepseek-v4-flash` banner |
| P3 | Bogus model | Confirmed | `{"name":"UnknownError","data":{"message":"Unexpected server error...","ref":"err_9c9fe1f2"}}`, exit 1 |
| **P4** | **`< /dev/null` optional (2026-07-22 finding)** | **Refuted** | a TRUE never-closing stdin (mkfifo, held open) hung 60s with zero output, 2/2 reproductions; 3/3 control runs with `< /dev/null` completed normally in the same harness, ruling out the documented backgrounded-startup flakiness as the cause. The 2026-07-22 "no hang" finding was evidently tested against a stdin source that reached EOF, not a genuinely open one. **`< /dev/null` (or equivalent) is mandatory**, not optional — canonical dispatch template updated below. |
| P5 | Read, no flags | Confirmed | read `readtest.txt`, reported XYZZY42, exit 0 |
| P6 | Write (file tool), no flags | Confirmed | `writetest.txt` = `HELLO.` on disk, exit 0, narration accurate |
| P6 | Write (shell command), no flags | Confirmed | `cmdtest.txt` = `P6CMD` on disk, exit 0, narration accurate (contrast: claude 2.1.220 narrated false success on this same probe, issue #44) |
| P8 | Git commit in sandbox | Confirmed | `git log` shows `test commit` (3744e1f) on top of the seeded initial commit, exit 0 |
| P9 | `--variant` reasoning knob | Confirmed | `minimax-m3` (had a variant-selection fix in v1.18.5) accepted `--variant high` and silently accepted `--variant bogusvariantxyz` alike — both PONG, exit 0, no warning either way. The 1.18.5 fix appears to affect whether a valid variant takes effect, not validation; "never assume it took effect" stands. |
| **P11** | **`-p` collision "silently misfires" (2026-07-22 wording)** | **Refined** | `--help` still lists `-p, --password`; dispatching with `-p "<prompt text>"` now fails loudly — `Error: You must provide a message or a command`, exit 1 — rather than the ambiguous "silently misfires" the prior entry implied. It is a footgun (wrong prompt swallowed into an auth field) but the failure mode is a clean, catchable error, not a silent wrong-behavior success. |
| P10 | Output contract (report-file) | Confirmed | task-specified `REPORT.md` held the full 6-line content; stdout stayed to banner + `DONE` (109 bytes total) — matches `report-transport: report-file` |
| P12 | Tier-table model dispatch | Confirmed | all 6 current table models (`deepseek-v4-flash`, `minimax-m3`, `qwen3.7-plus`, `deepseek-v4-pro`, `kimi-k2.7-code`, `glm-5.2`) dispatched PONG, exit 0 |
| P13 | Reviewer known-defect benchmark | Not run | trigger was version bump, not model release; review-lane models (`deepseek-v4-pro`, `glm-5.2`) are provider-pinned ids, not CLI-version-dependent aliases (contrast claude's `opus`), so this CLI bump does not put their P13 qualification (2026-07-22) in question |

**Net**: pack re-stamped to 1.18.9. One genuine refutation (P4 — stdin protection is
mandatory, not optional; canonical dispatch template updated to always redirect stdin)
and one wording refinement (P11 — loud error, not silent misfire). No push rights on
`hiivmind/swingle`; committed locally and opening an upstream issue for the P4 finding
(dispatch-template-affecting, the substantive one) per the recording ladder.

