# Grok harness adapter

| Concern | Grok mapping |
| --- | --- |
| Skill load | Skills are session-discovered (plugins + Claude/Cursor compat). There is **no** Claude `Skill(...)` tool. To load superpowers SDD: read and follow the loaded skill **`subagent-driven-development`** (plugin: superpowers). To run this plugin: read and follow **`sdd`** (plugin: sdd-dispatch). Same pattern for `delegate` / `sdd-dispatch-verify`. Announce the skill name, then follow its body. |
| Native subagents | `spawn_subagent` tool — built-in types include `general-purpose`, `explore`, `plan` (see Grok user-guide 16-subagents). Use a cheap/general child for supervised pack dispatch. |
| Task tracking | `todo_write` |
| Background jobs | Run the self-reaping wrapper from `core/liveness.md` (detached `setsid nohup` form when the parent session may reap children). Observe completion via the wrapper marker file / process exit; use the session `monitor` tool when available for long watches. Do not rely on Claude-style `run_in_background` task notifications. |
| Asset root | **Installed plugin:** `$GROK_PLUGIN_ROOT` (hooks also set Claude aliases `$CLAUDE_PLUGIN_ROOT` / `$CLAUDE_PLUGIN_DATA`). **Repo checkout or symlink:** resolve from the physical path of `skills/sdd/SKILL.md`: `<root> = dirname(dirname(dirname(SKILL.md)))` so `<root>/core` and `<root>/providers` exist. Prefer the physical path over a cache path when both are present (write verification logs only to a writable source tree). |

Grok-as-**controller** and Grok-as-**provider** are separate: this adapter is for when Grok is the controlling session. External dispatch still goes through `providers/<id>/` (including `providers/grok/` when the pack is the dispatch target).

The lever alias **“all Grok”** means `native-subagents` (harness-native `spawn_subagent`, not external packs).
