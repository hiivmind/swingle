# Layered YAML model tables — design

**Date:** 2026-07-24
**Status:** approved design, pending implementation plan
**Target version:** 1.8.0

## Problem

Model prioritisation tables are markdown tables hardcoded inside each provider pack
(`providers/<id>/models.md`), parsed by `scripts/validate-packs` and read directly by the
`sdd` and `delegate` skills. Three problems:

1. The tables ship frozen inside the deployed plugin — a user cannot adjust tier/priority
   assignments without editing the plugin install.
2. Open-catalog providers (opencode, pi) have no fixed model list: the reachable namespace
   is whatever is authed on the machine (`~/.pi/agent/auth.json`, opencode auth), so no
   shipped default can be correct for every machine.
3. Markdown tables conflate two things: the machine-readable priority table and the
   documentary evidence layer (verification narrative, watch lists, pricing notes).

## Design summary

Move the table of record to **`models.yaml`**, ship one per provider pack as the default,
and resolve it through a **layered, whole-file-precedence** walk (env → project → user →
shipped default) so projects and machines can override it. `models.md` remains the
documentary living document.

## 1. Source shape — `models.yaml` per provider pack

Each `providers/<id>/` gains a `models.yaml`: the single machine-readable source of truth
for tier/lane/priority rows.

```yaml
# providers/pi/models.yaml
schema: 1
provider: pi
models:
  - tier: cheapest          # cheapest | standard | most-capable
    lane: any               # implement | review | any
    priority: 1             # integer >= 1
    model: opencode-go/deepseek-v4-flash
    status: verified        # verified | experimental | documentary
    pricing: "$0.14/$0.28"  # optional, free text
    rationale: "cheapest paid coder; transcription/explore"  # optional
```

- Row semantics are unchanged from the current md tables: eligible statuses are
  `verified`/`experimental`; `documentary` rows are recorded but never dispatched.
- `models.md` is **retained** as the documentary living document — verification
  narrative, watch lists, multi-provider-reach notes, strike-through corrections — and
  opens with a pointer naming `models.yaml` as the table of record. The md priority
  table itself is removed (no duplication).
- Living-document rules are unaffected: verification logs stay append-only; `verified`
  status in the **plugin-default** `models.yaml` is stamped only from live end-to-end
  dispatch evidence recorded in that pack's verification log.

## 2. Layered resolution, whole-file precedence

Per provider, the first file found is the **entire** table for that provider — no merging:

1. `$SDD_DISPATCH_MODELS/<id>.yaml` (env layer — a directory path; full parity with the
   behaviour config's `$SDD_DISPATCH_CONFIG` override. Set-but-unreadable directory, or a
   present-but-malformed file inside it, is a STOP)
2. `<project>/.sdd-dispatch/models/<id>.yaml` (project layer — committable, team-shared,
   per-project tiering policy)
3. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` (user-global layer —
   "what is authed on THIS machine"; the expected common override for open-catalog
   providers)
4. `providers/<id>/models.yaml` in the plugin (shipped default)

**Git-ignore reconciliation (required, same PR).** The delegate skill's workspace step
currently appends a blanket `.sdd-dispatch/` to `git info/exclude`, which would silently
git-ignore the project layer at creation and defeat its committable, team-shared purpose.
That step changes to ignore **`.sdd-dispatch/delegate/`** only (probe sentinel
`.sdd-dispatch/delegate/.probe` — unchanged in spirit, narrowed in path).
`.sdd-dispatch/models/` is committable content and must never be auto-ignored. The
migration doc tells existing repos to replace a blanket `.sdd-dispatch/` line in their
`info/exclude` with `.sdd-dispatch/delegate/` (a repo-local, untracked file — the plugin
cannot fix it remotely). The scheme rule going forward: `.sdd-dispatch/` mixes ephemeral
(`delegate/`) and durable-committable (`models/`) content, so ignores are always added at
the subdirectory level, never the root.

Rules:

- Local and user-global files use the identical schema and the same status-eligibility
  rule. Their statuses are the owner's own assertion — no verification-log requirement
  outside the plugin defaults. The recommended flow is copy-the-default (inheriting
  stamped statuses) and mark freshly added models `experimental` until seen working.
- **Partial overrides are rejected, by design.** An override file is subject to the same
  structural checks as the shipped default — including priority-1 present per
  `(tier, lane)` it declares. A minimal one-row file covering a single tier/lane slot is
  valid (its other slots simply resolve to nothing — see next rule), but a slot it does
  declare must be complete. Implementers must NOT relax the validator's checks for
  override layers; `sdd-models init`'s copy-the-default flow is the supported authoring
  path.
- **Empty or non-covering overrides resolve to "no eligible model → ask".** An override
  with `models: []`, or one that omits the requested `(tier, lane)` walk entirely, is
  well-formed: whole-file precedence still applies (no fall-through to lower layers), the
  walk yields no candidate, and the resolver reports *no eligible model — override at
  `<path>` does not cover `(tier, lane)`* before the existing ask-the-user path. This is
  the supported way to say "don't auto-route this provider here".
- A malformed, wrong-typed, or schema-violating file at any layer is a **STOP with the
  error**, never a silent fall-through to the next layer — consistent with the
  behaviour-config error rules in both skills.
- Precedence mirrors the existing behaviour config's shape exactly (env override →
  project → XDG → shipped default; first found wins). The behaviour config itself is
  untouched by this design: steer/disable stays there; model tables stay in model files.

## 3. Resolver as the single authority

`scripts/validate-packs --resolve "<role>" <provider>` is extended to perform the layered
lookup. Because the validator has no notion of "the project", `--resolve` gains an
explicit **`--project <dir>`** flag: the caller (skill or user) passes the repo root; no
cwd inference, no directory walk-up. Omitting `--project` skips the project layer (env,
user-global, and default layers still apply). `--step0` model resolution uses the same
walk with the same flag, so the two entry points cannot diverge.

Output format is pinned: the existing candidate-walk lines are preserved unchanged, and
one line is **prepended**:

```
layer: <env|project|user|default> path=<absolute path>
```

Tests assert this line exactly. Walk semantics are unchanged: exact-lane rows by
priority, then `(tier, any)` rows by priority — that order is the complete fallback
sequence.

Skill changes (`skills/sdd/SKILL.md` step 8, `skills/delegate/SKILL.md` model step):
"resolve within the routed provider" now means the layered `models.yaml` walk — script
preferred, manual layered file-existence walk as the fallback when the script is
unavailable. Failure-class rules (channel-failure candidate advance, max 3 attempts,
ledger lines, quality never auto-falls-back) are untouched; they walk the resolved table.

## 4. Seeding and open-catalog providers

New helper `scripts/sdd-models`:

- `sdd-models init <provider> --project|--user` — copies the currently-winning table into
  the chosen layer as an editing starting point (creates parent directories; refuses to
  overwrite an existing file without `--force`).
- `sdd-models which <provider>` — prints the winning layer and path for each provider (or
  one provider).
- `sdd-models` performs no resolution of its own: it calls the same resolver code path as
  `validate-packs --resolve` (single implementation of the layered walk — a second
  precedence implementation drifting is the failure mode to avoid).
- For open-catalog providers, a new **optional manifest field `list-models-argv`** (e.g.
  `["pi", "--list-models"]`) declares how to enumerate the live catalog — following the
  "provider capabilities are manifest fields, not skill special-cases" rule. `init`
  surfaces this command (does not execute it unprompted) so the user can align the seeded
  file with what is actually authed on the machine.

## 5. Validator, tests, surfaces

Validator (`scripts/validate-packs`):

- Parses `models.yaml` per pack with the same checks as today: tier/lane/status enums,
  duplicate `(tier, lane, priority)` detection, priority-1 row present per `(tier, lane)`.
- **Closed schema, enforced**: `schema` required and `== 1` (parallel to the manifest's
  `schema-version` check); `provider` required and `==` the pack directory name for
  plugin defaults, `==` the requested provider id for override layers; per-row fields are
  the closed set {tier, lane, priority, model, status, pricing?, rationale?} — any
  unknown key is an error (typo protection), matching the manifest's unknown-field
  discipline.
- **Eligible-row guard**: errors if a pack's `models.md` still contains a *table row*
  with an eligible status (anti-drift between the retained prose file and the table of
  record). Scope caveat, stated so nobody over-reads it: the guard catches table rows
  only, not prose mentions — narrative text calling a model "verified" after the YAML
  demotes it is caught by review discipline, not the validator.
- `list-models-argv` added to `OPTIONAL` with argv-shape validation (list of strings,
  `argv[0]` == the CLI binary, same rule as other argv fields).
- Purity boundary unchanged: model ids appear only under `providers/<id>/` (and in
  user-owned override layers, which are outside the repo).

Tests (`tests/`):

- YAML schema parsing (valid + malformed fixtures; unknown-key rejection).
- Layered precedence: env beats project beats user-global beats default; whole-file, no
  merge; `--project` flag routing; the pinned `layer: <layer> path=<abspath>` output line.
- Partial-override and empty-override (`models: []`) resolution semantics per §2.
- Malformed-override STOP behaviour.
- Round-trip check that all five shipped packs' `models.yaml` files validate.
- Existing md-table tests retired with the tables.

Distribution surfaces and doc references kept in sync — the full list, because several
load-bearing references point at the md tables today:

- README "Adding a provider" table (new field, new files), install sections,
  `codex/INSTALL.md`, both `plugin.json` files → **1.8.0**, README `**Version:**` line.
- `docs/migration-1.8.0.md`: the md→yaml table move, the override layers, the
  `info/exclude` narrowing for existing repos, and a note that cached plugin installs
  (Codex plugin cache) carry stale `models.md` tables until refreshed.
- `core/roles.md` (the "Tier→model mapping lives in each pack's models.md" footnote),
  `core/playbook.md`, and `core/verification-protocol.md` — every models.md reference
  updated to name `models.yaml` as the table of record (purity boundary still binds:
  no model ids in `core/`).
- `skills/sdd/SKILL.md` and `skills/delegate/SKILL.md` — model-resolution steps (layered
  walk) AND the delegate workspace git-ignore step (narrowed path, per §2).
- `skills/sdd-dispatch-verify/SKILL.md` — **same PR, not a follow-up**: verification
  outcomes stamp statuses into the plugin `models.yaml` (instead of the md table); the
  pack's `models.md` keeps the narrative entry. Left un-updated, the verify skill would
  keep stamping `verified` into prose while the table of record drifts — the exact
  failure the eligible-row guard exists to catch, produced by the mechanism that creates
  the stamps.

## 6. Migration

One PR to `develop`: all five packs (`codex`, `opencode`, `agy`, `grok`, `pi`) get their
md tables converted to `models.yaml`, md files trimmed to documentary content with the
pointer line, validator/tests/skills/docs updated together, hard gate
(`python3 scripts/validate-packs --root . && ./scripts/codex-smoke`) chained with `&&`
before commit.

## Out of scope (backlog)

- Merging/overlay semantics (per-tier-lane or row patches) — deliberately rejected in
  favour of whole-file precedence; revisit only if copy-drift proves painful in practice.
- Executing `list-models-argv` automatically during readiness preflight (noted in the pi
  pack as a possible future gate).
- Folding model tables into the behaviour config file.
