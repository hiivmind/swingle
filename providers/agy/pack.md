---
schema-version: 1
id: agy
cli: agy
verified-version: "1.1.9"
version-argv: ["agy", "--version"]
resume-argv: ["agy", "--conversation", "{session_id}"]
session-source: conversation-id
stall-signal: process+print-timeout
report-transport: captured-output
sandbox: none
---

## Cross-CLI comparison — agy cells

| Property | agy |
| --- | --- |
| Prompt argument | `-p "<PROMPT>"` — position unrestricted; flags after `-p` parse correctly |
| `< /dev/null` needed | Not required (harmless; keep for consistency with other packs) |
| Sandbox | None — no isolation; file tools pass under default policy, shell commands gated by the permission baseline below |
| Permission flags | **Headless honors persisted `settings.json` policies** (per vendor changelog): file read/write passes under default policy, but shell `command` use is auto-denied (exit 0, zero work) unless `permissions.allow` has a `command(<target>)` rule or `--dangerously-skip-permissions` is passed — see the pack's verification log |
| Changelog | https://antigravity.google/changelog?tab=cli — read when re-verifying (`swingle-verify`, maintenance) or when triaging a drift-triggered failure; agy's permission behaviour is patch-volatile |
| Exit codes | Normal 0/1 |
| Model validation | Errors cleanly, lists available models |
| Reasoning-effort control | Effort-in-name (`-low/-medium/-high` slug or `(Low)` label) **or** base slug + `--effort` — mixing the same effort level is harmless; conflicting levels error |
| Output format | `--output-format text` (default) / `json` / `stream-json`: `json` returns `{"conversation_id":…,"status":"SUCCESS","response":…,"usage":{"input_tokens":…,"output_tokens":…,"total_tokens":…},"num_turns":…}` — token telemetry is available through this flag |
| Output contract | stdout, **but** document tasks divert to brain files (see gotchas) |
| Auth | OAuth — must run `agy` interactively once; headless fails **silently** if signed out |

### Resume — a kill is a checkpoint, not a restart

All three CLIs can continue a killed/expired session; **resume, don't re-dispatch from
scratch** after any backstop kill or hang-kill where partial progress is real:

| CLI | Resume |
| --- | --- |
| agy | `agy -c` (most recent) / `agy --conversation <id>` |

Working-tree progress survives the kill too (agents write as they go) — `git diff` before
resuming to see what's already landed.

## agy

### Dispatch

```bash
agy --model gemini-3.6-flash --effort <low|medium|high> \
  --add-dir <repo> --print-timeout 5m -p "<PROMPT>" < /dev/null
```

### Verified behavior

- agy print mode buffers output — a log-age watch WOULD kill healthy agy runs. Use
  process existence plus `--print-timeout` as the liveness signal and backstop.
- **Headless permission baseline:** file read/write passes under the default policy, while
  shell `command` use is auto-denied unless an allow-rule is present. No read-only tier
  exists. Treat version drift as advisory and record channel-class failures through the
  verification protocol (see the pack's verification log).
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
- **The artifact tool CANNOT write to the workspace — steer report writes explicitly.**
  agy's artifact tool rejects any path outside
  `~/.gemini/antigravity-cli/brain/<conversation-id>/`
  (`is not a valid artifact path`). When a dispatch says "write your report to
  `<workspace path>`" and the model reaches for the artifact tool, it errors, falls back to
  **Bash** to write the file, print mode soft-denies that confirmation, and the run
  **aborts with exit 0 and no report**. The tool choice is nondeterministic, so this fails
  intermittently. **Every agy dispatch naming a report path must carry:**
  *"Write your full report to `<path>` using your ordinary workspace FILE-WRITE tool. That
  path is a normal workspace file, NOT an artifact — do not use the artifact tool for it,
  and do not shell out to write it."*
  This steering targets the documented failure mode but is not a guarantee; see the pack's
  verification log for the evidence.
  **The reliable fix is structural: skip agent-side file writing entirely** and take the
  FULL report as the captured final message (the enforced-read-only output protocol). That
  cannot hit the artifact path at all, so it removes the failure mode instead of reducing
  its probability. Prefer it for agy read-lane dispatches.
- Exit codes are normal (0 success, 1 error). Bogus model → clean error listing all
  available models.
- **Model naming**: display label verbatim (`"Gemini 3.6 Flash (Low)"`) or slug
  (`gemini-3.6-flash-low`) both accepted. Effort: baked into the name **or** base slug +
  `--effort low|medium|high`; combining `--effort` with an effort-suffixed name **errors**
  (`--effort is not supported for model "Gemini 3.5 Flash"` — labels always carry effort).
- **Auth is OAuth**: run `agy` once interactively (creds → `~/.gemini/`); headless fails
  *silently* when signed out.
- `< /dev/null>` is harmless but not required.
- One prompt per turn — no conversation batching in print mode; `--print-timeout` bounds the wait.

## Headless permission baseline

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
