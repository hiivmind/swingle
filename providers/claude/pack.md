---
schema-version: 1
id: claude
cli: claude
verified-version: "2.1.220"
version-argv: ["claude", "--version"]
resume-argv: ["claude", "-p", "--resume", "{session_id}"]
fork-flag: "--fork-session"
session-source: conversation-id
stall-signal: log-age
report-transport: report-file
sandbox: none
---

## Cross-CLI comparison — claude cells (verified 2.1.218, 2026-07-24)

| Property | claude 2.1.218 |
| --- | --- |
| Prompt argument | **positional / trailing**; flags parse in any position (no `-p`-eats-next-arg, no `-p`=password trap). `-p`/`--print` selects non-interactive mode and is REQUIRED for headless dispatch — without it `claude` launches the interactive TUI. |
| `< /dev/null` needed | No — every probe ran without a stdin redirect and none hung. (P4 unclosed-pipe backstop not yet run; harmless insurance if wanted.) |
| Sandbox | **None** — Claude Code ships no built-in OS sandbox. `--dangerously-skip-permissions` is documented "Recommended only for sandboxes with no internet access"; containment is external (containers). Treat every dispatch as full-host capability, gated only by the permission mode. |
| Permission flags | Reads run headless with **no flag**. Writes and shell require `--dangerously-skip-permissions` (equivalently `--permission-mode bypassPermissions`). `acceptEdits` / `auto` / `dontAsk` do **not** grant writes headless — they still raise an approval prompt that no one can answer under `-p`, so the action **silently no-ops with exit 0** (see below). `--permission-mode plan` is an enforced read-only lane. |
| Exit codes | 0 success; **bogus model → exit 1** with a clean local error ("It may not exist or you may not have access. Run --model to pick"). Fails fast — no dispatch to a typo'd model. |
| Model validation | Local/fast — nonzero exit before work, unlike a remote-only pass-through. |
| Reasoning-effort control | `--effort low\|medium\|high\|xhigh\|max`. **Locally validated** — a bad value warns (`Unknown --effort value … Valid values: low, medium, high, xhigh, max`) and proceeds at default (warned, not silently ignored). |
| Output contract | Clean final message on **stdout**; the `claude.ai connectors are disabled …` banner (emitted when `ANTHROPIC_API_KEY` is set) goes to **stderr**. `--output-format json` returns a single object with `session_id`, `result`, `is_error`, `num_turns`; `stream-json` streams. Tool calls print incrementally (log-age stall detection works). |
| Auth | claude.ai OAuth **or** `ANTHROPIC_API_KEY` / `apiKeyHelper`. When a key is set it takes precedence over the OAuth login (hence the stderr banner). `--bare` forces API-key-only and skips CLAUDE.md/hooks/plugins. |
| Model surface | Aliases `haiku` / `sonnet` / `opus` (and `fable`) resolve to the latest snapshot — the recommended, self-updating form; the models.yaml keys are these aliases, not pinned ids. No open-catalog `list-models` argv (seat tiers, not an enumerable catalog). |
| Changelog | https://docs.claude.com/en/docs/claude-code — read the release notes on every version bump before re-probing. |

## The silent-write footgun (why the controller gate is mandatory)

A write or shell dispatch **without** an enabling permission mode does not error. The agent
narrates "I need permission to create the file … please approve" and exits **0** while
nothing lands on disk — verified across the default, `acceptEdits`, `auto`, and `dontAsk`
modes. A controller that trusted the exit code would ledger a phantom success. This is the
`core/safety-doctrine.md` controller-gate in its sharpest form: confirm every implementer's
work **on disk** (`git status` / `git diff` / test re-run), never from the report prose or
the exit status.

## Self-dispatch (claude under a Claude Code controller) — two traps

Dispatching `claude` from a **Claude Code** controller (the reflexive case) hits two gates a
non-Claude controller does not:

