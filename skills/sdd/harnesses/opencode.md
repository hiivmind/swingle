# opencode harness adapter

| Concern | opencode mapping |
| --- | --- |
| Skill load | Real `skill` tool. Skills register under their **bare frontmatter `name`** — there is no plugin namespace, so it is `skill(sdd)` / `skill(delegate)` / `skill(sdd-dispatch-verify)`, and superpowers SDD is `skill(subagent-driven-development)`. If the tool refuses, check `permission.skill` in `opencode.json` (`"*": "allow"` by default; `deny` hides a skill entirely, `ask` prompts). |
| Native subagents | `task` tool with `subagent_type`; built-in types are `build`, `plan`, `general`, `explore`. **Nesting is capped by `subagent_depth` (default `1`)** — a subagent cannot itself call `task`. Dispatch lanes are unaffected (subagents shell out to the provider CLI via `bash`, which is not a nested `task`), but any plan step that wants a subagent to spawn its own subagent needs `"subagent_depth": 2` in `opencode.json` first. |
| Task tracking | `todowrite` |
| Background jobs | **The `bash` tool has no background mode** — it takes only `timeout` (default 120000 ms). There is no `run_in_background` and no task-notification path for shell work. Always use the **detached** form from `core/liveness.md`: write the dispatch script to a file, launch it with `setsid nohup <script> >/dev/null 2>&1 </dev/null &` plus `disown`, record the CLI pid to a pid file, and have the wrapper append its terminal line to a marker file. Poll that marker with short `bash` calls between turns (`cat <marker> 2>/dev/null`) — there is no Monitor-style watcher tool. Do not raise `timeout` to hold a dispatch in the foreground: it blocks the controller and disables the stall rule. (`task` has a `background: true` flag, but it is gated behind `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` and applies to subagents, not to dispatch shells.) |
| Asset root | No plugin-root env var exists. Resolve from the **physical** path of `skills/sdd/SKILL.md`: `<root> = dirname(dirname(dirname(SKILL.md)))`, so `<root>/core` and `<root>/providers` exist. opencode scans skill dirs with symlinks followed, so a symlink install reports the link path — resolve it (`readlink -f`) before deriving `<root>`, and write verification logs only to the resulting source tree. |

## Discovery — know which route installed you

opencode finds skills from four places, merged into one set (`skill/index.ts`):
`~/.claude/skills/**/SKILL.md` and `.claude/skills/**` walking cwd→worktree root;
the same under `.agents/`; `{skill,skills}/**/SKILL.md` under each `.opencode` config
dir; and `**/SKILL.md` under every entry of `skills.paths` in `opencode.json`.
Install by exactly one route — two routes pointing at the same checkout register the
same skill twice. If the skills vanish, check `OPENCODE_DISABLE_EXTERNAL_SKILLS` and
`OPENCODE_DISABLE_CLAUDE_CODE`, which switch off the `.claude`/`.agents` compat scan.

## opencode-as-controller dispatching the opencode pack

Allowed, and unlike Codex there is no sandbox to probe (`providers/opencode/pack.md`
records `sandbox: none`). The hazard is session identity instead.

`providers/opencode/pack.md` sets `session-source: session-list`, i.e. the dispatched
session id is recovered from `opencode session list` rather than the run log. Under an
opencode controller that list **also contains the controller's own session and every
`task` subagent session**, so "take the newest entry" will hand you the wrong id and a
later `opencode run -s <id>` will resume the controller instead of the dispatch.

Snapshot before, diff after:

```bash
opencode session list > "$WORK/sessions.before"
# ... dispatch ...
comm -13 <(sort "$WORK/sessions.before") <(opencode session list | sort)
```

Exactly one new id should appear per dispatch. Zero or more than one means the
attribution is unsafe — treat it as a channel-class failure and ask the user rather
than resuming a guessed id.

The lever alias **"all opencode"** means `native-subagents` (harness-native `task`, not
external packs).
