# SDD Dispatch Reference — codex / opencode / agy

> Living document. Every fact is stamped with the CLI version it was verified against.
> If the installed version differs, re-run the [verification protocol](verification-protocol.md) before trusting this page.

## Cross-CLI comparison (the one-glance table)

| Property | codex 0.144.3 | opencode 1.17.18 | agy 1.1.4 |
| --- | --- | --- | --- |
| Prompt argument | positional (or stdin) | **positional** (`-p` = basic-auth *password*!) | `-p "<PROMPT>"` — **must be last arg** |
| `< /dev/null` needed | **Yes** — hangs reading stdin to EOF | No (verified; harmless insurance) | **Yes** — hangs |
| Sandbox | **Real**: writes outside workspace blocked; `/tmp` writable; `.git` read-only *by design* | None — headless reads/writes/shells freely, no flags | None — headless reads/writes freely, no flags |
| Permission flags | `-s workspace-write -c approval_policy="never"` (bypass flag blocked by auto-mode classifier) | `--auto` exists but is a no-op until permissions are configured; keep as intent documentation | `--dangerously-skip-permissions` no longer needed (≥1.1.4) |
| Exit codes | Normal 0/1 | Normal 0/1 | Normal 0/1 (≥1.1.4; earlier versions reportedly returned 1 on success) |
| Model validation | **Server-side** — bogus → HTTP 400, exit 1 | Errors (JSON) on bogus model, exit 1 | Errors cleanly, lists available models |
| Reasoning-effort control | `-c model_reasoning_effort=<low…max>` — **validated** (bogus → 400) | `--variant <high\|max\|minimal…>` — **silently ignored if unsupported** | Effort-in-name (`-low/-medium/-high` slug or `(Low)` label) **or** base slug + `--effort` — mixing both **errors** |
| Output contract | stdout + `-o <file>` = **last message only** | Clean stdout (small `build · model` banner) | stdout, **but** document tasks divert to brain files (see gotchas) |
| Auth | ChatGPT account | Zen (pay-as-you-go) | OAuth — must run `agy` interactively once; headless fails **silently** if signed out |

**Safety doctrine (all three):** the hard gate is the controller, not the CLI.
Only codex has a sandbox; agy and opencode can write anywhere with zero flags, so there is
no such thing as a "read-only dispatch" on those two. Therefore: dispatch only on a
**clean/committed tree**, `git diff` after every dispatch (including "read-only" roles),
re-run test gates yourself, and **the controller commits** — never the agent.
codex fails loud and is contained; agy and opencode fail quiet and are unconstrained —
prefer codex as the default lane for write tasks and structured reviews; use the others
for perspective diversity and price.

---

## Background dispatch & liveness protocol

**The failure mode this kills:** a background-dispatched agent hangs or dies early; the
controller keeps *believing* it is running (sometimes insisting so to the user) until asked
to check the logs — which then show it stopped long ago. Belief is not evidence. The two
rules below are mandatory for every background dispatch.

### Rule 1 — Observable launch, stall-based judgment, backstop cap

**Wall-clock time is not evidence of a hang — activity is.** A fixed timeout that kills a
healthy 40-minute run at minute 30 wastes the entire spend: the *stall check* (Rule 2) is
the primary kill criterion, and the wall-clock cap is only a **last-resort backstop** for
when nobody is watching (session ended, controller distracted).

At launch, three things:

```bash
LOG=<scratch>/<task>.log
timeout --kill-after=30s <backstop> \
  codex exec … > "$LOG" 2>&1        # backstop ≈ 4–5× the honest estimate — it should
                                     # essentially never fire while Rule 2 checks run
# opencode: same wrapper. agy: --print-timeout <backstop> serves the same role.
```

1. **Per-task log file** — its mtime/growth is the liveness signal.
2. **Generous backstop cap** (4–5× estimate, or omit entirely for a known-long run you
   will actively monitor). Its job is orphan cleanup, not progress policing — if a
   backstop ever fires on a healthy run, the estimate was wrong: raise it and resume.
3. **Record the session/conversation id** so a kill is never a total loss (see Resume).

### Resume — a kill is a checkpoint, not a restart

All three CLIs can continue a killed/expired session; **resume, don't re-dispatch from
scratch** after any backstop kill or hang-kill where partial progress is real:

| CLI | Resume |
| --- | --- |
| codex | `codex exec resume --last` (or by session id) |
| opencode | `opencode run -c` (last session) / `-s <session-id>` (+ `--fork` to branch) |
| agy | `agy -c` (most recent) / `agy --conversation <id>` |

Working-tree progress survives the kill too (agents write as they go) — `git diff` before
resuming to see what's already landed.

### Rule 2 — Evidence-first liveness check

**"It is still running" may only be claimed after running this check in the current turn.**
Never from memory, never from the fact that no completion notification has arrived.

