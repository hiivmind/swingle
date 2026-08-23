# Claude gotchas

CLI: `claude`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| headless write exits successfully but leaves no change after an unanswered permission request | intended write is missing despite exit 0 | inspect current help for the non-interactive bypass option (the log cites `--dangerously-skip-permissions`), retry with that bypass, and verify the requested change on disk afterward | providers/claude/log/2026-07.md |
| A never-closing non-TTY stdin pipe makes `claude -p` hang until killed | headless subprocess never completes | close stdin with `/dev/null` before launch | issue #73; providers/claude/log/2026-07.md |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| which models exist | there is no model-listing subcommand or flag; ground model names in the `--model` help text, which names the current aliases (`fable`, `opus`, `sonnet`) and the full-name form (`claude-fable-5`) | searching for a listing command is a dead end and costs probes; the help examples are the only discovery surface | full `claude --help` inspection, 2026-08-23 |
