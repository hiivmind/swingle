# Opencode gotchas

CLI: `opencode`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin hangs | headless dispatch never completes | close stdin with `/dev/null` before launch | providers/opencode/log/2026-07.md |
| intermittent background startup produces no output until killed and retried | liveness monitoring cannot distinguish startup from a dead run | kill the silent process and retry the dispatch | providers/opencode/log/2026-07.md |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `opencode models` — ids are provider-prefixed (`openai/gpt-5.6-luna`, `opencode/claude-fable-5`); pass the full prefixed id to `--model` | opencode aggregates many upstream providers; stripping or guessing the prefix produces ids the CLI rejects | `opencode --help` and live listing, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `opencode models` for the live list.
Snapshot 2026-08-23.

- openai/gpt-5.6-sol
- openai/gpt-5.6-luna
- opencode/claude-fable-5
