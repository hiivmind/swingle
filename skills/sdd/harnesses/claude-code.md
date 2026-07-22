# Claude Code harness adapter

| Concern | Claude Code mapping |
| --- | --- |
| Skill load | Skill tool: `superpowers:subagent-driven-development` |
| Native subagents | Agent tool; use haiku/sonnet for supervised flavour |
| Task tracking | TodoWrite |
| Background jobs | Bash `run_in_background` plus task notifications; run the self-reaping wrapper inside one background call, and treat notification as finished-or-reaped |
| Asset root | `${CLAUDE_PLUGIN_ROOT}` |

The lever alias “all Claude” means `native-subagents`.
