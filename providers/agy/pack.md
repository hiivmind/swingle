# Agy notes

CLI: `agy`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| permission-denied headless run exits successfully with no work | controller can record a phantom success | restore the required permission baseline, then retry | providers/agy/log/2026-07.md |
| Artifact diversion causes a missing workspace report | expected report file is absent | capture the final response through captured-output transport | providers/agy/log/2026-07.md |
| Buffered output gives no progress signal | a healthy run can be killed as stalled | use process existence and a print timeout as the liveness backstop | providers/agy/log/2026-07.md |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `agy models` | model ids carry effort suffixes (`-low/-medium/-high`) and are not guessable from `--help` | `agy --help`, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `agy models` for the live list.
Snapshot 2026-08-23.

- gemini-3.7-flash-low / -medium / -high
- gemini-3.6-flash-medium
- gemini-3.5-flash-high
