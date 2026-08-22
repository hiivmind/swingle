# Cursor-agent notes

CLI: `cursor-agent`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `--print` headless run in a directory the CLI has not seen trusted interactively exits 1 with a "Workspace Trust Required" prompt instead of running | headless dispatch fails immediately with no work done | pass `--trust` on every headless dispatch | cursor-agent 2026.07.09-a3815c0, 2026-08-22 |

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| setting effort for a dispatch | fold effort into the `--model` value as a bracket suffix, for example `--model 'sonnet-4-thinking[effort=high]'`; there is no separate `--effort` flag | `--help` documents `--model <model>` as accepting "Parameterized models accept quoted bracket overrides, e.g. `claude-opus-4-8[context=1m,effort=high,fast=false]`" and lists no `--effort` flag | cursor-agent 2026.07.09-a3815c0 --help, 2026-08-22 |
