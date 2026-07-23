# SDD Dispatch Verification Log

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-22 — agy 1.1.4 (trigger: assertion review; prior notes from ~1.1.1) (from archive/v1.1)

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

Not tested: `< /dev/null` hang (kept as-is), silent failure when unauthenticated (couldn't de-auth). (from archive/v1.1)

## 2026-07-23 — agy 1.1.5 (trigger: version bump discovered mid-smoke; incomplete — dispatch blocked)

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P5/P6 | ≥1.1.4 headless reads/writes freely, no permission flags needed | **Refined (latent gap since 1.1.4)** | flagless implement dispatch (`gemini-3.6-flash-low`) exited 0 with ZERO work: no report, empty diff, stdout = "no output produced — a tool required the \"command\" permission that headless mode cannot prompt for, so it was auto-denied. Add an allow-rule under permissions.allow in settings.json (e.g. command(<target>)). Alternatively, re-run with --dangerously-skip-permissions". Vendor changelog: **1.1.4 (2026-07-18) made headless runs honor persisted settings.json policies** (permissions, file access, sandbox, auto-execution) — the 07-22 P5/P6 pass only probed FILE read/write (allowed by persisted policy); shell `command` execution is what the policy gates. Not a 1.1.5 flip — a 1.1.4 change our probe surface missed |
| P2 | Exit codes signal failure | **Refined** | permission-starved run still exits **0** — exit code alone is NOT evidence of work done; the controller's diff-after/report-exists gate is what caught it |
| P1 | Version | **New** | `agy --version` → 1.1.5. Changelog 1.1.5 (2026-07-21): `/effort` command, `--effort` launch flag for reasoning-effort variants, **stable user-facing model slugs**, `model` option in custom agent frontmatter |

Incomplete: re-dispatch with `--dangerously-skip-permissions` (and the settings.json
allow-rule route) blocked by the controlling harness's permission classifier — needs user
authorization. `verified-version` stays "1.1.4" until a 1.1.5 dispatch verifies end-to-end;
run `sdd-dispatch-verify agy` once unblocked. Surfaces to verify then:
`permissions.allow` / `command(<target>)` allow-rules in `settings.json` (finer-grained
than the skip-all flag — likely the better canonical template if it works headless), and
the P5/P6 probe must now include a shell-command tool use, not just file read/write —
that blind spot is how the 1.1.4 gate went unnoticed.
Vendor changelog (add to every verify round): https://antigravity.google/changelog?tab=cli

**Addendum (same day, after user adopted the settings.json route):** `permissions.allow`
baseline VERIFIED as the operating mode on 1.1.5 — with command allow-rules in
`~/.gemini/antigravity-cli/settings.json` (grammar per official docs: `action(target)`,
per-token anchored regex, Deny > Ask > Allow, `command(*)` namespace wildcard), a flagless
headless implement dispatch (`gemini-3.6-flash-low`) ran `uv`/`pytest`, wrote the tree,
and reported DONE with the controller gate re-running 4/4 green. Baseline snippet and
portability caveats recorded in pack.md ("Headless permission baseline"). The
`--dangerously-skip-permissions` route was NOT exercised (harness classifier blocks it);
it remains the documented zero-setup fallback.

**Resume channel verified (same day):** a deliberately underspecified task returned
NEEDS_CONTEXT (clean stop, zero tree writes, questions in the status block); resuming with
`agy --conversation <id> --add-dir <repo> --print-timeout 10m -p "<answers>" < /dev/null`
continued the SAME conversation — the agent retained its brief and codebase context,
implemented against the supplied answers, and reported DONE with the controller gate green
(11/11). Conversation id source confirmed: newest directory under
`~/.gemini/antigravity-cli/brain/` immediately after dispatch matches the resumable id.
Also verified on 1.1.5 this run: `gemini-3.6-flash-low` and `gemini-3.6-flash-medium`
dispatch (effort-suffixed slugs, no `--effort` flag), print-mode buffering unchanged
(status block arrives at completion), detached-wrapper + marker pattern, reviewer
read-only intent held under clean-tree/diff-after.
Machinery notes from this smoke (v1.2.0, first agy-lane run): resolver walk, trust gate,
detached wrapper + marker + Monitor, and the process+print-timeout liveness contract all
behaved; the wrapper survived, marker fired, and the gate caught the silent no-op.
