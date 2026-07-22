---
schema-version: 1
id: agy
cli: agy
verified-version: "1.1.4"
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
| Sandbox | None — headless reads/writes freely, no flags |
| Permission flags | `--dangerously-skip-permissions` no longer needed (≥1.1.4) |
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
- **No permission gate on ≥1.1.4**: headless runs read **and write** freely with no flags.
  `--dangerously-skip-permissions` and `--mode accept-edits` are no longer required, and no
  read-only tier exists. (On ≤1.1.1 headless auto-denied every tool — a total behavior flip
  between patch releases; re-verify on every version bump.)
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

## Canonical dispatch template

```bash
agy --model <m> --effort <e> --add-dir <repo> --print-timeout <t> -p "<PROMPT>" < /dev/null
```
