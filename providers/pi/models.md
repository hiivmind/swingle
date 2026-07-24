# pi models — verified dispatching 2026-07-24

pi is provider-agnostic; the reachable namespace is whatever is authed in
`~/.pi/agent/auth.json`. This machine has **opencode-go (Zen)** only, the same backend the
[opencode pack](../opencode/models.md) benchmarked — so the tier assignments mirror it, but
every `verified` status below is stamped from a **live dispatch through `pi`** (not borrowed
from the opencode pack). Model ids use pi's combined `provider/model` form.

## Resolvable

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | opencode-go/deepseek-v4-flash | verified | $0.14/$0.28 | cheapest paid coder; transcription/explore. Dispatched repeatedly through pi (PONG, read, write, shell). |
| standard | implement | 1 | opencode-go/minimax-m3 | verified | $0.30/$1.20 | adaptation (eager — watch over-build). PONG through pi. |
| standard | implement | 2 | opencode-go/qwen3.7-plus | experimental | $0.40/$1.60 | adaptation alternate; in catalog, dispatch-through-pi not yet exercised. |
| standard | review | 1 | opencode-go/deepseek-v4-pro | verified | $1.74/$3.48 | per-task reviewer. PONG through pi. |
| most-capable | implement | 1 | opencode-go/deepseek-v4-pro | verified | $1.74/$3.48 | 1M-ctx heavy implement. PONG through pi. |
| most-capable | implement | 2 | opencode-go/kimi-k2.7-code | experimental | — | coding-strong, 256K ctx; in catalog, dispatch-through-pi not yet exercised. |
| most-capable | review | 1 | opencode-go/glm-5.2 | verified | $1.40/$4.40 | final review; 1M ctx. PONG through pi. |

## Documentary

- **Multi-provider reach.** With additional providers authed, pi also dispatches
  `anthropic/*` (e.g. `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`) and
  `huggingface/*` open-weights directly. None are in a tier slot here because only
  `opencode-go` is authed on this machine — add rows only after a live dispatch through pi
  on a machine where the provider is authed.
- **Model validation is remote** (pack.md): an unlisted id is forwarded as a "custom model
  id" and rejected by the provider at dispatch (`401`, exit 1), never locally. Resolve ids
  from `pi --list-models <provider>`.

## Watch list (unevaluated arrivals, opencode-go catalog 2026-07-24)

- `opencode-go/kimi-k3` (1M ctx), `opencode-go/grok-4.5` (500K), `opencode-go/mimo-v2.5-pro`,
  `opencode-go/qwen3.7-max`, `opencode-go/hy3` — present in the catalog, not yet
  benchmarked or priced against the table. Evaluate with the P13 reviewer benchmark + a
  small implementer probe before any table slot.

Zen pricing note: priced on **Zen pay-as-you-go** rates (opencode.ai/docs/zen), mirrored
from the opencode pack (same backend) — re-check on repricing.
