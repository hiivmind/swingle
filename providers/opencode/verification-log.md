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

