# grok models (Grok Build / xAI) — seeded 2026-07-24

## Resolvable

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row on seed machine; transcription/explore |
| standard | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; default implement/review |
| most-capable | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; final review until inventory grows |

Effort: `--reasoning-effort` / `--effort` with documented levels
`none|minimal|low|medium|high|xhigh|max` (and per-model menu ids). Record invalid /
silent-ignore behavior in the verification log (P9) before treating effort as trusted.

Status cells must be a single enum ∈ `{verified, experimental, unavailable, superseded, rejected}`.
Promote to `verified` only after P2 + implement-shaped on-disk evidence in this pack's
verification log.

## Documentary

(none yet)

## Watch list

- Additional models appearing in `grok models` after CLI updates — evaluate with P12
  before any table slot.
