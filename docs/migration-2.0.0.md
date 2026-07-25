# Migration: 1.x → 2.0.0 (sdd-dispatch → Swingle)

The plugin `sdd-dispatch` is renamed **Swingle** at v2.0.0. This release renames and
repositions; it does **not** alter dispatch behaviour, state layout, or config paths.

## What changed

- Plugin name: `sdd-dispatch` → `swingle`; marketplace: `sdd-dispatch-marketplace` →
  `swingle-marketplace`.
- One skill invocation: `/sdd-dispatch-verify` → `/swingle-verify`. `/sdd` and
  `/delegate` are unchanged.
- Repository: `discreteds/sdd-dispatch-plugin` → `hiivmind/swingle` (renamed to `swingle`
  at v2.0.0, then moved to the `hiivmind` org; GitHub 301-redirects the old URLs).

## What did NOT change

- `.sdd-dispatch/` workspace state (delegate artifacts, ledgers, `models/` overrides) —
  valid as-is, no migration.
- Config paths: `<project>/.sdd-dispatch.json`,
  `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, `$SDD_DISPATCH_MODELS`.
- Pack manifests, contracts, model tables, and all dispatch behaviour.

## Self-migration guide for a v1 workspace

Bring this checklist to any repo or machine that installed the plugin as
`sdd-dispatch`; an agent (or human) there can execute it directly.

> **Timing:** run this guide only after the upstream repository rename and org move
> (`discreteds/sdd-dispatch-plugin` → `hiivmind/swingle`) have happened. The old URLs
> 301-redirect, so the commands below work regardless, but they name the canonical
> `hiivmind/swingle` location.

1. **Remove the v1 install FIRST, then add the v2 source.** The old and new plugins
   both export `sdd` and `delegate`, so letting them coexist creates duplicate skill
   registrations with ambiguous discovery — and the install cache is keyed on the old
   marketplace name, so upgrade-in-place does not work. Order matters: remove, then add.
   (Subcommand spellings below are from Claude Code 2.x / Codex 0.145; confirm against
   `--help` if your version differs — the remove-before-add ordering is the requirement.)
   - Claude Code: `/plugin uninstall sdd-dispatch@sdd-dispatch-marketplace`, then
     `/plugin marketplace remove sdd-dispatch-marketplace`, then
     `/plugin marketplace add hiivmind/swingle` and
     `/plugin install swingle@swingle-marketplace`.
   - Codex: `codex plugin remove sdd-dispatch@sdd-dispatch-marketplace`, then
     `codex plugin marketplace remove sdd-dispatch-marketplace`, then
     `codex plugin marketplace add hiivmind/swingle` and
     `codex plugin add swingle@swingle-marketplace`.
   - opencode Route A: rerun `scripts/opencode-skills-path --merge <config>` after the
     Claude Code remove/reinstall. Route B / pi / symlink installs: update the checkout
     (`git pull` — the remote 301-redirects) and re-point any symlink named
     `sdd-dispatch-verify` at `skills/swingle-verify`.
2. **Update local invocation references.** In the workspace's CLAUDE.md / AGENTS.md /
   settings, replace `/sdd-dispatch-verify` with `/swingle-verify`. Leave `/sdd`,
   `/delegate`, and every `.sdd-dispatch/` path exactly as they are.
3. **Update pinned URLs — inspect before rewriting.** Git remotes keep working via the
   301, but pins should move to `https://github.com/hiivmind/swingle`. Run
   `git remote -v` first and rewrite **only** a remote whose URL is the old upstream
   (`discreteds/sdd-dispatch-plugin`, with or without `.git`). In a fork checkout,
   `origin` is your fork — leave it alone and update (or add) the `upstream` remote
   instead. Never blanket-rewrite `origin`.
4. **Verify.** Confirm `.sdd-dispatch/` contents are untouched, then run one live
   dispatch round (or `swingle-verify <id>` for a pack you use) to confirm the new
   install resolves packs.
