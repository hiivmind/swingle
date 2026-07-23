# Codex installation

Two supported routes. The plugin route is canonical on Codex ≥0.117 (plugins became a
first-class primitive 2026-03); the symlink route works everywhere skills are scanned.
Official references, verified 2026-07-23: learn.chatgpt.com/docs/build-plugins and
learn.chatgpt.com/docs/build-skills.

## Route A — Plugin install (recommended)

This repository is a Codex plugin (`.codex-plugin/plugin.json`, skills at `./skills/`)
and hosts its own marketplace (`.agents/plugins/marketplace.json`). Add the marketplace,
then install from the plugin browser:

```bash
codex plugin marketplace add discreteds/sdd-dispatch-plugin
codex plugin add sdd-dispatch@sdd-dispatch-marketplace
```

(Verified end-to-end 2026-07-23 on codex 0.144.3: the plugin installs to
`~/.codex/plugins/cache/<marketplace>/sdd-dispatch/<version>/` with the full repository —
`core/`, `providers/`, `contracts/` ship beside `skills/`, so root resolution works
unchanged.) Alternatively install from the `/plugins` browser in a session. Start a new
session before using the bundled skills. Refresh later with:

```bash
codex plugin marketplace upgrade sdd-dispatch-marketplace
codex plugin add sdd-dispatch@sdd-dispatch-marketplace
```

The plugin bundles the whole repository, so the `sdd` skill's sibling directories
(`core/`, `providers/`, `contracts/`) ship with it and root resolution works unchanged.

## Route B — Manual skills symlink

Codex scans skills from `.agents/skills` (working dir, parents, repo root),
`$HOME/.agents/skills` (user), and `/etc/codex/skills` (admin), following symlinks.
The `sdd` skill requires its sibling directories; copying only `SKILL.md` is unsupported.
Clone and symlink — the followed symlink preserves the physical sibling layout:

```bash
git clone https://github.com/discreteds/sdd-dispatch-plugin "$HOME/src/sdd-dispatch-plugin"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/src/sdd-dispatch-plugin/skills/sdd" "$HOME/.agents/skills/sdd"
ln -s "$HOME/src/sdd-dispatch-plugin/skills/sdd-dispatch-verify" "$HOME/.agents/skills/sdd-dispatch-verify"
```

If a target link already exists, inspect it first; replace it only when it is an obsolete
registration for this skill. Restart Codex. Update with
`git -C "$HOME/src/sdd-dispatch-plugin" pull`. For project scoping, symlink under a
repository's `.agents/skills/` instead.

> Older drafts of these instructions referenced `${CODEX_HOME:-$HOME/.codex}/skills`; the
> officially documented scan locations are the `.agents/skills` paths above.

## Manifests in this repository

| File | Purpose |
| --- | --- |
| `.codex-plugin/plugin.json` | Codex plugin manifest (identity, `skills` pointer, install-surface UI) |
| `.agents/plugins/marketplace.json` | Self-hosted Codex marketplace (git-subdir source at repo root) |
| `skills/*/agents/openai.yaml` | Per-skill metadata (display name, implicit-invocation policy) |
| `.claude-plugin/plugin.json` + `marketplace.json` | Claude Code plugin + marketplace equivalents |

## Prerequisites and verification

Whichever dispatch CLIs you use must be on PATH (`codex`, `opencode`, `agy`), each
authenticated once interactively; provider-specific setup (for example agy's headless
permission baseline) lives in `providers/<id>/pack.md`. On first use, read the Codex
harness adapter: `skills/sdd/harnesses/codex.md`.

From a clone, verify the repository layout and release gate:

```bash
./scripts/codex-smoke
```
