# Codex controller adapter

| Concern | Codex mapping |
| --- | --- |
| Skill load | superpowers Codex adaptation (`references/codex-tools.md`) |
| Native subagents | `spawn_agent` |
| Task tracking | `update_plan` |
| Background jobs | shell background plus a poll loop; use the same self-reaping wrapper and check it between turns |
| Asset root | Resolve from the physical path of this SKILL.md: `<root> = dirname(dirname(dirname(SKILL.md)))` |

Codex-as-provider under a Codex controller is allowed. Nested `codex exec` may be blocked by
sandbox policy, so run a one-shot nested-exec probe at the first Codex-lane dispatch and
treat failure as a channel-class failure (user question). There is no prohibition.
