# Pi notes

CLI: `pi`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin can end in `RangeError: Invalid string length` | headless dispatch crashes before completing | close stdin with `/dev/null` before launch | providers/pi/log/2026-07.md; issue #71 |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `pi --list-models [search]` — a table with provider, context, max-out, thinking, and images columns; `--model` takes `provider/id` and an optional `:<thinking>` suffix | pi aggregates many upstream providers; the suffix syntax appears only in help examples and is easy to miss | `pi --help` and live listing, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `pi --list-models` for the live list.
Snapshot 2026-08-23.

- opencode-go/gpt-5.6-luna
- opencode-go/deepseek-v4-pro
- opencode-go/glm-5.2
