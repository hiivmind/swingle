# Devin notes

CLI: `devin`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `-p`/`--print` in a directory not yet trusted interactively exits 1 with "Refusing to run in an untrusted workspace" instead of running | headless dispatch fails immediately with no work done | pass `--respect-workspace-trust false` on every headless dispatch | devin 3000.4.16 (355c3c9e), 2026-08-22 |

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| setting effort for a dispatch | do not attempt to pass an effort parameter; `devin` exposes no CLI-level effort control | `--help` lists only `--model <MODEL>`; no `--effort` flag or bracket-suffix syntax appears anywhere in top-level help or `models --help` | devin 3000.4.16 (355c3c9e) --help, 2026-08-22 |
