# Agy gotchas

CLI: `agy`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| permission-denied headless run exits successfully with no work | controller can record a phantom success | restore the required permission baseline, then retry | providers/agy/log/2026-07.md |
| Artifact diversion causes a missing workspace report | expected report file is absent | capture the final response through captured-output transport | providers/agy/log/2026-07.md |
| Buffered output gives no progress signal | a healthy run can be killed as stalled | use process existence and a print timeout as the liveness backstop | providers/agy/log/2026-07.md |
