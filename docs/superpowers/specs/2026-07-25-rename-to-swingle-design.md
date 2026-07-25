# Design: rename `sdd-dispatch` → Swingle (v2.0.0)

**Date:** 2026-07-25
**Status:** approved (user, 2026-07-25)
**Source backlog:** `docs/rename-to-swingle.md` (decided 2026-07-23)
**Branch:** `feature/rename-to-swingle` off `develop` @ 993c620 (v1.9.2) → PR to `develop`
**Target version:** 2.0.0 (breaking — plugin identity changes)

## Decisions locked before this design

- **Scope this round:** Workstreams 1–5 as a single v2.0.0 PR. W6 (repo rename and
  outside-the-repo references) and W7 (visual identity) follow separately.
- **Q2 (repo fate):** the GitHub repo will be **renamed in place** later —
  `discreteds/sdd-dispatch-plugin` → `discreteds/swingle`, relying on GitHub's 301.
  Docs written in this PR name `discreteds/swingle` as the canonical URL. **The repo
  rename is therefore a release prerequisite: it must land before v2.0.0 is released to
  `main`** (merging this PR to `develop` is safe; until the rename, the new URL 404s —
  reviewer finding, 2026-07-25).
- **Q4 (sequencing):** resolved by events — the Grok work shipped as v1.6.0 and the repo
  is now at v1.9.2, so the rename lands as its own clean diff.
- **Seed branch:** `develop` @ 993c620, confirmed by the owner.
- **W3 amendment (owner, 2026-07-25):** instead of a pure no-op, W3 produces a
  **portable self-migration guide** for v1 consumer workspaces (see W3 below).

## Rule 0 — what renames and what does not

Rename only the compound product name: `sdd-dispatch`, `sdd_dispatch`, `SDD Dispatch`
→ `swingle` / `Swingle`. Bare `sdd` / `SDD` — the methodology, the `/sdd` skill, and the
`.sdd-dispatch/` state directory — stays unchanged everywhere. No blind sed: every hit
file (~40 outside `archive/` and the verification logs) is read and edited deliberately.

Vocabulary shipping with the rename: **harness** (unit of dispatch), **dispatch** (not
"route"), **local dispatch, no proxy, no key custody** (not "gateway"/"upstream").
`llm-router` / `llm-gateway` appear in package keywords only, never prose. Tagline:
**"share the load."**

## W1 — Identity and manifests

Files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
`.codex-plugin/plugin.json` (including the whole `interface` block),
`.agents/plugins/marketplace.json`.

- `name` → `swingle`; `version` → `2.0.0` (kept in sync across both plugin.json files
  and the README version line); `repository` / `websiteURL` → `discreteds/swingle`.
- Descriptions are **rewritten**, not find-replaced: the product is a local
  harness-to-harness dispatcher with model tiering and token thrift — not "SDD via
  external CLIs."
- Keywords gain `llm-router`, `llm-gateway` for search discovery.

## W2 — Skills

- `skills/sdd-dispatch-verify/` → `skills/swingle-verify/`: directory rename plus
  `SKILL.md` frontmatter `name`/`description` and `agents/openai.yaml`.
- `skills/sdd/` **keeps its name** (Q1 resolved): it executes a plan via
  SDD-the-methodology. Product-name references in its prose update; methodology prose
  is untouched.
- `skills/delegate/` keeps its name; prose checked for product-name references. Its
  structural constraints hold: no operational superpowers dependency, and exactly one
  negative-disclaimer mention of each guarded string (the structural tests enforce this).
- `skills/sdd/harnesses/` — all five files (`claude-code.md`, `codex.md`, `grok.md`,
  `opencode.md`, `pi.md`) checked for product-name references; the directory name stays
  as load-bearing vocabulary.

## W3 — Portable self-migration guide (amended)

`.sdd-dispatch/` run-state directories in consumer workspaces are **not renamed** and
need no migration. Instead of code changes, W3 delivers a **self-migration guide** that
can be brought to any v1 workspace — a repo whose tooling installed the plugin as
`sdd-dispatch` — so an agent (or human) there migrates the workspace in place. It is
written as an executable checklist addressed to the consuming workspace, not prose about
this repo:

1. Re-point the plugin source — **remove the v1 install first, then add** (the old and
   new plugins both export `sdd`/`delegate`, so coexistence duplicates skill
   registrations; the cache dir is keyed on the old marketplace name): uninstall the v1
   plugin, remove the stale `sdd-dispatch-marketplace` entry, add the marketplace from
   `discreteds/swingle`, install `swingle`.
2. Update local invocation references: `/sdd-dispatch-verify` → `/swingle-verify` in the
   workspace's CLAUDE.md / AGENTS.md / settings; `/sdd` and `/delegate` are unchanged.
