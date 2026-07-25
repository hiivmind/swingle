# Antigravity harness adapter

| Concern | Antigravity (`agy`) mapping |
| --- | --- |
| Skill load | Skills are session-discovered (no Claude `Skill(...)` tool). To load superpowers SDD: read and follow the loaded skill **`subagent-driven-development`** (plugin: superpowers). To run this plugin: read and follow **`sdd`** (plugin: swingle). Same pattern for `delegate` / `swingle-verify`. Announce the skill name, then follow its body. |
| Native subagents | `invoke_subagent` with a built-in `TypeName` — **`self`** for full-capability work, **`research`** for read-only. Use a `self` (or, for read-only supervision, `research`) child for supervised pack dispatch. |
| Task tracking | **No todo tool.** Maintain a **task artifact** — `write_to_file` with `IsArtifact: true`, `ArtifactMetadata.ArtifactType: "task"`, edited with `replace_file_content` / `multi_replace_file_content`. **Not** `manage_task` (that manages background processes, not a checklist). |
| Background jobs | Launch the self-reaping wrapper from `core/liveness.md` via `run_command` (it runs asynchronously); observe completion via `manage_task` (`status` / `list`) and the wrapper marker file / process exit. Do **not** rely on Claude-style `run_in_background` task notifications. agy print-mode **buffers** output, so a log-age watch would false-kill a healthy run — use process existence + `--print-timeout` as the liveness signal (this is the target-side caveat that also governs what a controlling agy watches for). |
| Asset root | **Repo checkout or symlink:** resolve from the physical path of `skills/sdd/SKILL.md`: `<root> = dirname(dirname(dirname(SKILL.md)))` so `<root>/core` and `<root>/providers` exist. Prefer the physical source path over any installed-cache path (write verification logs only to a writable source tree). |
| Dispatch permission | A controlling agy session runs target CLIs through `run_command`, which is gated by the agy permission baseline (`~/.gemini/antigravity-cli/settings.json`). Driving another harness therefore requires an allow rule for that CLI — e.g. `command(opencode)`, `command(codex)` — in the baseline, exactly as agy-as-target requires allow rules for its own tools (see `providers/agy/pack.md` → Headless permission baseline). Without it the dispatch auto-denies (silent no-op); the controller gate catches the empty result. |

Antigravity-as-**controller** (this adapter) and Antigravity-as-**provider** (`providers/agy/`, a dispatch target) are separate roles. External dispatch still goes through `providers/<id>/` — including `providers/agy/` when agy is itself the dispatch target.

The lever alias **"all Antigravity"** (or "all agy") means `native-subagents` (harness-native `invoke_subagent`, not external packs).

**Verified as a driver 2026-07-25** by an inception dispatch: a job dispatched *to* agy had it drive a nested dispatch *to* opencode (`opencode run --auto -m opencode-go/deepseek-v4-flash …`) via `run_command`, capturing opencode's stdout and round-tripping a marker cleanly (`STATUS: DONE`, tree untouched). See `providers/agy/verification-log.md`.
