# omp controller adapter

omp (Oh My Pi) ships a full agentic harness: a `Task` tool with bundled subagents, a
background-job + process **hub** with completion notifications, on-disk todo tracking, and
`skill://` discovery. Unlike pi, **all five concerns below have a native mechanism** — do
not fall back to file-based substitutes. Built-in tools include `read`, `bash`, `edit`,
`write`, `grep`, `glob`, plus `Task`, `Todo`, and the `hub` job/process controls.

| Concern | omp mapping |
| --- | --- |
| Skill load | Native `skill://` discovery. omp injects installed skill names + descriptions into the system prompt and resolves `skill://<name>` (and `skill://<name>/<path>` for a file within) on demand — so to load this plugin, read and follow `skill://swingle-delegate` / `skill://swingle-sdd` / `skill://swingle-setup` (equivalently `<root>/skills/<id>/SKILL.md`). `--skills=<glob>` filters discovery; `--no-skills` disables it. Announce the skill name, then follow its body. |
| Native subagents | **Available.** The `Task` tool spawns background subagents from a bundled roster — `scout`, `reviewer`, `designer`, `librarian`, `security-reviewer`, `sonic`, `task` (`omp agents unpack` writes them to `~/.omp/agent/agents` (`--user`) or `./.omp/agents` (`--project`) for customization). The `native-subagents` route ("all omp") is therefore **real**: route review lanes to `reviewer`, read-only exploration to `scout`, general implementation to `task`. Subagents run async and **auto-deliver on completion** — no polling; inspect/steer via `hub` (`jobs` / `wait` / `send`), read a finished agent's output at `agent://<id>` and its transcript at `history://<id>`. (Verified: a `scout` dispatch returned structured output and auto-delivered.) |
| Task tracking | Native `Todo` tool (phased list; `init` / `start` / `done` / `block`). Use it for the controller's own plan — but the durable SDD record still lives in the plan progress file (`sdd`) / `.swingle/delegate/ledger.md` (`delegate`); the todo mirrors that ledger, it does not replace it. |
| Background jobs | Native **`hub`** — two forms. (1) Background **jobs** — subagents and `bash async:true` — that **auto-deliver a settled result** (the notification channel pi lacks). (2) Long-running **processes** — `hub start <name>` with readiness (`ready.log` / `ready.port`), `hub logs --follow` (log mtime = the `log-age` stall signal), `hub wait`, and `hub stop` (graceful kill **by name**, never a PID pattern). Run an external-provider dispatch as a named hub process with `persist: true` (survives the last client) or `detached: true` (survives broker/omp exit) so a supervisor event cannot orphan-kill it — the detached-wrapper guarantee from `core/liveness.md` without hand-rolled `setsid nohup`. Map the liveness protocol directly: observable launch = `ready`; stall check = `logs` mtime vs the manifest threshold; completion = `wait` / auto-delivery; kill = `stop`. (Verified: a named process launched, ready-matched, and its exit was observed via `hub wait`.) |
| Asset root | omp installs the plugin as a **full clone** at `~/.omp/plugins/cache/marketplaces/swingle-marketplace/` (`core/`, `providers/`, `controllers/`, `contracts/` are siblings of `skills/`). Resolve `<root>` from the physical path of `skills/sdd/SKILL.md` — `<root> = dirname(dirname(dirname(SKILL.md)))` — so `<root>/core`, `<root>/providers`, `<root>/controllers` exist. The marketplace cache is a throwaway snapshot clobbered on upgrade (and can lag the source — e.g. an install predating the `controllers/` rename); prefer a writable source checkout when one resolves, and write verification logs only there. |

## Install and discovery

`omp` installs swingle from the marketplace — a full-repo clone under
`~/.omp/plugins/cache/marketplaces/swingle-marketplace/` — so the layout contract
(`core/`, `providers/`, `controllers/`, `contracts/` as siblings of `skills/`) survives
intact. omp also discovers skills from `~/.omp/agent/skills`, project `./.omp/skills` and
`./.agents/skills`, and repeatable `--skills` / `-e` paths.

Two consequences worth knowing before a session:

- **Project-local skills and agents load only after the project is trusted.** omp
  auto-switches out of `~` to a temp dir unless `--allow-home`; a fresh checkout surfaces
  project `.omp/` / `.agents/` skills only once approved. Global and marketplace skills are
  unaffected.
- **A nested `omp -p` dispatch needs `--auto-approve`.** A *driving* omp session already
  holds its tools; omp-as-provider (`providers/omp/`) runs tools headlessly only under
  `--auto-approve`, and its model id resolves from `omp models`.

## Levers

The alias **"all omp"** means `native-subagents` — and **is available** (contrast stock
pi, where it is not). Route the SDD roles to bundled agents (`reviewer` for review lanes,
`scout` for read-only exploration, `task` for implementation), or dispatch externally
through the provider packs when the user wants a different engine or an independent quota.
Both are real engines; state which one the ledger's `route=` field records — never label a
native-subagent run as an external dispatch or vice versa.

omp-as-**controller** (this adapter) and omp-as-**provider** (`providers/omp/`) are
separate concerns. An omp controller may dispatch to any pack, including `providers/omp/` —
nested `omp -p` under an omp controller. `sandbox: none`, so nested dispatch needs no
containment gate (like pi, unlike codex-under-codex); the only rule is the shared one —
give each nested dispatch a distinct `--session-dir` so the child session never collides
with the controller's store.
