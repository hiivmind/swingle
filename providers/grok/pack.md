# Grok gotchas

CLI: `grok`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| single-object JSON output buffers until exit and can appear stalled | log-age monitoring reports a false stall | wait for process exit before treating the run as stalled | providers/grok/log/2026-07.md |
