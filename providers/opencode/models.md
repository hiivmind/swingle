# opencode models (OpenCode Go) — verified dispatching 2026-07-31

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

## Documentary

- **1.18.10 re-verification (2026-07-31): all six table models still dispatch, no
  status changes.** `opencode-go/deepseek-v4-flash` required a one-time China-hosting
  workspace opt-in before it would dispatch on this run's workspace — see pack.md
  Guidance; not a code defect, and no action needed once opted in.
- **New catalog arrivals, not yet benchmarked (2026-07-31):** `opencode-go/gpt-5.6-luna`
  (new since the 2026-07-29 listing); `opencode/big-pickle`, `opencode/ling-3.0-flash-free`
  (new free-tier arrivals). This round's trigger was a CLI version bump, not a model
  release, so none were run against the P13 reviewer benchmark or a small-implementer
  probe — added to the watch list below.

`opencode/nemotron-3-ultra-free` — ❌ rejected (2026-07-22). See the [provider verification log](verification-log.md) for the reviewer and implementer probe findings. (from archive/v1.1)

**Free-tier namespace + caveat:** all `-free` models live under `opencode/` (never
`opencode-go/`). Trial-use: prompts are logged and may train/improve the
provider's products — throwaway/OSS work only, never proprietary code. (from archive/v1.1)

## Watch list (unevaluated arrivals)

- `opencode-go/gpt-5.6-luna` — new since 2026-07-29's listing; confirmed dispatching
  (PONG, exit 0) 2026-07-31, not yet benchmarked/priced against the table.
- `opencode/big-pickle`, `opencode/ling-3.0-flash-free` — new free-tier arrivals spotted
  2026-07-31 (trial-use data caveat presumed); confirmed dispatching (PONG, exit 0).
  Evaluate with the known-defect reviewer benchmark + small implementer probe before any
  table slot.
- `opencode/laguna-s-2.1-free`, `opencode/mimo-v2.5-free`, `opencode/north-mini-code-free`
  — new free tiers spotted 2026-07-22 (trial-use data caveat presumed). Evaluate with the
  known-defect reviewer benchmark + small implementer probe before any table slot. (from archive/v1.1)
- `opencode-go/glm-5.1`, `hy3`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m2.7`,
  `qwen3.6-plus` — spotted 2026-07-29, not yet benchmarked/priced against the table.
- `opencode-go/kimi-k3`, `opencode-go/grok-4.5`, `opencode-go/qwen3.7-max` — appeared by
  2026-07-22, not yet benchmarked/priced against the table. (`qwen3.7-max` was previously
  dropped as dominated by glm-5.2 on both quality and price — re-check if repriced.) (from archive/v1.1)

Pricing note: priced/picked on **Zen pay-as-you-go** rates (opencode.ai/docs/zen) where
applicable, not list API. (from archive/v1.1)

## History

- **2026-07-21 — Google**: Gemini **3.6 Flash** (new workhorse), **3.5 Flash-Lite**
  (cheap/fast; *3.5-class — there is no "3.6 Lite"*), **3.5 Flash Cyber** (restricted).
  Source: blog.google announcement. Table moved all agy Flash rows 3.5 → 3.6 same week. (mirror; from archive/v1.1)
