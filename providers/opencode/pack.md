---
schema-version: 1
id: opencode
cli: opencode
verified-version: "1.18.9"
version-argv: ["opencode", "--version"]
resume-argv: ["opencode", "run", "-s", "{session_id}"]
fork-flag: "--fork"
session-source: session-list
session-list-argv: ["opencode", "session", "list"]
stall-signal: log-age
report-transport: report-file
sandbox: none
readiness-argv: ["opencode", "session", "list"]
---

## Cross-CLI comparison — opencode cells (from archive/v1.1)

| Property | opencode 1.18.9 |
| --- | --- |
| Prompt argument | **positional** (`-p` = basic-auth *password*!) |
| `< /dev/null` needed | **Yes — mandatory** (refuted 2026-07-29; a truly open stdin hangs indefinitely) |
| Sandbox | None — headless reads/writes/shells freely, no flags |
| Permission flags | `--auto` exists but is a no-op until permissions are configured; keep as intent documentation |
| Exit codes | Normal 0/1 |
| Model validation | Errors (JSON) on bogus model, exit 1 |
| Reasoning-effort control | `--variant <high\|max\|minimal…>` — **silently ignored if unsupported** |
| Output contract | Clean stdout (small `build · model` banner) |
| Auth | Zen (pay-as-you-go) |
| Changelog | https://github.com/sst/opencode/releases — read on every version bump before probing |

### Resume — a kill is a checkpoint, not a restart (from archive/v1.1)

All three CLIs can continue a killed/expired session; **resume, don't re-dispatch from
scratch** after any backstop kill or hang-kill where partial progress is real:

| CLI | Resume |
| --- | --- |
| opencode | `opencode run -c` (last session) / `-s <session-id>` (+ `--fork` to branch) |

Working-tree progress survives the kill too (agents write as they go) — `git diff` before
resuming to see what's already landed.

## opencode (verified v1.18.9, 2026-07-29) (from archive/v1.1)

### Dispatch (from archive/v1.1)
```bash
# prompt is POSITIONAL — `-p` is basic-auth password, not prompt
# stdin MUST be closed/redirected — a truly open stdin hangs indefinitely (2026-07-29)
opencode run --auto -m <provider/model> --variant <high|max|minimal…> \
  --dir <repo> "Read <brief-file> …" < /dev/null
```

### Verified behavior (from archive/v1.1)
- **No sandbox**: with no permission config present, headless `opencode run` read files,
  wrote files, and executed shell commands **without `--auto`**. `--auto`
  ("auto-approve permissions not explicitly denied") only matters once a permission config
  exists — keep passing it as intent documentation. Re-confirmed 2026-07-29, including the
  shell-command sub-case of P6 (file-tool and command permissions were NOT separately
  gated here, unlike agy).
- **`-p` means password** (basic auth for `--attach` mode). Carrying the agy `-p "<PROMPT>"`
  habit over does not silently misfire as of 1.18.9 — it fails loudly (`Error: You must
  provide a message or a command`, exit 1) since the prompt text is swallowed into the
  password field, leaving no positional message. Still a footgun (wrong prompt consumed
  by an auth flag) but a catchable one, not a silent wrong-behavior success.
- **Stdin MUST be closed or redirected — refuted 2026-07-29.** A truly never-closing stdin
  (not merely "under a timeout") hangs the process indefinitely with zero output;
  confirmed 2/2 with a held-open named pipe, against 3/3 clean runs with `< /dev/null` in
  the same session — ruling out the separately-documented backgrounded-startup flakiness
  below as the cause. The 2026-07-22 "no hang" finding was tested against a stdin source
  that reached EOF, not a genuinely open one. Always redirect stdin.
- `--variant` sets provider-specific reasoning effort — but is **silently ignored** when
  unsupported or misspelled (`--variant bogusvariant` ran without complaint). Never assume
  it took effect.
- Exit codes normal: 0 success; bogus model → JSON error (`"ref": "err_…"`), exit 1.
- Useful extras seen in `run --help`: `--format json` (raw JSON events), `-f/--file`
  attachments, `-s/--session` + `--fork` continuation, `--attach` to a running server.
- Model namespace: `opencode/<model>` and `opencode-go/<model>` are distinct lists —
  e.g. `deepseek-v4-flash-free` and `gemini-3.5-flash-lite` exist **only** under `opencode/`.
- **Intermittent zero-output startup hang (observed 2026-07-22, v1.17.18/Zen):**
  backgrounded `opencode run` occasionally hangs before its first output byte — process
  alive, log 0 bytes indefinitely; hit resume (`-s`), `--fork`, and cold dispatches alike
  (~5× in one window) while every foreground run succeeded. Cause undetermined (suspect
  non-tty/piped stdio at startup). Handling: 0-byte log past the 5-min threshold = stall →
  kill (by pid), retry once; second consecutive stall → switch to a FOREGROUND dispatch
  (short tasks) or apply a sub-2k fix inline. Exit codes are useless here — judge by log
  bytes only.
- **Session ids are NOT in plain-text run logs** — get them from `opencode session list`
  (newest first) for `-s` resume/`--fork`.

## Canonical dispatch template

```bash
opencode run --auto -m <model> --dir <repo> "<prompt>" < /dev/null
```
