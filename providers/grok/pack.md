# Grok gotchas

CLI: `grok`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| single-object JSON output buffers until exit and can appear stalled | log-age monitoring reports a false stall | switch the invocation to the live CLI's streaming-JSON format (for example, `--output-format streaming-json`, which streams line by line and carries the session id on the end event) so progress signals resume; only then treat unremitting no-output as a real stall | providers/grok/log/2026-07.md |
