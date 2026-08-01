# Claude Code controller adapter

| Concern | Claude Code mapping |
| --- | --- |
| Skill load | Skill tool: `superpowers:subagent-driven-development` |
| Native subagents | Agent tool; use haiku/sonnet for supervised flavour |
| Task tracking | TodoWrite |
| Background jobs | Bash `run_in_background` plus task notifications; run the self-reaping wrapper inside one background call, and treat notification as finished-or-reaped. If Claude Code kills the background task itself ("stopped" notification with a healthy log), use the detached form from core/liveness.md: `setsid nohup` the wrapper script, then watch its terminal marker file with the Monitor tool |
| Asset root | `${CLAUDE_PLUGIN_ROOT}` |

The lever alias “all Claude” means `native-subagents` — the in-session Agent tool, **not**
the `claude` provider pack. Both now exist under this controller, so keep them distinct:

- **“all Claude” / `native-subagents`** → Agent tool, no external process, no model
  resolution. The default for in-session Claude work.
- **“via claude”** → the external `claude` provider pack (`providers/claude/`), a real
  `claude -p` subprocess through the pack's dispatch template and model tiers. Use it only
  when isolation from this session is the point (a clean sub-context, cross-CLI parity).
  It carries the self-dispatch traps in `providers/claude/pack.md`: the parent auto-mode
  Bash classifier blocks the write-enabling flag, and the child-session env vars must be
  cleared. Prefer `native-subagents` for ordinary Claude-on-Claude work; reach for the
  provider only when its isolation is worth those two frictions.
