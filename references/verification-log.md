# SDD Dispatch Verification Log

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](verification-protocol.md).

---

## 2026-07-22 — agy 1.1.4 (trigger: assertion review; prior notes from ~1.1.1)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P11 | `-p` eats next arg as prompt; flag after `-p` silently replaces task | **Confirmed** | `-p --model "Gemini 3.5 Flash (Low)"` → prompt became `--model`, model selection dropped, fell back to default (Claude Opus) |
| P2 | Exit code 1 even on success | **Refuted** (≥1.1.4) | trivial PONG → exit 0; bogus model → exit 1. Normal semantics |
| P5/P6 | Headless auto-denies every tool; even reads need `--dangerously-skip-permissions` | **Refuted** (≥1.1.4) | with NO flags: read succeeded AND write succeeded; no `permissions.allow` pre-seeded in `~/.gemini/antigravity-cli/settings.json`. Total behavior flip vs 1.1.1 |
| P10 | Document tasks divert to `brain/<id>/*.md`, stdout banner-only | **Confirmed** | 500-word doc → 1006-byte stdout banner; artifact at `brain/e373…/widget_cache_architecture.md` (3530 bytes) |
| P10 | Sweep command `find … -newermt '-10 minutes'` | **Refuted** (broken) | matched nothing with artifact present; `-mmin -10` works |
| P3 | `--model` takes display label verbatim | **Refined** | labels AND slugs (`gemini-3.5-flash-low`) both accepted; bogus name errors cleanly listing all models |
| P9 | `--effort low\|medium\|high` sets reasoning | **Refined** | works only with base slug (`gemini-3.5-flash --effort low`); **errors** with display label or effort-suffixed name ("--effort is not supported for model …") |
| P1/P12 | Model inventory | **New** | `gemini-3.6-flash-{low,medium,high}` present (3.6-flash-low verified dispatching); no Flash-Lite exposed (`gemini-3.5-flash-lite` and `-3.6-` both rejected); only Pro is `gemini-3.1-pro-{low,high}` |

Not tested: `< /dev/null` hang (kept as-is), silent failure when unauthenticated (couldn't de-auth).

## 2026-07-22 — opencode 1.17.18 (trigger: assertion review)

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

## 2026-07-22 — codex 0.144.3 (trigger: assertion review)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P4 | `< /dev/null` mandatory | **Confirmed** | open pipe → "Reading additional input from stdin…", hung until killed (143). Help text: piped stdin is appended to prompt, read to EOF |
| P7 | `workspace-write` sandbox contains writes | **Confirmed + refined** | `~/` write blocked ("read-only file system"); **`/tmp` writable by design**; workspace writable |
| P8 | `.git` read-only "intermittently" | **Refined** (by design) | fresh repo: working-tree file created, `git commit` failed deterministically on `.git/index.lock: Read-only file system` |
| P10 | `-o <file>` = last message only | **Confirmed** | report file contained exactly the final reply |
| P3 | Exit codes / validation | **New** | 0/1 normal; bogus model → HTTP 400 (server-side, ChatGPT account), exit 1 |
| P9 | `model_reasoning_effort` validated | **New** | `low` accepted; `bogus` → HTTP 400, exit 1 — validated, unlike opencode `--variant` |
| P12 | Model IDs | **Confirmed** | `gpt-5.6-luna`/`terra`/`sol` all verified dispatching |

Not tested: `--dangerously-bypass-approvals-and-sandbox` blocked by auto-mode classifier
(a harness-side claim, not a codex behavior).

**Cross-CLI synthesis (2026-07-22):** codex fails loud and is contained (real sandbox,
server-validated knobs); agy and opencode fail quiet and are unconstrained (flag-free
read/write, silent knob failures, agy's silent `-p`/auth/brain-file traps). Codex is the
default lane for writes and structured reviews; the controller hard gate is the only real
safety boundary on all three.
