# Codex gotchas

CLI: `codex`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin waits for end-of-input and prevents completion | headless dispatch hangs | close stdin with `/dev/null` before launch | providers/codex/log/2026-07.md |
| `codex debug models` reports a per-slug `default_reasoning_level` that does not match the CLI's actual runtime default | effort assumptions built on the catalog field silently miss (luna: catalog says medium, an unset dispatch ran at high) | never infer the effective effort from `default_reasoning_level`; set effort explicitly via `-c model_reasoning_effort=...` or read it back from the dispatch/session output | smoke-test dispatch, 2026-08-23 |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `codex debug models` — a JSON catalog with `slug`, `display_name`, and per-slug `supported_reasoning_levels` | the catalog is buried under `debug` and appears nowhere in top-level help; model ids are not guessable from `--help` | `codex --help` inspection and live catalog probe, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `codex debug models` for the live list.
Snapshot 2026-08-23.

- gpt-5.6-sol (reasoning: low, medium, high, xhigh, max, ultra)
- gpt-5.6-luna (reasoning: low, medium, high, xhigh, max)
