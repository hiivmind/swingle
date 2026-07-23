# Codex installation

Codex discovers agent skills by scanning (official: learn.chatgpt.com/docs/build-skills,
verified 2026-07-23):

- `$CWD/.agents/skills`, parent folders' `.agents/skills`, and `$REPO_ROOT/.agents/skills` (repo-level)
- `$HOME/.agents/skills` (user-level)
- `/etc/codex/skills` (machine/admin level)

Symlinked skill folders are supported and followed, and there is no git-URL or registry
installer — so GitHub deployment is a clone plus symlinks.

## Install from GitHub (user-level)

The `sdd` skill requires its sibling directories `core/`, `providers/`, and `contracts/`;
copying only `SKILL.md` is unsupported. Clone the repository and symlink the skill
directories — the followed symlink preserves the physical sibling layout the skill uses to
resolve its root:

```bash
git clone https://github.com/discreteds/sdd-dispatch-plugin "$HOME/src/sdd-dispatch-plugin"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/src/sdd-dispatch-plugin/skills/sdd" "$HOME/.agents/skills/sdd"
ln -s "$HOME/src/sdd-dispatch-plugin/skills/sdd-dispatch-verify" "$HOME/.agents/skills/sdd-dispatch-verify"
```

If a target link already exists, inspect it first; replace it only when it is an obsolete
registration for this skill. Restart Codex; it should discover `sdd` and
`sdd-dispatch-verify`. Update with `git -C "$HOME/src/sdd-dispatch-plugin" pull`.

> Older drafts of these instructions referenced `${CODEX_HOME:-$HOME/.codex}/skills`; the
> officially documented scan locations are the `.agents/skills` paths above.

## Repo-level alternative

To scope the skills to one project instead of the user, create the symlinks under that
repository's `.agents/skills/` directory (same commands with the target path changed).

## Manifest

Each skill ships a Codex metadata manifest at `agents/openai.yaml` (display name,
description, implicit-invocation policy). No action is required; Codex reads it from the
skill folder.

## Prerequisites and verification

Whichever dispatch CLIs you use must be on PATH (`codex`, `opencode`, `agy`), each
authenticated once interactively; provider-specific setup (for example agy's headless
permission baseline) lives in `providers/<id>/pack.md`. On first use, read the Codex
harness adapter: `skills/sdd/harnesses/codex.md`.

From the clone, verify the repository layout and release gate:

```bash
cd "$HOME/src/sdd-dispatch-plugin"
./scripts/codex-smoke
```
