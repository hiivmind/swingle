# Pi gotchas

CLI: `pi`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin can end in `RangeError: Invalid string length` | headless dispatch crashes before completing | close stdin with `/dev/null` before launch | providers/pi/log/2026-07.md; issue #71 |
