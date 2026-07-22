---
schema-version: 1
id: codex
cli: codex
verified-version: "0.144.3"
version-argv: ["codex", "--version"]
resume-argv: ["codex", "exec", "resume", "{session_id}"]
session-source: exec-output
stall-signal: log-age
sandbox: enforced
---

## Cross-CLI comparison — codex cells (from archive/v1.1)

| Property | codex 0.144.3 |
| --- | --- |
| Prompt argument | positional (or stdin) |
| `< /dev/null>` needed | **Yes** — hangs reading stdin to EOF |
| Sandbox | **Real**: writes outside workspace blocked; `/tmp` writable; `.git` read-only *by design* |
| Permission flags | `-s workspace-write -c approval_policy="never"` (bypass flag blocked by auto-mode classifier) |
| Exit codes | Normal 0/1 |
| Model validation | **Server-side** — bogus → HTTP 400, exit 1 |
| Reasoning-effort control | `-c model_reasoning_effort=<low…max>` — **validated** (bogus → 400) |
| Output contract | stdout + `-o <file>` = **last message only** |
| Auth | ChatGPT account |

## codex (verified v0.144.3, 2026-07-22) (from archive/v1.1)

### Dispatch (from archive/v1.1)
```bash
codex exec -m <model> -C <repo> -s workspace-write -c approval_policy="never" \
  -c model_reasoning_effort=<low|medium|high|max> \
  --add-dir <parent-dir-for-cross-repo> --skip-git-repo-check \
  -o <report-file> "Read <brief-file> — your complete requirements. … Begin." < /dev/null
```

### Verified behavior (from archive/v1.1)
- **Stdin**: with a piped/open stdin, codex prints `Reading additional input from stdin...`
  and reads to EOF, appending stdin to the prompt. An unclosed pipe hangs it forever →
  `< /dev/null` is mandatory.
- **Sandbox is real**: a write to `~/` fails with "read-only file system". Two carve-outs:
  - `/tmp` **is writable by design** — don't treat the sandbox as total containment, and
    don't let agents stage artifacts there that you'll forget to clean.
  - **`.git` is read-only by design, not intermittently**: working-tree writes succeed while
    `git commit` deterministically fails on `.git/index.lock`. Controller-commits is
    structural, not a flakiness workaround.
- `--dangerously-bypass-approvals-and-sandbox` is blocked by the Claude Code auto-mode
  permission classifier — `workspace-write` + `approval_policy="never"` is the working ceiling.
- **`-s read-only` exists and makes codex the only CLI with an *enforced* read-only
  dispatch** — use it for all reviewer roles (the tier table's "read-only" mode is intent
  on agy/opencode but enforcement here).
- `-o <file>` contains **only the agent's final message** — verify via `git diff` + your own
  gate re-run, never the report prose.
- Model IDs and `model_reasoning_effort` are **server-validated**: bogus values → HTTP 400,
  exit 1, with a clear JSON error.
- Model IDs verified dispatching: `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`.
- Known model quirk: **Luna long-context recall ~41%** (Sol/Terra ~90%) — bump Luna→Terra
  the moment a task reasons over a large codebase/diff.

---

## Canonical dispatch template

```bash
codex exec -m <model> -C <repo> -s workspace-write -c approval_policy="never" \
  -c model_reasoning_effort=<effort> --skip-git-repo-check -o $WORKSPACE/task-N-status.md \
  "Read $WORKSPACE/implementer-contract.md — your operating contract. \
   Read $WORKSPACE/task-N-brief.md — your complete requirements. \
   Scene: <one line: where this task fits>. \
   Interfaces from prior tasks: <lines, or 'none'>. \
   Write your full report to $WORKSPACE/task-N-report.md. Begin." \
  < /dev/null
```

This is a foreground command. Place it inside the self-reaping wrapper in
`core/liveness.md`; that wrapper exclusively owns backgrounding, logging, and PID
tracking. Record `BASE=$(git rev-parse HEAD)` before starting the wrapper.

### Resume — a kill is a checkpoint, not a restart (from archive/v1.1)

All three CLIs can continue a killed/expired session; **resume, don't re-dispatch from
scratch** after any backstop kill or hang-kill where partial progress is real:

| CLI | Resume |
| --- | --- |
| codex | `codex exec resume --last` (or by session id) |

Working-tree progress survives the kill too (agents write as they go) — `git diff` before
resuming to see what's already landed.

For this verified codex surface, `codex exec resume` accepts only `-c key=value` config
overrides plus `--last` or `SESSION_ID` and the prompt. It rejects `-C`, `-s`, `-o`, and
`--skip-git-repo-check` (exit 2). Pass sandbox and effort settings as
`-c sandbox_mode=...` and `-c model_reasoning_effort=...`.

The `< /dev/null>` redirect is mandatory for codex dispatches: an open or piped stdin can
hang while codex reads to EOF.
