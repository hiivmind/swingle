# omp models

omp (Oh My Pi) is a mega-router: one CLI reaching five backends through the operator's own
subscriptions/OAuth — `anthropic`, `openai-codex`, `google-antigravity`, `opencode-go`
(metered Zen), and `xai-oauth`. `--model` fuzzy-matches an id from `omp models`.

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, tiering rationale, and watch lists.

## Tiering — subscription-first

The tier slots deliberately prefer the **flat-rate subscription backends** (Anthropic Max,
ChatGPT/codex, Antigravity) and keep the metered `opencode-go` Zen backend out of the
default routes, so routing to omp does not incur per-token spend:

- **cheapest / any** → `gemini-3.6-flash` (Antigravity) — fast agentic/coding lane.
- **standard / implement** → `claude-sonnet-4-5` (Max, 1M ctx); fallback `gpt-5.5` (codex).
- **standard / review** → `gpt-5.6-terra` (codex — doctrine prefers GPT-5.6 for structured
  reviews); fallback `claude-sonnet-4-5`.
- **most-capable / implement** → `claude-opus-4-5` (Max); fallback `gpt-5.6-sol` (codex).
- **most-capable / review** → `gpt-5.6-sol` (codex); fallback `claude-opus-4-5`.

## Documentary

- **`verified` is stamped from a live dispatch through omp**, not borrowed from a sibling
  pack. Verified this round (omp 17.2.4): `gemini-3.6-flash` (PONG + session resume),
  `claude-sonnet-4-5` (full write + bash tool-use under `--auto-approve`), `claude-opus-4-5`
  (PONG). See [log/](log/).
- **Review lanes are `experimental` pending P13.** `gpt-5.6-terra` / `gpt-5.6-sol` dispatch
  cleanly (PONG through omp) and are the doctrine-preferred review models, but the review
  severity-qualification probe (P13 — rate a planted directory-crash defect ≥Important) has
  not yet been run *through omp*. They stay eligible-but-flagged until it is.
- **Model validation is remote/at-dispatch.** An unauthed or absent backend fails only when
  the dispatch runs (exit 1, "No API key found for <provider>"), never locally. `omp models`
  lists only authed backends but exits 0 even with none authed — it is a catalog, not an
  auth gate (hence no `readiness-argv`; preflight reports `available (auth unverified)`).

## Watch list (unevaluated arrivals)

Present in the `omp models` catalog, not yet dispatch-probed through omp — evaluate with a
PONG + implementer probe (and P13 for any review slot) before a table slot:

- Anthropic: `claude-sonnet-4-6`, `claude-haiku-4-5` (P2 fallback, seeded experimental).
- openai-codex: `gpt-5.6-luna`, `gpt-5.4` / `gpt-5.4-mini`.
- google-antigravity: `gemini-3.1-pro`, `gemini-3.5-flash`.
- opencode-go (metered — intentionally off the default routes): `deepseek-v4-pro`, `glm-5.2`,
  `kimi-k2.7-code`, `kimi-k3`.
- xai-oauth: `grok-4.5`, `grok-4.3`.
