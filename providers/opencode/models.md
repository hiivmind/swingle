# opencode models (OpenCode Go)

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

## Documentary

- **All six table models dispatch with their listed statuses.**
  `opencode-go/deepseek-v4-flash` requires a China-hosting workspace opt-in; see pack.md
  Guidance and the pack's verification log.
- **Catalog arrivals not yet benchmarked:** `opencode-go/gpt-5.6-luna`,
  `opencode/big-pickle`, and `opencode/ling-3.0-flash-free` are in the watch list below.
  They require the P13 reviewer benchmark and a small-implementer probe before a table slot.

`opencode/nemotron-3-ultra-free` — ❌ rejected. See the [provider verification log](verification-log.md) for the reviewer and implementer probe findings.

**Free-tier namespace + caveat:** all `-free` models live under `opencode/` (never
`opencode-go/`). Trial-use: prompts are logged and may train/improve the
provider's products — throwaway/OSS work only, never proprietary code.

## Watch list (unevaluated arrivals)

- `opencode-go/gpt-5.6-luna` — dispatches but is not yet benchmarked/priced against the table.
- `opencode/big-pickle`, `opencode/ling-3.0-flash-free` — free-tier arrivals that dispatch
  with the trial-use data caveat.
  Evaluate with the known-defect reviewer benchmark + small implementer probe before any
  table slot.
- `opencode/laguna-s-2.1-free`, `opencode/mimo-v2.5-free`, `opencode/north-mini-code-free`
  — free tiers with the trial-use data caveat. Evaluate with the
  known-defect reviewer benchmark + small implementer probe before any table slot.
- `opencode-go/glm-5.1`, `hy3`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m2.7`,
  `qwen3.6-plus` — not yet benchmarked/priced against the table.
- `opencode-go/kimi-k3`, `opencode-go/grok-4.5`, `opencode-go/qwen3.7-max` — not yet
  benchmarked/priced against the table. Re-check `qwen3.7-max` if repriced.

Pricing note: priced/picked on **Zen pay-as-you-go** rates (opencode.ai/docs/zen) where
applicable, not list API.
