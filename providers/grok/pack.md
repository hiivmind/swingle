---
schema-version: 1
id: grok
cli: grok
verified-version: "0.2.111"
version-argv: ["grok", "--version"]
resume-argv: ["grok", "--resume", "{session_id}"]
fork-flag: "--fork-session"
session-source: exec-output
session-list-argv: ["grok", "sessions", "list"]
stall-signal: log-age
report-transport: report-file
sandbox: enforced
readiness-argv: ["grok", "models"]
---

## Cross-CLI comparison — grok cells

| Property | grok 0.2.111 (user-guide + smoke) |
| --- | --- |
| Prompt argument | `-p` / `--single` (also `--prompt-file`, `--prompt-json`) |
| `< /dev/null>` needed | **No** — headless does not read piped stdin as prompt |
| Sandbox | **Enforced** profiles: `off`, `workspace`, `read-only`, `strict`, `devbox` (Landlock/Seatbelt) |
| Permission flags | **`--always-approve`** ≡ `--yolo` ≡ `bypassPermissions`. Do not use `--permission-mode acceptEdits` headless (flag does not enable that policy) |
| Exit codes | Docs: 0/1/130/143; smoke: bogus model may still exit 0 — gate on disk/stdout |
| Model validation | Error text (`unknown model id`); re-check exit code on verify |
| Reasoning-effort control | `--reasoning-effort` / `--effort`: none…max (P9 for invalid) |
| Output contract | `plain` (default), `json` (`.sessionId` + `.text`), `streaming-json` |
| Auth | grok.com OAuth / `XAI_API_KEY`; SuperGrok for higher limits |
| Docs | `~/.grok/docs/user-guide/` — read 14/17/18/22 on every version bump |

### Resume — a kill is a checkpoint, not a restart

| CLI | Resume |
| --- | --- |
| grok | `grok --resume <session_id>` (+ skill-appended `-p "<prompt>"`); `-c` for most-recent in cwd; `--fork-session` to branch |

Session ids: prefer `--output-format json` → `.sessionId`. Fallback: `grok sessions list`
(UUID column, cwd-scoped). Working-tree progress survives kill — `git diff` before resuming.

**Assembly rule (matches agy):** `resume-argv` does **not** embed `-p`. The skill appends
`-p "<continuation>"` (and implement/review flags). Fork form:

```bash
grok --resume <session_id> --fork-session -p "<continuation>" --always-approve --cwd <repo>
```

Sandbox on resume is **session-fixed** (user-guide 18): omit `--sandbox` on resume or
pass the same profile; a different profile is refused.

## grok (surface seed 0.2.111, 2026-07-24)

Authority: `~/.grok/docs/user-guide/14-headless-mode.md`, `17-sessions.md`,
`18-sandbox.md`, `22-permissions-and-safety.md`, and `~/.grok/README.md`.

### Verified / documented behavior

- **`--always-approve` / `--yolo`** is the unattended implement ceiling (always-approve
  mode). File write and shell write land on disk under this flag (pre-pack smoke).
- **`--permission-mode acceptEdits` via CLI does not enable acceptEdits policy** (only
  `bypassPermissions` and `default` fully apply via that flag; set other modes via
  `defaultMode` in settings). Smoke: acceptEdits + shell → silent no-op.
- **Headless does not ingest piped stdin** as prompt material — no codex/agy-class hang.
- **Sandbox** is real OS isolation. Unknown custom profile fails closed.
- **`-s` / `--session-id` creates only** (must be UUID); resume with `-r` / `-c`.
- Fallback if always-approve is admin-locked: document and STOP (requirements.toml).

### Canonical dispatch template

**Implement:**

```bash
grok -p "<PROMPT>" -m <model> --cwd <repo> --always-approve \
  --sandbox workspace --output-format plain
```

**Review:**

```bash
grok -p "<PROMPT>" -m <model> --cwd <repo> --always-approve \
  --sandbox read-only --output-format plain
```

For session-id capture on the same run, use `--output-format json` and parse
`.sessionId` / `.text`. Alias: `--yolo` ≡ `--always-approve`.

This is a foreground command. Place it inside the self-reaping wrapper in
`core/liveness.md`; that wrapper exclusively owns backgrounding, logging, and PID
tracking. Record `BASE=$(git rev-parse HEAD)` before starting the wrapper.

### Gotchas

1. Do not use `--permission-mode acceptEdits` headless — use `--always-approve` / `--yolo`.
2. Gate on stdout + on-disk effects (bogus model may still exit 0 despite docs 0/1).
3. `-p` = one user turn with multi-tool agency; stdin is not the prompt.
4. `-s` creates only (UUID); resume with `-r` / `-c`.
5. Sandbox profiles are real; resume cannot change profile.
6. Model inventory may be thin — check `grok models` each session.
7. Quota exhaustion is a **dispatch-time channel failure** (upsell on the dispatch).
   `readiness-argv` (`grok models`) proves the CLI answers, not remaining quota.
8. Re-read `~/.grok/docs/user-guide/{14,17,18,22}-*.md` on every CLI version bump before
   probing — never assume permission/sandbox survived a patch.
