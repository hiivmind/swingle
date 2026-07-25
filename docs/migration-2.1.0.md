# Migration: 2.0.x → 2.1.0 (skill names prefixed)

The two remaining unprefixed skill names are renamed: `sdd` → **`swingle-sdd`** and
`delegate` → **`swingle-delegate`**, matching `swingle-verify`. This release renames only
the skill frontmatter names; it does **not** alter dispatch behaviour, state layout,
config paths, or the on-disk directory names.

## Why

opencode and Codex register skills under bare frontmatter names in a flat, name-deduped
namespace, so `sdd` and `delegate` were global names there: another installed skill using
either generic name would silently collide, with whichever loaded first winning. Prefixing
removes the collision (the alias previously tracked in the README). Claude Code namespaces
skills per plugin, so the rename is cosmetic on that harness.

## What changed

- Skill frontmatter names: `sdd` → `swingle-sdd`, `delegate` → `swingle-delegate`
  (`swingle-verify` was already prefixed).
- Slash invocations: `/sdd` → `/swingle-sdd`, `/delegate` → `/swingle-delegate`. The
  `swingle-sdd` description keeps `/sdd` as a trigger phrase, so the old spelling still
  routes on description-matching harnesses.
- Natural-language routing is unaffected: "delegate this to grok" and "run this plan with
  SDD" match on the descriptions, not the names.

## What did NOT change

- Directory names: `skills/sdd/`, `skills/delegate/` — the layout contract, symlink
  installs, and `skills.paths` entries are untouched.
- `.sdd-dispatch/` workspace state, ledgers, and `models/` overrides.
- Config paths: `<project>/.sdd-dispatch.json`,
  `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, `$SDD_DISPATCH_MODELS`.
- Pack manifests, contracts, model tables, and all dispatch behaviour.

## Migration steps

1. **Upgrade the install** (plugin routes pick up the new names automatically):
   - Claude Code: `/plugin marketplace update swingle-marketplace` (or reinstall).
   - Codex: `codex plugin marketplace upgrade swingle-marketplace`, then
     `codex plugin add swingle@swingle-marketplace`.
   - opencode Route A: rerun `scripts/opencode-skills-path --merge <config>` after the
     Claude Code upgrade. Symlink installs: `git pull` the checkout — symlinks point at
     directories, which did not move.
2. **Update local invocation references.** In CLAUDE.md / AGENTS.md / settings, replace
   `/sdd` with `/swingle-sdd` and `/delegate` with `/swingle-delegate` where they refer to
   these skills. Prose asks ("delegate X to codex") need no change.
3. **Verify**: list skills on your harness and confirm `swingle-sdd`, `swingle-delegate`,
   and `swingle-verify` all register once each, with no bare `sdd`/`delegate` residue from
   a cached 2.0.x install.