3. Update any pinned repo URLs — inspect `git remote -v` first and rewrite only remotes
   whose URL is the old upstream; in a fork checkout `origin` is the user's fork and
   stays, with `upstream` updated instead. Never blanket-rewrite `origin`.
4. Verify: `.sdd-dispatch/` state (ledgers, contracts, logs) is untouched and remains
   valid; a live dispatch round confirms the new install resolves packs.

This guide is the core of `docs/migration-2.0.0.md` (W4), following the
`docs/migration-1.2.0.md` precedent for structure: what changed, what breaks, how to
re-install, explicit "no state-dir migration" statement.

## W4 — Docs and doctrine

- `README.md` — full rewrite, not a rename. Order: the local-dispatch differentiator up
  top (**a router is a hop; Swingle spawns processes locally** against credentials the
  user already holds — nothing enters the prompt path), harness vocabulary, "share the
  load" tagline, `**Version:** 2.0.0` line, install sections pointing at
  `discreteds/swingle`. **Branding decision (owner, 2026-07-25): the "Greedy Cup
  doctrine" and the milkshake epigraph are dropped entirely** — they predate the Swingle
  branding and do not align with it. All branding derives from the swingletree /
  draught-harness concept only.
- Repo `CLAUDE.md` — product name, paths, skill names (including the skill table row
  `sdd-dispatch-verify` → `swingle-verify`).
- `core/roles.md`, `core/playbook.md`, `core/safety-doctrine.md`, `core/liveness.md`,
  `core/verification-protocol.md` (post-backlog addition).
- `contracts/*.md` — all four contract files.
- `codex/INSTALL.md`.
- `providers/*/pack.md` — all six providers (agy, claude, codex, grok, opencode, pi).
- `docs/migration-2.0.0.md` — **new**; carries the W3 self-migration guide.

### Judgment calls (approved)

1. `docs/migration-1.2.0.md` and `docs/migration-1.8.0.md` are dated historical
   artefacts like `docs/sol-*.md` — **not rewritten**.
2. Verification logs (`core/verification-log.md`, six `providers/*/verification-log.md`)
   are append-only: each gets **one appended dated entry** noting the rename; no prior
   entry is edited.
3. `docs/rename-to-swingle.md` itself has its Status line flipped to
   "implemented in v2.0.0, pending release" in this PR and records the Q2/Q4
   resolutions and the W3 amendment; "shipped" waits for the release to `main`.

### Do NOT rewrite

`archive/v1.1/**`, `docs/sol-*.md`, prior verification-log entries, dated migration
docs, git history.

## W5 — Code, tests, CI

- `scripts/validate-packs` (version-sync check must accept the new name, and is
  **extended** to also sync `.codex-plugin/plugin.json` — previously it compared only
  `.claude-plugin/plugin.json` against the README, leaving Codex-manifest drift
  undetected), `scripts/codex-smoke`, `scripts/sdd-models` (post-backlog addition).
- `tests/test_delegate_skill.py`, `tests/test_validate_packs.py`.
- `tests/fixtures/**` — checked for hardcoded product-name strings; fixtures are
  evidence artefacts and are not regenerated, only touched if a test's string
  assertions require it.
- `.github/workflows/ci.yml`, `.github/ISSUE_TEMPLATE/verification-finding.md`,
  `.gitignore`.

## Out of scope for this PR

- W6: GitHub repo rename, `~/.claude/CLAUDE.md` "SDD Delegation & Model Tiering"
  section, the `agy-antigravity-dispatch` memory, local checkout path, marketplace
  entries in `.claude/settings.json` files.
- W7: visual identity (mark + hero illustration); `feature/hero-logo` is stale.
- A `swing` CLI binary; the harness capability model; any behaviour change.

## Verification before PR

1. Full hard gate, chained: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`.
2. `uv run --with pytest pytest tests/ -q` fully green.
3. Residual-name sweep over **tracked content** (`git grep` — a recursive filesystem
   grep cannot pass, since git-ignored agent workspaces carry old names): hits land
   **only** in the allowed set — `archive/**`, `docs/sol-*.md`, dated migration
   docs, dated `docs/superpowers/specs+plans/**` artefacts, verification-log historical
   entries, historical prose in `docs/rename-to-swingle.md` / this spec, and state/config
   paths that deliberately keep the old name (`.sdd-dispatch/`, `.sdd-dispatch.json`,
   `~/.config/sdd-dispatch/`, `$SDD_DISPATCH_MODELS` — renaming these is a behaviour
   change and out of scope).
4. Every commit on the branch passes the gate (`&&`-chained, never `;`).

## Execution

Standard Delivery Flow: this spec → user review → `superpowers:writing-plans` for the
implementation plan → adversarial review of the plan → execute via the `sdd` skill →
post-implementation review → PR to `develop`.
