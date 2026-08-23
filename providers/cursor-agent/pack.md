# Cursor-agent notes

CLI: `cursor-agent`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `--print` headless run in a directory the CLI has not seen trusted interactively exits 1 with a "Workspace Trust Required" prompt instead of running | headless dispatch fails immediately with no work done | pass `--trust` on every headless dispatch | cursor-agent 2026.07.09-a3815c0, 2026-08-22 |

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| setting effort for a dispatch | fold effort into the `--model` value as a bracket suffix, for example `--model 'sonnet-4-thinking[effort=high]'`; there is no separate `--effort` flag | `--help` documents `--model <model>` as accepting "Parameterized models accept quoted bracket overrides, e.g. `claude-opus-4-8[context=1m,effort=high,fast=false]`" and lists no `--effort` flag | cursor-agent 2026.07.09-a3815c0 --help, 2026-08-22 |
| which models exist | run `cursor-agent models` (account-scoped; the `--list-models` flag is the equivalent one-shot form) | the account's model set differs from any generic list and ids carry effort/fast suffixes not guessable from `--help` alone | `cursor-agent --help` and live listing, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `cursor-agent models` for the live list.
Snapshot 2026-08-23.

- auto (default)
- gpt-5.3-codex-high
- gpt-5.3-codex-fast
- gpt-5.3-codex-low
