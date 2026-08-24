# Grok notes

CLI: `grok`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| single-object JSON output buffers until exit and can appear stalled | log-age monitoring reports a false stall | switch the invocation to the live CLI's streaming-JSON format (for example, `--output-format streaming-json`, which streams line by line and carries the session id on the end event) so progress signals resume; only then treat unremitting no-output as a real stall | providers/grok/log/2026-07.md |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | run `grok models` — prints login status, the account default, and the available list | the default model is surfaced here and nowhere in top-level help | `grok --help` and live listing, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `grok models` for the live list.
Snapshot 2026-08-23.

- grok-4.6 (account default)
- grok-4.5
