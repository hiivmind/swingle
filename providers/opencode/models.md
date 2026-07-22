# opencode models (Zen) — verified dispatching 2026-07-22

## Resolvable

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | opencode-go/deepseek-v4-flash | verified | $0.14/$0.28 | cheapest paid coder; transcription/explore |
| standard | implement | 1 | opencode-go/minimax-m3 | verified | $0.30/$1.20 | adaptation (eager — watch over-build) |
| standard | implement | 2 | opencode-go/qwen3.7-plus | verified | $0.40/$1.60 | adaptation alternate |
| standard | review | 1 | opencode-go/deepseek-v4-pro | verified | $1.74/$3.48 | per-task reviewer (caught planted defect) |
| most-capable | implement | 1 | opencode-go/deepseek-v4-pro | verified | $1.74/$3.48 | 1M ctx heavy implement |
| most-capable | implement | 2 | opencode-go/kimi-k2.7-code | experimental | — | coding-strong, 256K ctx |
| most-capable | review | 1 | opencode-go/glm-5.2 | verified | $1.40/$4.40 | final review; #1 open-weights AA 51 |

## Documentary

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

Zen pricing note: priced/picked on **Zen pay-as-you-go** rates (opencode.ai/docs/zen), not list API. (from archive/v1.1)

## History

- **2026-07-21 — Google**: Gemini **3.6 Flash** (new workhorse), **3.5 Flash-Lite**
  (cheap/fast; *3.5-class — there is no "3.6 Lite"*), **3.5 Flash Cyber** (restricted).
  Source: blog.google announcement. Table moved all agy Flash rows 3.5 → 3.6 same week. (mirror; from archive/v1.1)
