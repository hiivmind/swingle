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
and resolve it through a **three-layer, whole-file-precedence** walk so projects and
machines can override it. `models.md` remains the documentary living document.

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

## 2. Three-layer resolution, whole-file precedence

Per provider, the first file found is the **entire** table for that provider — no merging:

1. `<project>/.sdd-dispatch/models/<id>.yaml` (project layer — committable, team-shared,
   per-project tiering policy)
2. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` (user-global layer —
   "what is authed on THIS machine"; the expected common override for open-catalog
   providers)
3. `providers/<id>/models.yaml` in the plugin (shipped default)

Rules:

- Local and user-global files use the identical schema and the same status-eligibility
  rule. Their statuses are the owner's own assertion — no verification-log requirement
  outside the plugin defaults. The recommended flow is copy-the-default (inheriting
  stamped statuses) and mark freshly added models `experimental` until seen working.
- A malformed, wrong-typed, or schema-violating file at any layer is a **STOP with the
  error**, never a silent fall-through to the next layer — consistent with the
  behaviour-config error rules in both skills.
- Precedence mirrors the existing behaviour config (`$SDD_DISPATCH_CONFIG` →
  `<project>/.sdd-dispatch.json` → XDG). The behaviour config itself is untouched by this
  design: steer/disable stays there; model tables stay in model files.

## 3. Resolver as the single authority

`scripts/validate-packs --resolve "<role>" <provider>` is extended to perform the layered
lookup: it prints **which layer won** (absolute path) and the candidate walk. Walk
semantics are unchanged: exact-lane rows by priority, then `(tier, any)` rows by
priority — that order is the complete fallback sequence.

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
- For open-catalog providers, a new **optional manifest field `list-models-argv`** (e.g.
  `["pi", "--list-models"]`) declares how to enumerate the live catalog — following the
  "provider capabilities are manifest fields, not skill special-cases" rule. `init`
  surfaces this command (does not execute it unprompted) so the user can align the seeded
  file with what is actually authed on the machine.

## 5. Validator, tests, surfaces

Validator (`scripts/validate-packs`):

- Parses `models.yaml` per pack with the same checks as today: tier/lane/status enums,
  duplicate `(tier, lane, priority)` detection, priority-1 row present per `(tier, lane)`.
- Errors if a pack's `models.md` still contains a table row with an eligible status
  (anti-drift guard between the retained prose file and the table of record).
- `list-models-argv` added to `OPTIONAL` with argv-shape validation (list of strings,
  `argv[0]` == the CLI binary, same rule as other argv fields).
- Purity boundary unchanged: model ids appear only under `providers/<id>/` (and in
  user-owned override layers, which are outside the repo).

Tests (`tests/`):

- YAML schema parsing (valid + malformed fixtures).
- Layered precedence: project beats user-global beats default; whole-file, no merge.
- Malformed-override STOP behaviour.
- Round-trip check that all five shipped packs' `models.yaml` files validate.
- Existing md-table tests retired with the tables.

Distribution surfaces kept in sync: README "Adding a provider" table (new field, new
files), install sections, `codex/INSTALL.md`, both `plugin.json` files → **1.8.0**, README
`**Version:**` line, and `docs/migration-1.8.0.md` describing the md→yaml table move and
the override layers.

`sdd-dispatch-verify` changes: verification outcomes stamp statuses into the plugin
`models.yaml` (instead of the md table); the pack's `models.md` keeps the narrative entry.

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
