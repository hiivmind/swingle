# Provider-Pack Architecture — sdd-dispatch v2 design

Date: 2026-07-22
Status: approved-in-brainstorm, pending spec review
Target version: 1.2.0

## Problem

Provider knowledge (dispatch incantations, gotchas, model inventories, verification
history) for codex / opencode / agy is interleaved across shared reference files:
`dispatch-reference.md` holds all three CLIs, `model-catalog.md` mixes the cross-provider
policy grid with per-provider inventories, and `verification-log.md` is one chronological
stream. This blocks three goals:

1. **Extensibility** — adding a provider means editing every shared file.
2. **Machine-local relevance** — a machine without (say) agy still drags agy content
   through every skill run; nothing skips absent providers.
3. **Shareability** — there is no self-contained unit another user can take for "just
   the opencode knowledge".

## Decisions (brainstorm outcomes)

| Fork | Decision |
| --- | --- |
| Unit of split | **Provider packs inside this plugin** (`providers/<name>/`); core stays shared. Not plugin-per-provider. |
| Availability | **Runtime detection** (`command -v` per pack) **+ optional gitignored override** `providers.local.json`. |
| Policy table | **Core defines roles→tiers (abstract); each pack maps tiers→models.** Adding a provider touches zero core files. |

## Layout

```
sdd-dispatch-plugin/
  core/
    roles.md                  # SDD role → required tier + judgment bar (provider-free)
    liveness.md               # self-reaping wrapper, effort-scaled thresholds, resume doctrine
    safety-doctrine.md        # hard gate, controller commits, clean-tree/diff, read-only intent
    playbook.md               # dispatch flavours & economics, E-rules (from sdd-external-dispatch.md)
    verification-protocol.md  # probe suite P1–P12 + reviewer known-defect benchmark
    verification-log.md       # cross-provider incidents and synthesis entries ONLY
  providers/
    codex/    pack.md  models.md  verification-log.md
    opencode/ pack.md  models.md  verification-log.md
    agy/      pack.md  models.md  verification-log.md
  contracts/                  # implementer + task-reviewer contracts (unchanged, provider-agnostic)
  skills/
    sdd/                      # process skeleton + detection + pack resolution
    sdd-dispatch-verify/      # pack-scoped verification
  providers.local.json        # OPTIONAL, gitignored, machine-local
```

## The pack contract

A directory under `providers/` is a valid pack iff it contains:

### `pack.md`
Starts with a YAML front-matter block — the machine-readable interface:

```yaml
---
name: opencode
cli: opencode                     # binary name
detect: command -v opencode       # availability probe (exit 0 = present)
version-probe: opencode --version
resume: opencode run -s <session-id>   # continuation incantation (+ --fork variant note)
session-source: opencode session list  # where session ids come from
stall-signal: log-age             # log-age | process+print-timeout
sandbox: none                     # enforced | none
---
```

Body (prose, version-stamped): dispatch template, verified behavior, gotchas, auth notes,
output conventions. All content that today lives in that provider's section of
`dispatch-reference.md`.

### `models.md`
Tier→model table for this provider:

| Tier | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- |
| cheapest | 1 | … | verified/listed/rejected | … | … |
| standard | 1 | … | | | |
| most-capable | 1 | … | | | |

