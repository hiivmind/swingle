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

## 2026-07-23 — delegate-skill post-plan smokes (v1.3.0, agy lane)

Three live smokes of the new `delegate` skill on agy 1.1.5 (`gemini-3.6-flash-low`
worker/reader, `gemini-3.6-flash-medium` reviewer). All three passed; four behavioral
findings recorded.

**Finding 1 — a denied shell command can abort the whole run, and the gate is what
catches it.** Smoke A (read-lane explore) attempt 1 returned exit 0 with only the
auto-deny banner and NO report: the reader reached for a shell command outside the
allow-list and stopped rather than falling back to file reads. The read-lane evidence
gate (report must exist) caught it correctly — exit 0 is never evidence. Attempt 2, with
the prompt stating that shell execution is denied and directing the agent to file-read
tools plus a named file list, produced a fully cited, accurate report. **Operating rule:
every agy dispatch prompt should carry an explicit "shell is denied, use file tools,
continue rather than stop on a denial" clause.**

**Finding 2 — the documented baseline's git allow-rule does not cover exploration.**
`command(git (status|diff|log|show|rev-parse|ls-files|branch))` excludes `git grep`, the
natural first move for a codebase-explore role, and there is no rule matching a repo-local
script path (`./scripts/codex-smoke`), so plan-mandated gate steps were auto-denied on
every implement dispatch of this run. Harmless under doctrine (the controller re-runs all
gates and never trusts agent-reported results), but it means **agent-side gate steps
should not be dispatched to agy at all** — hand them to the controller.

**Finding 3 — the cheapest tier does not reliably emit the mandated status block.**
`gemini-3.6-flash-low` workers in the supervised batch (jobs 003–005) ignored the
contract's four-status vocabulary (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED)
and emitted a prose `## Status` markdown section instead. `gemini-3.6-flash-medium`
emitted the exact block every time (jobs 001, 002 and both reviews). Consequence: any
controller or supervisor that parses status by keyword must treat a missing block as
unknown-and-escalate, never as success — and status-block fidelity is a reason to prefer
the standard tier when a machine reads the status.

**Finding 4 — resume channel re-verified on both worker and reviewer threads.**
`agy --conversation <id>` resumed the worker for a fix round (retained its own prior work
— "the mul() work you just completed" — and made only the requested change, HEAD
unchanged) and separately resumed the ORIGINAL reviewer with a versioned package
(`002-review-package-2.md`); the reviewer verified its own finding as resolved rather than
re-deriving the review. Conversation ids taken from newest-first
`~/.gemini/antigravity-cli/brain/` under strictly serialized dispatch, per the pack's
concurrency caveat.

Also confirmed this run: pre-commit reviewer containment (artifact-only scratch directory
outside the target repo) held — the target tree after the review carried exactly the
worker's two modified files and nothing else; and the write-lane evidence gate
(HEAD-unchanged + porcelain + stat) held across all five delegate jobs.
