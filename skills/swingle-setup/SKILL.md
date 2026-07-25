---
name: swingle-setup
description: Environment onboarding and health check for swingle — inspect paths, configuration, registry layers, CLI presence and auth, migration residue, and harness setup, report status, and offer individual consented fixes. Explicit user invocation only.
---

# Swingle Setup — Environment Onboarding & Health Check

**Harness**: identify your controlling harness and read `<root>/skills/sdd/harnesses/<harness>.md` (claude-code, codex, grok, opencode, pi, agy) before setup — it maps skill-loading, native subagent dispatch, background jobs, completion observation, and asset-root resolution. `<root>` is this skill directory's grandparent (the directory containing `skills/`, `core/`, `providers/`, `contracts/`).

This skill has **no superpowers dependency**: it never invokes superpowers skills, never runs `scripts/sdd-workspace`, and never reads or writes `.superpowers/sdd/`.

## Boundary against existing skills

- **`swingle-setup` checks the environment**: paths, configuration files, registry layers, CLI presence, authentication readiness, versions, migration residue, and harness install state.
- **`swingle-verify` probes provider behavior**: the P1–P13 dispatch suite. Setup NEVER dispatches a probe; where it finds version drift or a baseline requiring dispatch confirmation, it recommends `swingle-verify <id>`.
- **`swingle-sdd` / `swingle-delegate` consume the environment**: their Step-0 remains self-sufficient; a dispatch must never require setup to have run. Setup changes nothing about their read-only stance toward user config; setup is the one skill with a mandate to write configuration because the user summoned it for exactly that.
- **Setup↔verify criterion**: a pack-declared setup precondition is in setup's scope **iff it is a local-state inspection** — a file, environment-variable, or process read requiring no model dispatch (for example, checking persisted permission settings in local config files). Any precondition whose confirmation requires dispatching a model is a Phase D hand-off to `swingle-verify <id>`, exactly like version drift. Phase C baseline application is conditioned on this same criterion.
- The dispatch skills' once-per-session no-override-layer nudge points to this skill: "run `swingle-setup` to seed the machine-wide registry."

## Invocation and argument scoping

Explicit user invocation only: `/swingle-setup`, or natural-language requests ("set up swingle", "check my swingle install", "migrate my swingle config", "swingle doctor"). The skill never auto-runs on install, on session start, or as a side effect of a dispatch skill.

Idempotent: safe to re-run at any time. On a healthy environment it is purely a status report — an already-seeded registry layer or already-applied baseline is reported as an OK line, never a failure.

**Argument scoping rules**:
- The argument is natural-language text.
- Lowercase input tokens and match against installed provider IDs.
- An unknown token: run Phase A unscoped and surface `"could not scope to '<token>'"` as a finding.
- Multiple provider IDs: inspect all named providers sequentially.
- Reserved keyword `migrate`: jumps directly to Phase C Migration (§6.3) and always wins over any provider ID of the same name.

## Operating phases

The setup skill operates in strictly ordered phases. Phase A is always read-only, and every write in Phase C is individually consented.

### Phase A — Inspect (read-only, always runs in full unless scoped)

1. **Root + trust gate**: resolve `<root>` (grandparent rule) and run `python3 <root>/scripts/validate-packs --root <root>`. A non-zero exit is reported as the first finding. Setup continues inspecting — unlike dispatch, whose trust gate is a hard stop — but Phase C offers no writes while the validator fails, and **the report must mark every provider row "validation failed — enumeration skipped" rather than rendering an empty table that reads as "no providers installed"**.
2. **Environment health via script**: run `python3 <root>/scripts/validate-packs --health` (passing `--provider <id>` if scoped, `--project <repo>` if project specified, and `--config <file>` if config path given). This single call emits, per pack: installed (CLI on PATH), installed version vs `verified-version`, bounded readiness probe result (timeout-bounded; a hang is a finding), and the resolving registry layer per provider via `resolve_models`. The skill executes no manifest argv itself — `validate-packs --health` is the single implementation of environment inspection.
3. **Config discovery & validation**: the resolving config layer comes directly from `--health` output (`config-layer=<env|project|user|none|env-unreadable>`). Validate found config files using `python3 <root>/scripts/validate-packs --check-config <file>`. See [docs/config.md](../../docs/config.md) for the configuration schema and validation rules. **Malformed config is a finding with an offered fix, never a STOP** — setup is the tool dispatch STOPs point to. Enumerated findings match the dispatch STOP list:
   - Malformed or wrong-typed JSON file.
   - Unknown provider ID in `disable`, `default_provider`, or `providers_by_lane`.
   - Disabled provider referenced as `default_provider` or `providers_by_lane` target.
   - **Set-but-unreadable `$SWINGLE_CONFIG`** (finding wording matches dispatch STOP; offered fix: unset or repair).
