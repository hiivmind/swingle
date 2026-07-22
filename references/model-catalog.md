# SDD Model Catalog & Tiering

> Living document. The role→model table below is THE policy — the `sdd` skill reads it
> at Step 0; there is no separate copy to keep in sync.
> Model inventories are as observed via `codex` dispatch, `opencode models`, and `agy models`
> on the stamp date.

## Role → tier → model (policy table, synced 2026-07-22)

| SDD role | Tier | codex | opencode | agy | Mode |
| --- | --- | --- | --- | --- | --- |
| Transcription implementer (complete code in brief) | cheapest | `gpt-5.6-luna` | `opencode-go/deepseek-v4-flash` | `gemini-3.6-flash-low` | bg, write |
| Adaptation implementer (prose/design/debug) | standard | `gpt-5.6-terra` | `opencode-go/minimax-m3` / `opencode-go/qwen3.7-plus` | `gemini-3.6-flash-medium` | bg, write |
| Large-codebase / long-context implement | most capable | `gpt-5.6-sol` | `opencode-go/deepseek-v4-pro` / `opencode-go/kimi-k2.7-code` | `gemini-3.1-pro-high` | bg, write |
| Read-only codebase explore ("where is X") | cheapest | `gpt-5.6-luna` | `opencode-go/deepseek-v4-flash` | `gemini-3.6-flash-low` | bg, read-only* |
| External research / synthesis (long-context) | standard | `gpt-5.6-terra` | `opencode-go/kimi-k2.7-code` | `gemini-3.6-flash-medium` | bg, read-only* |
| Per-task reviewer (spec + quality, scale to diff) | standard | `gpt-5.6-terra` | `opencode-go/deepseek-v4-pro` | `gemini-3.6-flash-medium` | bg, read-only* |
| Final whole-branch / design review | most capable | `gpt-5.6-sol` | `opencode-go/glm-5.2` | `gemini-3.1-pro-high` | bg, read-only* |

\* "read-only" is an *intent*, enforced only on codex — agy/opencode have no read-only tier
(see dispatch-reference.md safety doctrine): clean tree before, diff after.

**Tiering rules:**
- **Turn count beats token price** — cheapest models take 2–3× the turns on multi-step work;
  standard is the floor for reviewers and prose-brief implementers.
- Scale reviewer power to the **diff's** size/risk. Final whole-branch review is
  architecture-class — always most capable.
- Prefer **codex** for structured code/design reviews (clean stdout contract, sandbox,
  server-validated knobs); reach for agy/opencode for Gemini/open-weights perspective.

## Provider inventories

### codex (ChatGPT account) — verified dispatching 2026-07-22
| Model | Status | Notes |
| --- | --- | --- |
| `gpt-5.6-luna` | ✅ verified | cheapest; **long-context recall ~41%** — bump to Terra on large codebases |
| `gpt-5.6-terra` | ✅ verified | standard workhorse; ~90% long-context recall |
| `gpt-5.6-sol` | ✅ verified | most capable; ~90% long-context recall |

### agy / Antigravity (v1.1.4) — `agy models`, 2026-07-22
| Model | Status | Notes |
| --- | --- | --- |
| `gemini-3.6-flash-{low,medium,high}` | ✅ verified (low) | **current Flash workhorse** — released 2026-07-21; DeepSWE 49% vs 3.5's 37%, OSWorld 83.0 vs 78.4, ~17% fewer output tokens (better *and* cheaper) |
| `gemini-3.5-flash-{low,medium,high}` | ✅ verified | superseded by 3.6 for all Flash rows |
| `gemini-3.1-pro-{low,high}` | listed | **agy's only Pro** (no 3.5/3.6 Pro exists in agy) — reserve for long-context + hardest architecture |
| `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium` | listed | in-CLI extras; redundant with controller/codex lanes |
| ~~any Flash-Lite~~ | ❌ not exposed | `gemini-3.5-flash-lite` and hypothetical `-3.6-` both rejected as unknown (probed 2026-07-22) |

### opencode / Zen (v1.17.18) — `opencode models`, 2026-07-22
Priced/picked on **Zen pay-as-you-go** rates (opencode.ai/docs/zen), not list API.
`opencode/` and `opencode-go/` are distinct namespaces.

| Model | Status | Rationale |
| --- | --- | --- |
| `opencode-go/deepseek-v4-flash` | ✅ verified | cheapest paid coder (~$0.14/$0.28, near-V4-Pro coding) → transcription/explore |
| `opencode/deepseek-v4-flash-free` | listed (`opencode/` only) | free tier for high-volume mechanical work |
| `opencode-go/deepseek-v4-pro` | listed | 1M ctx, SWE-V 80.6 → long-context heavy implement |
| `opencode-go/glm-5.2` | listed | #1 open-weights intelligence (AA 51) → review rows |
| `opencode-go/minimax-m3`, `opencode-go/qwen3.7-plus` | listed | cheap reasoning coders → adaptation (not transcription; minimax over-builds) |
| `opencode-go/kimi-k2.7-code` | listed | coding-strong, 256K ctx |
| `opencode/gemini-3.5-flash-lite` | ✅ verified | **the only route to Flash-Lite** ($0.30/$2.50, 350 tok/s) — doesn't undercut deepseek-v4-flash; a latency/Gemini-flavour option, not a new floor |
| `opencode/gemini-3.6-flash` | listed | Gemini 3.6 via Zen, alternative to agy lane |

## Watch list (unevaluated arrivals)

- `opencode-go/kimi-k3`, `opencode-go/grok-4.5`, `opencode-go/qwen3.7-max` — appeared by
  2026-07-22, not yet benchmarked/priced against the table. (`qwen3.7-max` was previously
  dropped as dominated by glm-5.2 on both quality and price — re-check if repriced.)
- `Gemini 3.5 Flash Cyber` — limited-access pilot (governments/partners via CodeMender);
  not generally available, not in agy or Zen.
- agy gaining a Flash-Lite tier — would slot into the cheapest rows *below* 3.6 Flash;
  re-check `agy models` after each agy update.

## Release history

- **2026-07-21 — Google**: Gemini **3.6 Flash** (new workhorse), **3.5 Flash-Lite**
  (cheap/fast; *3.5-class — there is no "3.6 Lite"*), **3.5 Flash Cyber** (restricted).
  Source: blog.google announcement. Table moved all agy Flash rows 3.5 → 3.6 same week.
