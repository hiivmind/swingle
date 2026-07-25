# pi harness adapter

pi keeps its core deliberately small: "it intentionally does not include built-in MCP,
sub-agents, permission popups, plan mode, to-dos, or background bash" (`docs/usage.md`,
pi 0.81.1). Built-in tools are `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`.
Three of the five concerns below therefore have **no core mechanism** — this adapter maps
them to file-based substitutes rather than to tools that do not exist. Do not fabricate
`Task`/`TodoWrite`/background-flag calls; they will fail.

| Concern | pi mapping |
| --- | --- |
| Skill load | There is **no skill tool**. pi injects skill names and descriptions into the system prompt as XML and expects the agent to `read` the full `SKILL.md` on demand — so to load this plugin, read and follow `<root>/skills/sdd/SKILL.md`; same for `delegate` / `swingle-verify`. Announce the skill name, then follow its body. `/skill:<name>` forces a load in interactive mode. Name collisions keep the **first** skill found and warn. |
| Native subagents | **Not in core.** The `native-subagents` route is unavailable unless a subagent extension/package is installed; superpowers' `references/pi-tools.md` names `pi-subagents` as the optional companion. With no such tool present, do not degrade silently — say the harness-native route is unavailable and run every lane through `providers/<id>/`, or execute sequentially in-session when the user declines external dispatch. |
| Task tracking | **Not in core.** Use the plan ledger on disk (`.sdd-dispatch/delegate/ledger.md` for `delegate`, the plan progress file for `sdd`). This costs nothing here: SDD's tracking is already file-based, and the ledger is the durable record a todo tool would only mirror. |
| Background jobs | **No background bash.** The `bash` tool runs foreground only, so the detached form from `core/liveness.md` is the sole mechanism: write the dispatch script to a file, launch it with `setsid nohup <script> >/dev/null 2>&1 </dev/null &` plus `disown`, record the CLI pid to a pid file, and have the wrapper append its terminal line to a marker file. Observe completion by polling that marker with short `bash` calls between turns — there is no notification channel and no watcher tool. pi's own docs point at tmux and containers for anything richer. Never hold a dispatch in the foreground: it blocks the controller and disables the stall rule. |
| Asset root | No plugin-root env var. **Package install:** the clone lands at `~/.pi/agent/git/<host>/<owner>/<repo>` (`PI_PACKAGE_DIR` overrides the package directory; `PI_CODING_AGENT_DIR` overrides `~/.pi/agent`). **Any install:** resolve from the physical path of `skills/sdd/SKILL.md` — `<root> = dirname(dirname(dirname(SKILL.md)))` — so `<root>/core` and `<root>/providers` exist. Prefer the physical path over any cache path when both are present, and write verification logs only to a writable source tree. |

## Install and discovery

`pi install https://github.com/discreteds/swingle` clones the whole repository
as a package and discovers its `skills/` directory automatically, so the layout contract
(`core/`, `providers/`, `contracts/` as siblings of `skills/`) survives intact. This is the
preferred route. pi also loads skills from `~/.pi/agent/skills/`, `~/.agents/skills/`,
project `.pi/skills/` and `.agents/skills/`, a `skills` array in settings (which can point
at `~/.claude/skills`), and repeatable `--skill <path>` flags.

Two consequences worth knowing before a session:

- **Project-local skills load only after the project is trusted.** A fresh checkout will
  not surface `.agents/skills` or `.pi/skills` until the project is approved (`--approve`).
  Global and package skills are unaffected.
- **pi validates frontmatter strictly.** A skill whose description is a plain YAML scalar
  containing a colon-space is rejected outright — the whole frontmatter fails to parse and
  the skill is dropped with a warning, not loaded in degraded form. Lenient harnesses hide
  this class of defect, so when a skill is missing on pi, check the frontmatter before
  suspecting discovery. (This plugin hit exactly that on `skills/sdd/SKILL.md`; fixed in
  v1.6.1 by folding the description into a `>-` block scalar.)

## Levers

The alias **"all pi"** means `native-subagents` — and is therefore **unavailable on stock
pi**. If the user asks for it with no subagent tool installed, say so and offer the two
real options: external dispatch through the provider packs, or sequential in-session
execution. Silently substituting one for the other misreports which engine did the work
and corrupts the ledger's `route=` field.

pi-as-**controller** (this adapter) and pi-as-**provider** (`providers/pi/`) are separate
concerns. A pi controller may dispatch to any pack, including `providers/pi/` — nested
`pi -p` under a pi controller. There is no sandbox to probe (unlike codex-under-codex), so
nested dispatch needs no gate; the only rule is the shared one — assign a distinct
`--session-id` per dispatch so the child session never collides with the controller's.
