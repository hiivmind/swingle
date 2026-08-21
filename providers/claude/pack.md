# Claude gotchas

CLI: `claude`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| headless write exits successfully but leaves no change after an unanswered permission request | intended write is missing despite exit 0 | inspect current help for the non-interactive bypass option (the log cites `--dangerously-skip-permissions`), retry with that bypass, and verify the requested change on disk afterward | providers/claude/log/2026-07.md |
| A never-closing non-TTY stdin pipe makes `claude -p` hang until killed | headless subprocess never completes | close stdin with `/dev/null` before launch | issue #73; providers/claude/log/2026-07.md |
