# Migration: 2.x → 3.0.0 (config/state namespace renamed `sdd-dispatch` → `swingle`)

Every config and state path carrying the pre-rename `sdd-dispatch` name now uses
`swingle`. This is a hard cut: 3.0.0 reads only the new paths — there is no fallback to
the old ones. Dispatch behaviour, pack manifests, skill names, and on-disk skill
directory names are unchanged.

## Rename map

| 2.x | 3.0.0 |
| --- | --- |
| `<project>/.sdd-dispatch.json` | `<project>/.swingle.json` |
| `<project>/.sdd-dispatch/` (workspaces, `models/` overrides) | `<project>/.swingle/` |
| `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/` (config + user model registry) | `${XDG_CONFIG_HOME:-~/.config}/swingle/` |
| `$SDD_DISPATCH_CONFIG` | `$SWINGLE_CONFIG` |
| `$SDD_DISPATCH_MODELS` | `$SWINGLE_MODELS` |
| `scripts/sdd-models` | `scripts/swingle-models` |

## Per-project migration steps

Run in each repository that has used the plugin:

```bash
# 1. Project config file, if present
[ -f .sdd-dispatch.json ] && git mv .sdd-dispatch.json .swingle.json 2>/dev/null \
  || { [ -f .sdd-dispatch.json ] && mv .sdd-dispatch.json .swingle.json; }

# 2. Workspace + committable model overrides
[ -d .sdd-dispatch ] && mv .sdd-dispatch .swingle
```

Then re-point the ignore entry: if `.sdd-dispatch/` appears in the repo's tracked
`.gitignore`, change it to `.swingle/` (a committed change). If it was added to
`.git/info/exclude` by the skills, edit that file the same way — or simply let the next
dispatch re-add the new entry.

Note the split within `.swingle/`: `models/` is committable project config; the
`delegate/` and sdd workspaces are agent scratch and stay ignored. Never ignore
`.swingle/` wholesale if you commit model overrides.

## Per-machine migration steps

```bash
# 3. User config + machine-wide model registry
[ -d "${XDG_CONFIG_HOME:-$HOME/.config}/sdd-dispatch" ] && \
  mv "${XDG_CONFIG_HOME:-$HOME/.config}/sdd-dispatch" "${XDG_CONFIG_HOME:-$HOME/.config}/swingle"
```

4. In shell profiles, CI variables, and harness settings, rename `$SDD_DISPATCH_CONFIG` →
   `$SWINGLE_CONFIG` and `$SDD_DISPATCH_MODELS` → `$SWINGLE_MODELS`.
5. Update any local invocation references to `scripts/sdd-models` → `scripts/swingle-models`.

## Verify

```bash
scripts/swingle-models which            # every provider names the layer you expect
scripts/validate-packs --root <root>    # exit 0
```

A 2.x path left behind is silently invisible to 3.0.0 — the symptom is dispatches
resolving from pack defaults (or default config) when you expected an override. If
`swingle-models which` says `layer=default` for a provider you had customized, the
override file was not moved.

## What did NOT change

- Skill names (`swingle-sdd`, `swingle-delegate`, `swingle-verify`) and skill directory
  names (`skills/sdd/`, `skills/delegate/`).
- Pack manifests, contracts, model-table schema, and all dispatch behaviour.
- Ledger and workspace file formats — a moved `.swingle/delegate/` ledger resumes exactly
  where `.sdd-dispatch/delegate/` left off.

## First-time setup note (new in 3.0.0)

`scripts/swingle-models init --user` with no provider argument now seeds the machine-wide
model registry for every shipped provider in one command
(`~/.config/swingle/models/<id>.yaml`). Until a layer is seeded, dispatches resolve from
pack defaults — which is normal, not an error.
