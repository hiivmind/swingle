# Copilot notes

CLI: `copilot`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `-p`/`--prompt` dispatch that needs a tool (write, shell) loops retrying different approaches with "Permission denied and could not request permission from user" on each attempt, then never exits on its own | headless dispatch hangs indefinitely instead of failing fast, burning AI credits until killed | pass `--allow-all-tools` on every headless dispatch that may need to write files or run commands | GitHub Copilot CLI 1.0.79, 2026-08-22 |

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| setting effort for a dispatch | pass a fully separate `--effort`/`--reasoning-effort <level>` flag alongside `--model`; the enum is `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` | `--help` documents `--effort, --reasoning-effort <level>` as its own flag, independent of `--model <model>`, with the enum values stated in help rather than left to guesswork | GitHub Copilot CLI 1.0.79 --help, 2026-08-22 |
| which models exist | there is no headless model-listing subcommand or flag; `copilot help billing` covers credit usage (shown in the interactive footer) but lists no models | searching for a listing command is a dead end; ground model names against the live CLI by invoking it, not from cached notes | full `copilot --help` and `help billing` inspection, 2026-08-23 |
