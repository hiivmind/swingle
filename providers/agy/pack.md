---
schema-version: 1
id: agy
cli: agy
verified-version: "1.1.5"
version-argv: ["agy", "--version"]
resume-argv: ["agy", "--conversation", "{session_id}"]
session-source: conversation-id
stall-signal: process+print-timeout
sandbox: none
---

## Cross-CLI comparison — agy cells (from archive/v1.1)

| Property | agy 1.1.4 |
| --- | --- |
| Prompt argument | `-p "<PROMPT>"` — **must be last arg** |
| `< /dev/null` needed | **Yes** — hangs |
| Sandbox | None — no isolation; file tools pass under default policy, shell commands gated by the permission baseline below |
| Permission flags | **Headless honors persisted `settings.json` policies since 1.1.4** (per vendor changelog): file read/write passes under default policy, but shell `command` use is auto-denied (exit 0, zero work) unless `permissions.allow` has a `command(<target>)` rule or `--dangerously-skip-permissions` is passed — see 2026-07-23 verification-log entry |
| Changelog | https://antigravity.google/changelog?tab=cli — read on every version bump before probing |
| Exit codes | Normal 0/1 (≥1.1.4; earlier versions reportedly returned 1 on success) |
| Model validation | Errors cleanly, lists available models |
| Reasoning-effort control | Effort-in-name (`-low/-medium/-high` slug or `(Low)` label) **or** base slug + `--effort` — mixing both **errors** |
| Output contract | stdout, **but** document tasks divert to brain files (see gotchas) |
| Auth | OAuth — must run `agy` interactively once; headless fails **silently** if signed out |

### Resume — a kill is a checkpoint, not a restart (from archive/v1.1)

All three CLIs can continue a killed/expired session; **resume, don't re-dispatch from
scratch** after any backstop kill or hang-kill where partial progress is real:

| CLI | Resume |
| --- | --- |
| agy | `agy -c` (most recent) / `agy --conversation <id>` |

Working-tree progress survives the kill too (agents write as they go) — `git diff` before
resuming to see what's already landed.

## agy (verified v1.1.4, 2026-07-22) (from archive/v1.1)

### Dispatch (from archive/v1.1)

```bash
# -p "<PROMPT>" must be the LAST argument
agy --model gemini-3.6-flash --effort <low|medium|high> \
  --add-dir <repo> --print-timeout 5m -p "<PROMPT>" < /dev/null
```

### Verified behavior (from archive/v1.1)

- agy print mode buffers output — a log-age watch WOULD kill healthy agy runs. Use
  process existence plus `--print-timeout` as the liveness signal and backstop.
- **`-p` eats the next argument as the prompt.** A flag placed after `-p` becomes the prompt
  *and the real task and model selection are silently dropped* (verified: fell back to the
  default model, Claude Opus, and answered the flag text). Always put `-p "<PROMPT>"` last.
- ~~**No permission gate on ≥1.1.4**: headless runs read **and write** freely with no
  flags.~~ **Superseded 2026-07-23**: this held only for FILE tools — 1.1.4 made headless
  honor persisted `settings.json` policies and shell `command` use is auto-denied without
  an allow-rule (see "Headless permission baseline" below). No read-only tier exists.
  (On ≤1.1.1 headless auto-denied every tool — permission behavior has now shifted at
  every patch release; re-verify on every version bump.)
- **Document-shaped tasks divert output**: "produce a document" prompts write the answer to
  `~/.gemini/antigravity-cli/brain/<conversation-id>/*.md` and print only a banner to stdout.
  Mitigations, in order:
  1. Always instruct: *"output your full answer inline as your final message; do not write any file."*
  2. If stdout is banner-only, sweep before declaring failure:
     ```bash
     find ~/.gemini/antigravity-cli/brain -name '*.md' -mmin -10 \
       -not -path '*/.system_generated/*' | xargs ls -t | head -1
     ```
     Use `-mmin`, **not** `-newermt '-10 minutes'` — that form silently matches nothing.
