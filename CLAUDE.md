# CLAUDE.md — sdd-dispatch plugin

Harness-neutral plugin for SDD execution via external CLIs (codex / opencode / agy).
This repository is simultaneously a **Claude Code plugin** (`.claude-plugin/`), a
**Codex plugin** (`.codex-plugin/` + `.agents/plugins/marketplace.json`), and a plain
skills tree — treat all three distribution surfaces as first-class.

## The one hard gate

Before every commit:

```bash
python3 scripts/validate-packs --root .
./scripts/codex-smoke
```

A non-zero exit blocks the commit. The validator enforces manifest grammar, model-table
shape, resolution order, version sync (plugin.json vs README), and the relative-link scan.

## Living-document rules

- **Verification logs are append-only** (`core/verification-log.md`,
  `providers/*/verification-log.md`). Never rewrite a prior entry — a later contradiction
  *dates* a behavior change. Supersede in place only for same-session uncommitted text;
  otherwise strike (`~~…~~`) with a dated correction or append a new entry.
- **Purity boundary**: provider *names* may appear in `core/`; model ids and invocation
  strings may NOT — they live in `providers/<id>/`. The validator's link scan and the
  purity adjudication (2026-07-23) are the precedent.
- **Pack facts changed ⇒ bump the plugin patch version** and keep `plugin.json`,
  `.codex-plugin/plugin.json`, and the README `**Version:**` line in sync.
- **On any CLI version bump**: read the pack's `Changelog` row FIRST (verify skill step
  2b), then re-verify with `sdd-dispatch-verify <id>`. Never assume permission or sandbox
  behavior survived a patch release — agy has flipped permission behavior on every one.
- `verified-version` in a pack manifest is stamped only by live end-to-end dispatch
  evidence, recorded in that pack's verification log.

## Layout contract

`skills/sdd/SKILL.md` resolves the plugin root as its grandparent directory — `core/`,
`providers/`, `contracts/` are load-bearing siblings of `skills/`. Anything that breaks
that physical layout (moving skills out alone, flattening the tree) breaks every install
route. Codex plugin installs cache the whole repo, so the layout survives; the symlink
route depends on it.

## Distribution surfaces to keep in sync

| Surface | Files |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Codex plugin | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` (plugin source stays `local ./` — a git-subdir self-reference fails) |
| Codex skills metadata | `skills/*/agents/openai.yaml` |
| Docs | `README.md` install sections, `codex/INSTALL.md` |

## Git flow for this repo

- Feature/architecture work: `feature/*` branch → merge to `main` on the owner's
  explicit instruction.
- Living-document rounds (verification entries, pack fact updates, doc fixes): commit
  directly to `main` and push, per the owner's standing direction — but only after the
  hard gate passes.
- Tag releases `v<plugin-version>` when the owner asks.

## Testing

```bash
uv run --with pytest pytest tests/ -q   # 31+ validator cases
```

Fixtures in `tests/fixtures/` (including the P13 reviewer-qualification diff) are
evidence artifacts — do not regenerate them casually.
