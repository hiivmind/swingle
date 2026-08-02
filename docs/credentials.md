# Credentials, CI, and subscription seats

How the CLIs authenticate, what that means for CI, and the honest position on
subscription-seat economics. The README carries the per-CLI CI consequence line; the
detail lives here.

## Authentication per CLI

Whichever dispatch CLIs you use must be on `PATH` and **authenticated once**: `claude`,
`codex`, `opencode`, `agy`, `grok`, `pi`. Most use interactive OAuth; some also accept an API
key — Claude via `ANTHROPIC_API_KEY`, Grok via `XAI_API_KEY`. The credential lives in the
CLI's own auth store, never in a Swingle pack.

## Consequence for CI

An **OAuth-only** CLI needs a human-seeded credential store, so it does not run in
headless CI or ephemeral runners as-is. An **API-key-capable** CLI (Claude, Grok) can,
with the key supplied as a CI secret. Check which mode the CLIs you depend on use before
wiring them into a pipeline — the mode is per CLI, not universal.

## Subscription seats

Swingle's economics work best when it drives CLIs you already run under **flat-rate
subscription seats** rather than metered API keys. Two honest caveats:

- **Framing.** This is *orchestration* — driving tools you already run interactively — not
  *arbitrage*. Unattended, programmatic use of consumer subscription seats can sit near the
  line in some providers' acceptable-use terms; check yours.
- **Degradation.** If a provider closes seat-based CLI use, the CLIs that also
  accept an API key keep working — authenticate that way instead (Claude via
  `ANTHROPIC_API_KEY`, Grok via `XAI_API_KEY`, or any other API-key mode a CLI offers).
  `models.yaml` only picks *which* model. CLIs with no API-key mode lose that route — so
  the fallback is real where an API path exists, not universal.

## Hitting a cap mid-run

A seat usage limit or an API quota surfaces as a **channel failure**, and the controller stops
and adjudicates rather than silently falling back a tier or to another CLI — see
[safety.md](safety.md#when-a-seat-hits-its-cap). Quota-aware automatic fallback is roadmap,
not a feature today.
