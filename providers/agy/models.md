# agy models (Antigravity) — verified dispatching 2026-07-22

## Resolvable

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | gemini-3.6-flash-low | verified | — | current Flash workhorse; cheapest dispatch lane |
| standard | any | 1 | gemini-3.6-flash-medium | verified | — | verified 2026-07-23: implement + 2 task reviews + resume, all clean gates |
| most-capable | any | 1 | gemini-3.1-pro-high | verified | — | agy's only Pro; verified 2026-07-23 final whole-branch review |

Effort is baked into the model id, or use a base slug with `--effort`; combining both
errors.

## Documentary

### Superseded Flash rows

| Model | Status | Notes |
| --- | --- | --- |
| `gemini-3.5-flash-{low,medium,high}` | ✅ verified | superseded by 3.6 for all Flash rows |

### Other inventory notes

| Model | Status | Notes |
| --- | --- | --- |
| `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium` | listed | in-CLI extras; unused — redundant with controller/codex lanes |
| any Flash-Lite | ❌ not exposed | `gemini-3.5-flash-lite` and hypothetical `-3.6-` both rejected as unknown |

### Watch list (unevaluated arrivals)

- agy gaining a Flash-Lite tier — would slot into the cheapest rows *below* 3.6 Flash;
  re-check `agy models` after each agy update. (from archive/v1.1)

## History

- **2026-07-21 — Google**: Gemini **3.6 Flash** (new workhorse), **3.5 Flash-Lite**
  (cheap/fast; *3.5-class — there is no "3.6 Lite"*), **3.5 Flash Cyber** (restricted).
  Source: blog.google announcement. Table moved all agy Flash rows 3.5 → 3.6 same week. (from archive/v1.1)
- **2026-07-21 — agy 1.1.5**: stable, user-facing model slugs in the `/model` picker and a
  launch-time `--effort` flag for effort variants (per vendor changelog) — the Resolvable
  slug column is now vendor-stable, not scraped convention.