```bash
pgrep -fa '[b]in/codex exec|[o]pencode run|[a]gy '   # is the process even alive?
# bracket the first letter: a plain pattern matches YOUR OWN check command (the shell's
# command string contains it) and long-lived `codex app-server` daemons — both false alives
stat -c 'mtime=%y size=%s' "$LOG"; tail -5 "$LOG"   # when did it last say anything?
```

Verdict table:

| Process | Log activity | Verdict | Action |
| --- | --- | --- | --- |
| absent | any | **Dead** — regardless of expectations | Read log tail for cause; re-dispatch (once) or escalate tier |
| alive | mtime fresh (< stall threshold) | Running | Leave it alone; re-check at the next threshold |
| alive | mtime stale (> stall threshold) | **Presumed hung** | `kill` it, capture the log, re-dispatch once — second hang ⇒ change model/CLI, don't loop |

Stall thresholds by CLI (how "silence" maps to "stalled"):
- **codex / opencode** stream incrementally (tool calls, shell output) — log silence
  **> ~5 min** on an active task = stalled.
- **agy print mode buffers** — the log may legitimately stay empty until the final answer,
  so log-growth is NOT a liveness signal for agy. Rely on `--print-timeout` + process
  existence instead (and remember the brain-file diversion when stdout stays empty at exit).

### Operating rules

- **Elapsed wall-clock alone is never grounds to kill** — a slow healthy run and a hung run
  look identical on a clock and completely different in the log. Kill only on stall
  evidence (or let the generous backstop reap a genuinely orphaned process).
- **Check on cadence, not on suspicion**: after launching background dispatches, check
  liveness at the first stall threshold — don't wait for the user to ask.
- **The user asking "is it still running?" is itself evidence it probably isn't.** Run the
  check immediately; never answer from belief. (Track record so far: 3 asks, 3 stalls.)
- **Kill by recorded PID, never by pattern, from any shell that also dispatches.** A
  wrapper shell embeds the dispatch string in its own command line, so even a bracketed
  `pkill -f '[o]pencode run'` kills the wrapper itself (observed 2026-07-22: shell died
  pre-launch, exit 125/144, 0-byte log). Capture `$!`/pgrep the specific pid at dispatch
  time; pattern-kill only from a shell that dispatches nothing.
- **Harness background tasks: run the CLI in the wrapper's foreground.** Backgrounding
  with `&` inside an already-backgrounded harness command makes the harness "completed"
  notification fire when the wrapper exits — seconds after launch, not when the CLI
  finishes. Foreground-in-wrapper makes notification == CLI exit; pair it with a separate
  stall-watcher loop (wake on process exit OR log-silence past threshold).
- On any early exit, the log tail is the diagnosis — silent failure modes already
  documented: agy signed-out (exits quietly), agy `-p` footgun (answers the wrong prompt
  fast), codex stdin hang (waiting on EOF), opencode auth/balance errors (JSON on stdout).
- Record any *new* hang/early-exit signature in this file and append the incident to
  [verification-log.md](verification-log.md).

---

## codex (verified v0.144.3, 2026-07-22)

### Dispatch
```bash
codex exec -m <model> -C <repo> -s workspace-write -c approval_policy="never" \
  -c model_reasoning_effort=<low|medium|high|max> \
  --add-dir <parent-dir-for-cross-repo> --skip-git-repo-check \
  -o <report-file> "Read <brief-file> — your complete requirements. … Begin." < /dev/null
```

### Verified behavior
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

## opencode (verified v1.17.18, 2026-07-22)

### Dispatch
```bash
# prompt is POSITIONAL — `-p` is basic-auth password, not prompt
opencode run --auto -m <provider/model> --variant <high|max|minimal…> \
  --dir <repo> "Read <brief-file> …"
```

### Verified behavior
- **No sandbox**: with no permission config present, headless `opencode run` read files,
  wrote files, and executed shell commands **without `--auto`**. `--auto`
  ("auto-approve permissions not explicitly denied") only matters once a permission config
  exists — keep passing it as intent documentation.
- **`-p` means password** (basic auth for `--attach` mode). Carrying the agy `-p "<PROMPT>"`
  habit over silently misfires. The prompt is a positional argument.
- **No stdin hang** (verified under timeout with open stdin) — `< /dev/null` optional.
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

---

## agy — Antigravity CLI (verified v1.1.4, 2026-07-22)

### Dispatch
```bash
# -p "<PROMPT>" must be the LAST argument
agy --model gemini-3.6-flash --effort <low|medium|high> \
  --add-dir <repo> --print-timeout 5m -p "<PROMPT>" < /dev/null
```

### Verified behavior
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
- `< /dev/null` mandatory (hang, as codex).
- One prompt per turn — no conversation batching in print mode; `--print-timeout` bounds the wait.

---

## Change history

- **2026-07-22** — Initial reference from full three-CLI verification round
  (see verification-log.md entry 2026-07-22). Major refutations vs prior notes:
  agy permission model flipped open in 1.1.4; agy exit codes normalized;
  codex `.git` read-only reclassified from "intermittent" to by-design;
  opencode confirmed sandbox-free and stdin-safe.
