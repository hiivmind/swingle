---
schema-version: 1
id: pi
cli: pi
verified-version: "0.83.0"
version-argv: ["pi", "--version"]
resume-argv: ["pi", "-p", "--session-id", "{session_id}"]
fork-flag: "--fork"
session-source: conversation-id
stall-signal: log-age
report-transport: report-file
list-models-argv: ["pi", "--list-models"]
sandbox: none
---

## Cross-CLI comparison — pi cells (verified 0.81.1, 2026-07-24; P4 updated 0.83.0, 2026-07-31)

| Property | pi |
| --- | --- |
| Prompt argument | **positional / trailing message**; flags parse in any position (no `-p`-eats-next-arg, no `-p`=password trap). `-p`/`--print` selects non-interactive mode and is REQUIRED for headless dispatch. |
| `< /dev/null` needed | **Yes (mandatory from 0.83.0)** — pi reads stdin data when the pipe is open; an infinite stdin causes a `RangeError: Invalid string length` crash. `< /dev/null` was "harmless insurance" at 0.81.1; it is now mandatory. See #71. |
| Sandbox | None — `security.md`: built-in tools "read files, write files, edit files, and run shell commands with the permissions of the pi process". Read, write, and shell all ran headless with no flags. |
| Permission flags | `--approve`/`-a` trusts project-local files (extensions/skills), NOT a tool-permission gate — headless tools already run ungated. No read-only tier. |
| Exit codes | 0 success; **remote** model validation → 1 (see below). |
| Model validation | **Remote, not local.** An unknown model id emits `Warning: … Using custom model id` and is passed through; the provider rejects it (`401 ModelError`, exit 1). A typo is not caught before dispatch. |
| Reasoning-effort control | `--thinking off\|minimal\|low\|medium\|high\|xhigh\|max`. **Locally validated** — a bad value warns with the valid list and proceeds at default (warned, not silently ignored). |
| Output contract | Clean stdout, **no banner**. Tool calls and the final message print incrementally (log-age stall detection works). No artifact diversion — agents write report files to workspace paths with the ordinary `write` tool. |
| Auth | Per-provider; `~/.pi/agent/auth.json`. This machine: `opencode-go` (Zen) only. `--provider`/`--model` or a combined `provider/model` string select the target. |
| Model surface | `pi --list-models [provider]`. pi is multi-provider (anthropic, huggingface, opencode-go, …); reachable models are gated by which providers are authed. |
| Changelog | https://github.com/earendil-works/pi (packages/coding-agent) — read on every version bump before probing. Shipped docs live under the installed package's `docs/`. |

## Sessions — the controller assigns the id (from live probe 2026-07-24)

pi is the **only** pack where the controller *chooses* the session id up front rather than
recovering it afterward. `--session-id <id>` creates the session if missing and resumes it
if present, so there is no `session list` to diff (opencode) and no id to parse out of
stdout (codex/grok). `session-source: conversation-id` reflects this — and pi's is the
strongest form of it, because no recovery step can fail.

Dispatch a task/role with a deterministic id (e.g. `sdd-task-3-implement`), then resume by
the same id:

```bash
pi -p --session-id <id> --model <provider/model> "<prompt>"   # create-or-resume
pi -p --session-id <id> --model <provider/model> "<continuation>"   # resume, full memory
```

- **Resume is cwd-scoped.** Sessions are stored per project at
  `~/.pi/agent/sessions/<cwd-slug>/…_<id>.jsonl`, so `resume-argv` omits `--session-dir`:
  resume from the same working directory the dispatch used (the natural SDD case — dispatch
  and resume both target the repo). `PI_CODING_AGENT_SESSION_DIR` / `--session-dir` override
  the location; if a dispatch sets one, resume must set the same.
- **Fork branches by id.** `--fork <src-id> --session-id <new-id>` starts a new session
  seeded with the source's context (verified: forked child recalled the parent's secret),
  leaving the parent untouched. Use it for re-review-in-a-branch without mutating the
  implementer's thread.
- **Memory continuity verified**: a value set in turn 1 was recalled after resume and after
  fork (`4242`, `BANANA`).

### Resume — a kill is a checkpoint, not a restart

| CLI | Resume |
| --- | --- |
| pi | `pi -p --session-id <id>` (create-or-resume, cwd-scoped) / `--continue` for the most recent in cwd / `--fork <id>` to branch |

Working-tree progress survives a kill (agents write as they go) — `git diff` before resuming.

## Verified behavior (pi 0.81.1, 2026-07-24; stdin updated 0.83.0, 2026-07-31)

- **No sandbox, no permission gate**: read, write, and shell executed headless with no
  flags. `security.md` documents this as intentional — pi ships no sandbox; use containers
  or the Gondolin extension for isolation. Treat every dispatch as full-host capability.
- **`-p`/`--print` is mandatory** for headless dispatch; without it pi launches the TUI.
- **`< /dev/null` is mandatory** from 0.83.0 — pi reads stdin data when the fd is open;
  leaving stdin attached to a live pipe (e.g. piped from another process) causes a
  `RangeError: Invalid string length` crash. Always redirect stdin to `/dev/null`. (At
  0.81.1 this was harmless insurance; it is now a hard requirement.)
- **Flag parsing is order-insensitive** and the prompt is a trailing positional message, so
  the agy `-p "<PROMPT>"`-must-be-last footgun and the opencode `-p`=password footgun do
  **not** apply here. `"<prompt>" --thinking low` parsed correctly.
- **Model validation is remote**: a bogus id is forwarded as a "custom model id" and fails
  only at the provider (`401 ModelError`, exit 1). Resolve model ids from `pi --list-models`,
  never trust a hand-typed id to fail fast.
- **`--thinking` is locally validated** (warns + proceeds on a bad value) — unlike
  opencode's silent-ignore, but still confirm the intended level took effect from the value
  you passed, not from the absence of an error.
- **No background bash, no subagents, no to-dos** in core (`usage.md` design principles) —
  these are harness-adapter concerns, not pack concerns, but they mean a pi *controller*
  runs every dispatch through the detached wrapper in `core/liveness.md`. See
  `skills/sdd/harnesses/pi.md`.
- **No cheap auth-probe subcommand**: `readiness-argv` is omitted, so preflight defaults to
  `version-argv` (local only). Auth reachability surfaces as a channel failure on the first
  real dispatch, handled by the standard fallback rules. `pi --list-models <provider>` is a
  network-backed catalog check if an explicit readiness gate is wanted later.

## Canonical dispatch template

```bash
pi -p --session-id <id> --model <provider/model> --thinking <level> "<prompt>" < /dev/null
```

Run inside the self-reaping detached wrapper (`core/liveness.md`); keep stdout in the
per-task log; the session id is the one you assigned, recorded in the ledger for resume.
