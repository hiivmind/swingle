# agy models (Antigravity)

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

Effort is baked into the model id, or use a base slug with `--effort`. Combining a slug
with the same effort level is harmless; conflicting levels error. Display labels always
carry effort and reject `--effort`.

## Documentary

### Vendor catalog notes

- 3.6 Flash is the current Flash generation; the 3.5 Flash rows in `models.yaml` remain
  verified fallbacks at lower priority.
- 3.5 Flash-Lite is 3.5-class — no 3.6 Lite exists.
- 3.5 Flash Cyber is restricted and is not a dispatch candidate.

### Other inventory notes

| Model | Status | Notes |
| --- | --- | --- |
| `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium` | listed | in-CLI extras; unused — redundant with controller/codex lanes |
| any Flash-Lite | ❌ not exposed | `gemini-3.5-flash-lite` and hypothetical `-3.6-` both rejected as unknown |

### Watch list (unevaluated arrivals)

- agy gaining a Flash-Lite tier — would slot into the cheapest rows *below* 3.6 Flash;
  re-check `agy models` after each agy update.