1. **The parent auto-mode Bash classifier blocks the enabling flag.** A nested command
   containing `--dangerously-skip-permissions` or `--permission-mode bypassPermissions` is
   refused by the controlling session's classifier (the same wall codex's
   `--dangerously-bypass-approvals-and-sandbox` hits). The operator must add a Bash allow
   rule for the dispatch, or route through a non-Claude controller.
2. **Child-session env makes the nested agent defer to the parent.** With
   `CLAUDECODE=1` / `CLAUDE_CODE_CHILD_SESSION=1` exported (Claude Code sets these for
   every subprocess), the nested `claude` treats itself as a child session and denies
   headless writes even under `acceptEdits`. Clear them for a clean dispatch:
   `env -u CLAUDECODE -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_ENTRYPOINT
   -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_EXECPATH -u CLAUDE_PID claude -p …`.

Controllers on **codex / grok / opencode / pi** (or a plain shell) have neither problem —
`claude` is a clean external implementer/reviewer there. The `native-subagents` lever ("all
Claude" under Claude Code) remains the right tool for in-harness Claude work; this pack is
for cross-harness dispatch and for deliberately isolated `claude`-under-`claude` runs.

## Sessions — the controller assigns the id

Like pi, the controller **chooses** the session id up front rather than recovering it after.
`--session-id <uuid>` (the value **must be a valid UUID**) creates the session if missing and
resumes it if present, so there is no list to diff and no id to parse out of stdout —
`session-source: conversation-id` in its strongest form (no recovery step can fail). Memory
continuity verified: a number stored on turn 1 was recalled after `--resume`.

```bash
claude -p --session-id <uuid> --model <alias> "<prompt>"     # create-or-resume
claude -p --resume <uuid> --model <alias> "<continuation>"    # resume, full memory
```

- **`--fork-session`** on a resume mints a new session id seeded with the source's context,
  leaving the parent thread untouched — use it for re-review-in-a-branch.
- **`-c` / `--continue`** resumes the most recent conversation in the current directory.
- `--output-format json` also emits the auto-generated `session_id` when you do not assign
  one.

### Resume — a kill is a checkpoint, not a restart

| CLI | Resume |
| --- | --- |
| claude | `claude -p --resume <uuid>` (or `--continue` for the latest in cwd; `--fork-session` to branch) |

Working-tree progress survives a kill (agents write as they go) — `git diff` before resuming.

## Read-only reviewer lane

`--permission-mode plan` is an **enforced** read-only lane: a dispatched write was refused
(verified — nothing landed on disk). Caveat: plan mode blocks the review-file write too
(it writes a planning doc under `~/.claude/plans/`, not the workspace), so a plan-mode
reviewer must return its verdict as the **captured final message**, not a report file. For
an ordinary report-file reviewer, dispatch without plan mode — read-only by contract
instruction plus the controller's HEAD-unchanged gate — as on the other `sandbox: none`
packs.

## Canonical dispatch template

```bash
claude -p --model <alias> --session-id <uuid> --effort <low|medium|high|xhigh|max> \
  --dangerously-skip-permissions --add-dir <parent-dir-for-cross-repo> \
  "Read $WORKSPACE/implementer-contract.md — your operating contract. \
   Read $WORKSPACE/task-N-brief.md — your complete requirements. \
   Scene: <one line: where this task fits>. \
   Interfaces from prior tasks: <lines, or 'none'>. \
   Write your full report to $WORKSPACE/task-N-report.md. Begin."
```

Reviewer dispatches drop `--dangerously-skip-permissions` for `--permission-mode plan`
(enforced read-only, captured-output verdict) or run report-file with read-only by contract.
When the controller is itself Claude Code, prepend the `env -u …` prefix from **Self-dispatch**
and expect the classifier gate on the enabling flag.

This is a foreground command. Place it inside the self-reaping wrapper in `core/liveness.md`;
that wrapper exclusively owns backgrounding, logging, and PID tracking. Record
`BASE=$(git rev-parse HEAD)` before starting the wrapper, and confirm the implementer's work
on disk (the silent-write footgun above), never from its report or exit code.
