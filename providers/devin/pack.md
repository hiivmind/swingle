# Devin notes

CLI: `devin`

## Gotchas

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| `-p`/`--print` in a directory not yet trusted interactively exits 1 with "Refusing to run in an untrusted workspace" instead of running | headless dispatch fails immediately with no work done | pass `--respect-workspace-trust false` on every headless dispatch | devin 3000.4.16 (355c3c9e), 2026-08-22 |

## Dispatch guidance

| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| setting effort for a dispatch | do not attempt to pass an effort parameter; `devin` exposes no CLI-level effort control | `--help` lists only `--model <MODEL>`; no `--effort` flag or bracket-suffix syntax appears anywhere in top-level help or `models --help` | devin 3000.4.16 (355c3c9e) --help, 2026-08-22 |
| which models exist, and what they cost | run `devin models list` — families with aliases, effort-suffixed slugs, and inline per-model prices (`$X / 1M Input · $Y / 1M Output`) | the listing is the only place prices and family aliases appear; ids are not guessable from `--help` | `devin --help`, `devin models list` live output, 2026-08-23 |

## Typical models

Orientation only — not definitive, not a gate. Run `devin models list` for the live list
(with current prices). Snapshot 2026-08-23.

- claude-opus-5-high
- gemini-3-7-flash-high
- gpt-5.6-sol (family)
