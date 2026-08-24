# Omp notes

CLI: `omp`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `omp models` — grouped by upstream provider with context/max-out/thinking columns, plus list/search/refresh actions; `--model` fuzzy-matches short forms (`opus`, `gpt-5.2`) and full ids (`openai/gpt-5.2`) | omp aggregates many upstream providers, so the id space is far larger than any guess and the grouping is the only map | `omp --help` and live listing, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `omp models` for the live list.
Snapshot 2026-08-23.

- claude-fable-5 (1M context)
- claude-opus-4-7
- claude-haiku-4-5
