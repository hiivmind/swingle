# Codex gotchas

CLI: `codex`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin waits for end-of-input and prevents completion | headless dispatch hangs | close stdin with `/dev/null` before launch | providers/codex/log/2026-07.md |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `codex debug models` — a JSON catalog with `slug`, `display_name`, and per-slug `supported_reasoning_levels` | the catalog is buried under `debug` and appears nowhere in top-level help; model ids are not guessable from `--help` | `codex --help` inspection and live catalog probe, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `codex debug models` for the live list.
Snapshot 2026-08-23.

- gpt-5.6-sol (reasoning: low, medium, high, xhigh, max, ultra)
- gpt-5.6-luna (reasoning: low, medium, high, xhigh, max)
