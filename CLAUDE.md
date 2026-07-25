# CLAUDE.md — swingle plugin

Harness-neutral plugin for SDD execution via external CLIs (codex / opencode / agy / grok / pi / claude).
This repository is simultaneously a **Claude Code plugin** (`.claude-plugin/`), a
**Codex plugin** (`.codex-plugin/` + `.agents/plugins/marketplace.json`), and a plain
skills tree — treat all three distribution surfaces as first-class.

## The one hard gate

Before every commit:

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit ...
```

A non-zero exit blocks the commit. The validator enforces manifest grammar, model-table
shape, resolution order, version sync (plugin.json vs README), and the relative-link scan.

**Chain the gate to the commit with `&&`, never `;`.** Written as separate statements the
gate becomes a neighbouring command whose failure you have to notice, and a failing gate
will commit and push anyway — observed 2026-07-23, when a purity violation reached `main`
because the shell used `;`. The gate is a precondition, not a preceding step.

## Living-document rules

- **Verification logs are append-only** (`core/verification-log.md`,
  `providers/*/verification-log.md`). Never rewrite a prior entry — a later contradiction
  *dates* a behavior change. Supersede in place only for same-session uncommitted text;
  otherwise strike (`~~…~~`) with a dated correction or append a new entry.
- **Purity boundary**: provider *names* may appear in `core/`; model ids and invocation
  strings may NOT — they live in `providers/<id>/`. The validator's link scan and the
  purity adjudication (2026-07-23) are the precedent. This binds `core/` prose *and*
  verification-log entries — write "the cheapest tier", not the slug. It binds
  `skills/**` too, enforced by `tests/test_delegate_skill.py`.
- **Provider capabilities are manifest fields, not skill special-cases.** When a CLI
  behaves differently in a way a skill must branch on, add a validated manifest field and
  have the skills read it — never hardcode a provider name in skill logic.
  `report-transport: report-file | captured-output` (added v1.4.0) is the worked example:
  agy cannot reliably write an agent-authored file to a workspace path, so it declares
  `captured-output` and both skills ask for no file. Adding a field means updating `REQ`
  or `OPTIONAL` plus `ENUMS` in `scripts/validate-packs`, declaring it in every shipped
  pack, and documenting it in the README's "Adding a provider" table.
- **Prefer structural fixes to prompt workarounds.** A prompt nudge can only lower the
  rate of a misbehaviour; routing around it can remove the failure mode. When you claim a
  fix works, say which kind it is — and do not call a mitigation "verified" off a single
  run when the failure is intermittent (2026-07-23 precedent: a 19-run trial returned
  p = 0.21 and could not support the claim a single green run had seemed to).
- **Pack facts changed ⇒ bump the plugin patch version** and keep `plugin.json`,
  `.codex-plugin/plugin.json`, and the README `**Version:**` line in sync.
- **On any CLI version bump** (a *maintenance* activity, NOT a per-dispatch gate): read
  the pack's `Changelog` row FIRST (verify skill step 2b), then re-verify with
  `swingle-verify <id>`. Never assume permission or sandbox behavior survived a patch
  release — agy has flipped permission behavior on every one. The `swingle-sdd`/`swingle-delegate` skills
  do not stop a user on drift: the version gate is advisory (warn + proceed), and a
  channel-class dispatch failure *while drift is in effect* is what surfaces a
  drift-triggered verification finding to recommend recording — the real-world trigger for
  a re-verify round.
- `verified-version` in a pack manifest is stamped only by live end-to-end dispatch
  evidence, recorded in that pack's verification log.

## Layout contract

`skills/sdd/SKILL.md` and `skills/delegate/SKILL.md` both resolve the plugin root as their
grandparent directory — `core/`, `providers/`, `contracts/` are load-bearing siblings of
`skills/`. Anything that breaks that physical layout (moving skills out alone, flattening
the tree) breaks every install route. Codex plugin installs cache the whole repo, so the
layout survives; the symlink route depends on it.

The three skills and what they own (frontmatter names are `swingle-`-prefixed since v2.1.0
because opencode/Codex register skills in a flat namespace; directory names are unchanged):

| Skill | Directory | Owns |
| --- | --- | --- |
| `swingle-sdd` | `skills/sdd/` | executing a written multi-task plan (task reviews, ledger, final review) |
| `swingle-delegate` | `skills/delegate/` | an explicitly requested one-off job or homogeneous batch — no plan, no superpowers dependency; workspace `.swingle/delegate/` |
| `swingle-verify` | `skills/swingle-verify/` | re-probing a CLI on version bumps and model releases |

`swingle-delegate` must stay free of any *operational* superpowers dependency: it never invokes a
superpowers skill, never runs `scripts/sdd-workspace`, and never touches `.superpowers/`.
The structural tests assert exactly one negative-disclaimer mention of each, so adding a
second mention of either string fails the suite.

## Distribution surfaces to keep in sync

| Surface | Files |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Codex plugin | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` (plugin source stays `local ./` — a git-subdir self-reference fails) |
| Codex skills metadata | `skills/*/agents/openai.yaml` |
| Docs | `README.md` install sections, `codex/INSTALL.md` |

## Git flow for this repo

**`main` is protected by a ruleset (2026-07-23). Everything lands via a PR — including
docs and living-document rounds.** This supersedes the previous standing direction to
commit doc fixes directly to `main`: that exception is withdrawn, because the ruleset now
enforces the PR path and a documented exception that only an admin bypass can satisfy is
worse than no exception at all.

- **`develop` is the integration branch (adopted 2026-07-24).** Any change:
  `feature/*` / `bugfix/*` / `docs/*` / `chore/*` branch → PR to `develop` → merge on the
  owner's instruction. Releases go `develop` → `release/*` → PR to `main` → tag.
- `main` remains protected and release-only: it blocks force-pushes, deletion, and
  non-linear history; conversation resolution is required. The ruleset currently protects
  `main` only — `develop` has no equivalent ruleset yet, so branch protection there is
  convention, not enforcement, until an admin adds one.
- The ruleset lists **repo admin as a bypass actor**, so a direct push to `main` will
  succeed for the owner. That is an emergency escape hatch, not the flow — using it
  silently reintroduces the conflict this section exists to remove.
- Tag releases `v<plugin-version>` when the owner asks.

**CI does not replace the hard gate.** `.github/workflows/ci.yml` runs `pytest` only, as
the `tests` required status check. `pytest` drives `scripts/validate-packs` via subprocess
(`tests/test_validate_packs.py`), so the validator IS enforced on GitHub — but
`./scripts/codex-smoke` is **not** in CI by deliberate choice: it asserts developer-workspace
layout, not repo correctness. Run the full gate locally, chained with `&&`, as above.

## Testing

```bash
uv run --with pytest pytest tests/ -q   # validator + skill-structure suites
```

Fixtures in `tests/fixtures/` (including the P13 reviewer-qualification diff) are
evidence artifacts — do not regenerate them casually.
