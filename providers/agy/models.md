# agy models (Antigravity) — verified dispatching 2026-07-22

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

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
