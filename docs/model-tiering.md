# Model tiering & overrides

Tier the model to each task: a cheap model for a review or a trivial edit, the strongest for
a hard implementation — instead of paying premium rates on everything. That is the economic
idea, and it is why **`floor it`** (cheapest model clearing each bar) is the default. The
README carries the principle; the resolution mechanics live here.

The role → (tier, lane) mapping is owned by `core/roles.md`; the resolution algorithm the
skills run is in `skills/sdd/SKILL.md` (Step 0). This page is the user-facing view of how the
table is chosen and overridden.

## Model tables

Each pack ships its model priority table in `providers/<id>/models.yaml` — restricted YAML: a
flat header plus `tier/lane/priority/model/status[/pricing/rationale]` rows. `models.yaml` is
the table of record; `models.md` is the narrative. Statuses `verified` / `experimental` are
eligible; a `verified` stamp comes from live dispatch evidence only.

## Override precedence

At dispatch time the table is resolved per harness — **first file found wins whole-file** (no
merging):

1. `$SDD_DISPATCH_MODELS/<id>.yaml` — env override (a directory)
2. `<project>/.sdd-dispatch/models/<id>.yaml` — committable, team-shared
3. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` — this machine
4. the pack default

Seed an override with `scripts/sdd-models init <id> --project <repo>|--user`; inspect the
resolved layer and walk with `scripts/sdd-models which` (or
`scripts/validate-packs --resolve "<role>" <id> --project <repo>`).

## Override discipline

Override statuses are **your own assertion** — the `verified` stamps in pack defaults come
from live dispatch evidence, yours do not inherit that weight. A malformed override is a hard
error, never a silent fall-through. An override that omits a (tier, lane) slot resolves that
slot to "no eligible model — ask", which is the supported way to keep a harness from
auto-routing in one project.

## Economics, honestly

Tiering is a sound design principle; a **measured** token/cost delta on a real plan has not
been published yet. That number can't be asserted — it has to be measured — and it's tracked
in [#17](https://github.com/hiivmind/swingle/issues/17). What stands today is the handoff
itself (briefing, tiering, contract, evidence gate), which you get whether or not the savings
number is ever measured; the *savings* are the part awaiting a number.