A tier MAY list alternates: multiple rows per tier, ordered by an explicit **Priority**
column (1 = default; ascending = fallback order when the default is unavailable,
rejected, or has just failed a task in this session). Row order in the file carries no
meaning — only Priority does. Rows with Status `rejected` are never resolved regardless
of priority (they remain in the table as documented evidence). Duplicate priorities
within a tier are a pack validity error. Example: opencode adaptation tier —
minimax-m3 priority 1, qwen3.7-plus priority 2.
Plus watch list and rejected-models section (with evidence links into the pack's log).
Namespaces, free-tier caveats, and per-model warnings (e.g. Luna long-context recall)
live here.

### `verification-log.md`
Append-only, this provider's probes, incidents, and model evaluations. Never rewritten.

**Extensibility rule:** a new provider = one new directory following this contract.
No core file changes. Sharing = copy the directory (or PR it upstream).

## Core contents

- **`roles.md`** — the abstract policy, provider-free:

  | SDD role | Tier | Mode |
  | --- | --- | --- |
  | Transcription implementer (complete code in brief) | cheapest | bg, write |
  | Adaptation implementer (prose/design/debug) | standard | bg, write |
  | Large-codebase / long-context implement | most-capable | bg, write |
  | Read-only explore | cheapest | bg, read-only* |
  | Research / synthesis | standard | bg, read-only* |
  | Per-task reviewer | standard | bg, read-only* |
  | Final whole-branch / design review | most-capable | bg, read-only* |

  Plus the tiering rules (turn count beats token price; scale reviewer to diff;
  read-only is intent except where a pack declares `sandbox: enforced`).
- **`liveness.md`** — self-reaping wrapper template, effort-scaled thresholds
  (300s low/med, 600–900s high/xhigh), the `stall-signal` dispatch on pack front-matter
  (agy-style buffering CLIs are watched by process + print-timeout, never log age),
  kill-is-checkpoint recovery, pid-only kills, evidence-first "is it running" rules.
- **`safety-doctrine.md`** — hard gate, controller commits, clean-tree-before/diff-after
  on `sandbox: none` packs, never-trust-self-report.
- **`playbook.md`** — dispatch flavours (inline / sub / ext / supervised) & economics,
  token-efficiency rules E1–E7, triviality floor, batching.
- **`verification-protocol.md`** — probe suite P1–P12, plus (new, promoted from smoke
  run 2) the **reviewer known-defect benchmark**: re-run a candidate reviewer on a diff
  where a trusted model already caught a defect; a false-clean fails the candidate.
- **`verification-log.md`** — cross-provider synthesis and incidents spanning providers
  (e.g. the harness wrapper-notification findings). Per-provider events go to pack logs.

## Detection & resolution flow (skill Step 0)

1. For each `providers/*/pack.md`, run its `detect:` command → **detected set**.
2. If `providers.local.json` exists, apply it:
   ```json
   { "disable": ["codex"], "prefer": "opencode", "note": "no ChatGPT seat on this box" }
   ```
   `disable` removes detected providers; `prefer` sets the default lane when the plan
   doesn't name one. → **active set**.
3. Load ONLY active packs' `pack.md` + `models.md`.
4. Role→model resolution: role → tier (core `roles.md`) → model (active pack's
   `models.md`), honoring the session's routing lever.
5. If the plan/lever names an **inactive** provider: surface to the user (named provider
   is absent/disabled here — reroute or abort?). Never silently reroute.

`providers.local.json` is machine policy, not capability: it can only disable/steer, never
enable an undetected CLI.

## Skill changes

- **`skills/sdd/SKILL.md`** — keeps the process skeleton (Step 0, dispatch overrides,
  flavour choice, controller rules) but references `core/*` and "the active packs";
  the per-CLI gotcha quick-list moves into pack.md bodies; Step 0 gains the
  detection/resolution steps above.
- **`skills/sdd-dispatch-verify/SKILL.md`** — becomes pack-scoped: verify one named
  provider (only its pack files + log change) or sweep the active set. Model evaluations
  use the known-defect reviewer benchmark + small implementer probe as standard.
  Version bump policy unchanged (patch per verification commit).

## Migration plan (content re-org, zero information loss)

1. Create `core/` and `providers/{codex,opencode,agy}/`; move every fact from the five
   current reference files into exactly one new home (mapping table kept in the
   migration commit message).
2. Split `verification-log.md`: cross-provider narratives stay in core; per-provider
   entries copied into pack logs (originals preserved — logs are append-only history).
3. Replace the five old files with one-line tombstones ("moved to core/… or
   providers/…") for one release, since installed skill caches may reference old paths.
4. Update both SKILL.md files, README, and `.gitignore` (+`providers.local.json`).
5. Version → **1.2.0**; reinstall/reload; memory file pointer updated.

## Testing

1. **Detection**: dry Step-0 run on this machine → all three packs active; with
   `providers.local.json` disabling codex → codex skipped and lever "via codex"
   surfaces a user question.
2. **Resolution**: one tiny ext-dispatch resolving role→tier→model purely through the
   new pack files (no old paths anywhere in the skill run).
3. **Pack validity**: front-matter of each pack parses; `detect`/`version-probe`
   commands run clean; every tier in `models.md` has exactly one priority-1 row and no
   duplicate priorities; no `rejected` row is resolvable.
4. **Tombstones**: grep the repo for references to the five old paths — only tombstones
   remain.

## Out of scope (backlog)

- Extracting packs into standalone marketplace plugins (layout deliberately preserves
  this as a future move).
- Auto-generated cross-provider comparison grid rendered from pack `models.md` files
  (rejected for now: generated artifacts drift; revisit if eyeballing lanes side-by-side
  is missed in practice).
- A `pack.md` JSON-schema validator script in the verify skill.
