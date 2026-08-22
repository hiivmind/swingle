# Codex gotchas

CLI: `codex`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| open stdin waits for end-of-input and prevents completion | headless dispatch hangs | close stdin with `/dev/null` before launch | providers/codex/log/2026-07.md |
