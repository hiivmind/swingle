# opencode models (OpenCode Go) — verified dispatching 2026-07-29

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

## Documentary

- **1.18.9 re-verification (2026-07-29): all six table models still dispatch, no status
  changes.** Auth mode this round was OpenCode Go (subscription tier), not Zen
  (pay-as-you-go) — the table is already entirely `opencode-go/`-namespaced so no
  migration was needed. See [verification-log.md](verification-log.md) for the full
  probe matrix, including a stdin-hang refutation that changed the canonical dispatch
  template (stdin must now always be redirected) and a `-p`-collision wording refinement.
- **New catalog arrivals, not yet benchmarked (2026-07-29):** `opencode-go/glm-5.1`,
  `hy3`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m2.7`, `qwen3.6-plus` — this
  round's trigger was a CLI version bump, not a model release, so these were not run
  against the P13 reviewer benchmark or a small-implementer probe. Add to the watch list
  below; evaluate before any table slot.

`opencode/nemotron-3-ultra-free` — ❌ rejected (2026-07-22). See the [provider verification log](verification-log.md) for the reviewer and implementer probe findings. (from archive/v1.1)

**Free-tier namespace + caveat:** all `-free` models live under `opencode/` (never
`opencode-go/`). Zen marks them trial-use: prompts are logged and may train/improve the
provider's products — throwaway/OSS work only, never proprietary code. (from archive/v1.1)

## Watch list (unevaluated arrivals)

- `opencode/laguna-s-2.1-free`, `opencode/mimo-v2.5-free`, `opencode/north-mini-code-free`
  — new free tiers spotted 2026-07-22 (trial-use data caveat presumed). Evaluate with the
  known-defect reviewer benchmark + small implementer probe before any table slot. (from archive/v1.1)
- `opencode-go/kimi-k3`, `opencode-go/grok-4.5`, `opencode-go/qwen3.7-max` — appeared by
  2026-07-22, not yet benchmarked/priced against the table. (`qwen3.7-max` was previously
  dropped as dominated by glm-5.2 on both quality and price — re-check if repriced.) (from archive/v1.1)
- `opencode-go/glm-5.1`, `hy3`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m2.7`,
  `qwen3.6-plus` — spotted 2026-07-29 during the 1.18.9 re-verification's model listing,
  not yet benchmarked/priced against the table.

Zen pricing note: priced/picked on **Zen pay-as-you-go** rates (opencode.ai/docs/zen), not list API. (from archive/v1.1)

## History

- **2026-07-21 — Google**: Gemini **3.6 Flash** (new workhorse), **3.5 Flash-Lite**
  (cheap/fast; *3.5-class — there is no "3.6 Lite"*), **3.5 Flash Cyber** (restricted).
  Source: blog.google announcement. Table moved all agy Flash rows 3.5 → 3.6 same week. (mirror; from archive/v1.1)