- **The artifact tool CANNOT write to the workspace — steer report writes explicitly**
  (verified 2026-07-23). agy's artifact tool rejects any path outside
  `~/.gemini/antigravity-cli/brain/<conversation-id>/`
  (`is not a valid artifact path`). When a dispatch says "write your report to
  `<workspace path>`" and the model reaches for the artifact tool, it errors, falls back to
  **Bash** to write the file, print mode soft-denies that confirmation, and the run
  **aborts with exit 0 and no report**. The tool choice is nondeterministic, so this fails
  intermittently. **Every agy dispatch naming a report path must carry:**
  *"Write your full report to `<path>` using your ordinary workspace FILE-WRITE tool. That
  path is a normal workspace file, NOT an artifact — do not use the artifact tool for it,
  and do not shell out to write it."*
  This steering is **mechanistically targeted but NOT statistically verified**: a 19-run
  controlled trial (2026-07-23) gave 10/10 steered vs 7/9 unsteered — Fisher one-tailed
  p = 0.21, not significant, because the base failure rate is only ~22%. Carry it (it is
  free and addresses the exact rejection seen in the transcript), but do not treat it as a
  guarantee.
  **The reliable fix is structural: skip agent-side file writing entirely** and take the
  FULL report as the captured final message (the enforced-read-only output protocol). That
  cannot hit the artifact path at all, so it removes the failure mode instead of reducing
  its probability. Prefer it for agy read-lane dispatches.
- Exit codes normal on ≥1.1.4 (0 success, 1 error). Bogus model → clean error listing all
  available models.
- **Model naming**: display label verbatim (`"Gemini 3.6 Flash (Low)"`) or slug
  (`gemini-3.6-flash-low`) both accepted. Effort: baked into the name **or** base slug +
  `--effort low|medium|high`; combining `--effort` with an effort-suffixed name **errors**
  (`--effort is not supported for model "Gemini 3.5 Flash"` — labels always carry effort).
- **Auth is OAuth**: run `agy` once interactively (creds → `~/.gemini/`); headless fails
  *silently* when signed out.
- `< /dev/null>` mandatory (hang, as codex).
- One prompt per turn — no conversation batching in print mode; `--print-timeout` bounds the wait.

## Headless permission baseline (required since 1.1.4)

Headless agy honors the persisted permission policy in
`~/.gemini/antigravity-cli/settings.json`; unconfigured actions default to Ask, which
headless auto-denies (exit 0, zero work, banner on stdout). **The canonical operating mode
is an allow/deny baseline in that file** — rule grammar is `action(target)`, one
whitespace-separated anchored-regex token each, precedence Deny > Ask > Allow, `command(*)`
wildcards a whole namespace:

```json
"permissions": {
  "allow": [
    "command(uv)", "command(python3)", "command(python)", "command(pytest)",
    "command(git (status|diff|log|show|rev-parse|ls-files|branch))",
    "command(ls)", "command(cat)", "command(echo)", "command(mkdir)", "command(touch)",
    "command(cp)", "command(mv)", "command(sed)", "command(grep)", "command(rg)",
    "command(find)", "command(head)", "command(tail)", "command(wc)", "command(diff)",
    "command(chmod \\+x)", "command(make)", "command(npm (test|run))", "command(node)"
  ],
  "deny": [
    "command(sudo)", "command(rm -rf? /)", "command(git push)", "command(git commit)",
    "command(curl)", "command(wget)", "command(ssh)"
  ]
}
```

Portability facts every installer must know:

- **This file is machine-local and user-global** — the plugin cannot ship it. Without the
  baseline, the first dispatch on a fresh machine silently no-ops; only the controller's
  diff-after/report-exists gate catches it.
- **Readiness probe (before the FIRST agy dispatch of a session)**: verify the baseline
  exists — `grep -q 'permissions' ~/.gemini/antigravity-cli/settings.json` — and on a miss
  STOP and hand the user this section instead of dispatching.
- **The rules apply to the user's interactive agy sessions too**: `allow` auto-approves
  there as well, and the `git commit`/`git push` denies (deliberate — they mechanically
  enforce the controller-commits doctrine) will also block interactive commits. A user who
  wants agy to commit interactively must scope their own baseline accordingly.
- **Zero-setup alternative**: `--dangerously-skip-permissions` per dispatch — no config
  touch, but auto-approves *everything* and forfeits the deny-list containment; treat it
  as the fallback, not the mode.
- A denied command surfaces as the silent-no-op signature above; if a legitimately needed
  command is missing from the baseline, extend the allow list and record it here.

## Canonical dispatch template

```bash
agy --model <resolvable-model-id> --add-dir <repo> --print-timeout <t> -p "<PROMPT>" < /dev/null
```

**Effort XOR rule:** the resolvable model IDs already carry their effort suffix, so do
not pass `--effort` with this template. Use either an effort-suffixed model ID **or** a
base model slug with `--effort <low|medium|high>`, never both.