4. **Registry layer record**: from `--health` output, record the **currently-resolving layer per provider** before any Phase C offer is composed — offers are computed against this record.
5. **Legacy namespace residue**: check for presence of `<project>/.sdd-dispatch.json`, `<project>/.sdd-dispatch/`, `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, and set `$SDD_DISPATCH_CONFIG` / `$SDD_DISPATCH_MODELS` environment variables. For a legacy project directory, classify its contents: **pure-untracked vs contains-tracked-files** (`git ls-files .sdd-dispatch/` non-empty), and whether the new-name target (`.swingle/`) already exists.
6. **Harness/provider baselines**: inspect each installed provider's pack-declared, local-state-only setup preconditions read from pack manifests at run time. Inspect the driving harness's own install state (e.g. opencode `skills.paths` pinning) per its harness adapter.
7. **Workspace ignore state**: check whether `.swingle/` scratch directory is covered by `.git/info/exclude` or `.gitignore` in the current repository (informational; dispatch skills self-heal this).

### Phase B — Report

Output a single summary table followed by findings grouped into **OK**, **ACTION AVAILABLE**, and **HAND-OFF**:

```
provider  cli     installed  verified  auth      registry-layer  baseline
codex     codex   0.144.3    0.144.3   ready     default         —
opencode  opencode 1.18.5    1.17.18   ready     user            —
agy       agy     1.1.6      1.1.5     ready     default         MISSING
grok      none    not on PATH
config: none found (dispatch uses built-in defaults)      legacy paths: ~/.config/sdd-dispatch/ EXISTS
```

- Every **ACTION AVAILABLE** line names the exact change it would make.
- Every **HAND-OFF** line gives the exact command the user must run themselves.

### Phase C — Offer & apply (consent per item)

- Each item is offered individually using the harness question tool where available, or a plain question otherwise.
- A plain-question fallback must re-state the specific item in the question body so that a "yes" response can never be read as blanket consent.
- "yes to all" is acceptable input for non-destructive items, but **never covers a destructive option** (`--force` overwrites, any file deletion or overwrite).
- After applying a consented change, re-run the relevant Phase A check and display the before → after result. A write is confirmed by re-inspection, never assumed.

### Phase D — Hand-offs (never performed by the skill)

The skill never performs the following operations directly:

- **Interactive auth**: hand the user the CLI's login command (from pack/credentials doc); never drive an OAuth flow.
- **Version drift**: recommend `swingle-verify <id>` per drifted provider.
- **Dispatch-requiring baselines**: recommend `swingle-verify <id>` for any baseline requiring model dispatch confirmation.
- **Shell profile / CI env-var edits**: print exact replacement lines for legacy `$SDD_DISPATCH_*` or shadowing `$SWINGLE_MODELS` variables; edit profiles only on explicit user request naming the file.
- **Project-tracked-file changes**: present the exact `git mv`/diff sequence from [docs/migration-3.0.0.md](../../docs/migration-3.0.0.md) for the user's own commit — setup never commits and never edits project-tracked files.

## What setup must never do

- No model dispatches.
- No git commits.
- **No writes to project-tracked files** (offer the `git mv`/diff for the user's own commit instead). Consented writes *outside* the project repo, such as a provider's persisted settings file or user-level config (`~/.config/swingle/config.json`), are legitimate Phase C writes, not exceptions to this rule.
- No uninvited writes of any kind — every filesystem change is individually consented in Phase C.
- No interactive authentication flows.
- No provider-specific command strings hardcoded in the skill — every CLI name, argv, and baseline procedure is read from pack manifests and prose at run time. Purity boundary: `skills/**` stays free of model IDs and CLI invocation strings.

## Write inventory (Phase C)

### Registry seeding (§6.1)

Offers are computed against the Phase A layer record: **only offer to seed a layer that would actually win the walk** for that provider. If `$SWINGLE_MODELS` or a project layer already shadows the target layer, state so explicitly and route to the Phase D environment variable / profile hand-off instead of seeding a file that resolution will never read. Re-inspection after a seed compares the recorded layer to the new `swingle-models which` output; "seeded but still shadowed" is a contradiction to surface, never a silent success.

- **User layer**: `scripts/swingle-models init --user` (all providers) or `init <id> --user`.
- **Project layer**: `scripts/swingle-models init <id> --project <repo>` (committable — remind the user it is theirs to commit).
- **Idempotency**: the script's exit when a path exists ("pass `--force` to overwrite") is reported as **already seeded — OK**, not as a failure. Passing `--force` overwrites user customizations; it is offered only behind an explicit, item-specific confirmation and is never covered by "yes to all".

### Config scaffolding (§6.2)

- Offer user layer (`${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`) or project layer (`<project>/.swingle.json`), scaffolded from the canonical template in [docs/config.md](../../docs/config.md) with all keys present but neutral (empty `disable`, no `default_provider`, `require-verified-version: false`), then walk the user through keys they asked about.
- A malformed existing file is shown verbatim alongside the schema; the fix is applied only after the user picks the corrected content.

### Migration (§6.3)

Branch on the Phase A classification of legacy residue:

- **Pure-untracked legacy paths, new-name target absent**: apply the [docs/migration-3.0.0.md](../../docs/migration-3.0.0.md) moves one consented `mv` at a time (`.sdd-dispatch` → `.swingle`, config-file rename, `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch` → `${XDG_CONFIG_HOME:-~/.config}/swingle`), each with a post-move `swingle-models which` confirmation.
- **New-name target already exists (partial prior migration)**: NEVER run a bare `mv <src> <existing-target>` — on Linux it nests the source inside the target (`.swingle/.sdd-dispatch/`), silently corrupting the layer walk. List conflicting children, offer a per-item merge (move children that do not collide; ask per collision), and leave the emptied legacy directory's removal as its own consented step.
- **Legacy directory contains tracked files** (committed `models/` overrides under the old name): project-tracked content is a Phase D hand-off — print the exact `git mv` sequence from the migration runbook for the user's own history-preserving commit. Setup moves only the untracked remainder (if any) after the user's `git mv`.

Environment variable renames are always Phase D hand-offs.

### Provider and harness baselines (§6.4)

- Apply a pack-documented, local-state-only baseline exactly as the pack specifies it (e.g. persisted permission settings — a consented write outside the project repo), quoting the pack section in the offer.
- Where the driving harness has a generator script (such as opencode `skills.paths`), offer to run it.
- A baseline whose confirmation would require a model dispatch is never applied here — route to Phase D.
