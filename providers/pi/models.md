# pi models

pi is provider-agnostic; the reachable namespace is whatever is authed in
`~/.pi/agent/auth.json`. This machine has **opencode-go (Zen)** only, the same backend the
[opencode pack](../opencode/models.md) benchmarked — so the tier assignments mirror it, but
every `verified` status below is stamped from a **live dispatch through `pi`** (not borrowed
from the opencode pack). Model ids use pi's combined `provider/model` form.

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

## Documentary

- **Multi-provider reach.** With additional providers authed, pi also dispatches
  `anthropic/*` (e.g. `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`) and
  `huggingface/*` open-weights directly. None are in a tier slot here because only
  `opencode-go` is authed on this machine — add rows only after a live dispatch through pi
  on a machine where the provider is authed.
- **Model validation is remote** (the provider body, the current registry file): an unlisted id is forwarded as a "custom model
  id" and rejected by the provider at dispatch (`401`, exit 1), never locally. Resolve ids
  from `pi --list-models <provider>`.

## Watch list (unevaluated arrivals, opencode-go catalog)

**Dispatch-confirmed (P12, PONG exit 0) but not yet benchmarked for table slots** (see the
pack's [verification logs](log/)):
- `opencode-go/kimi-k3` (1M ctx, Kimi) — dispatches; evaluate with P13 + implementer probe before table slot
- `opencode-go/grok-4.5` (500K ctx) — dispatches; evaluate before table slot

**Unevaluated (in catalog, no dispatch test):**
- `opencode-go/glm-5.1` (202.8K ctx), `opencode-go/kimi-k2.6` (262K), `opencode-go/mimo-v2.5`,
  `opencode-go/mimo-v2.5-pro`, `opencode-go/minimax-m2.7`, `opencode-go/qwen3.6-plus`,
  `opencode-go/qwen3.7-max`, `opencode-go/hy3` — present in the catalog, not yet
  individually probed. Evaluate with P13 + implementer probe before any table slot.

Zen pricing note: priced on **Zen pay-as-you-go** rates (opencode.ai/docs/zen), mirrored
from the opencode pack (same backend) — re-check on repricing.
