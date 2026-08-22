# Opencode gotchas

CLI: `opencode`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin hangs | headless dispatch never completes | close stdin with `/dev/null` before launch | providers/opencode/log/2026-07.md |
| intermittent background startup produces no output until killed and retried | liveness monitoring cannot distinguish startup from a dead run | kill the silent process and retry the dispatch | providers/opencode/log/2026-07.md |
