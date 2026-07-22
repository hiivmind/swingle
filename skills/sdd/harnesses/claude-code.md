# Claude Code harness adapter

| Concern | Claude Code mapping |
| --- | --- |
| Skill load | Skill tool: `superpowers:subagent-driven-development` |
| Native subagents | Agent tool; use haiku/sonnet for supervised flavour |
| Task tracking | TodoWrite |
| Background jobs | Bash `run_in_background` plus task notifications; run the self-reaping wrapper inside one background call, and treat notification as finished-or-reaped. If the harness kills the background task itself ("stopped" notification with a healthy log), use the detached form from core/liveness.md: `setsid nohup` the wrapper script, then watch its terminal marker file with the Monitor tool |
| Asset root | `${CLAUDE_PLUGIN_ROOT}` |

The lever alias “all Claude” means `native-subagents`.
