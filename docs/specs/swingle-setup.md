# Design spec — `swingle-setup` skill

**Status:** revised after adversarial design review (GLM 5.2 via opencode, job 017,
verdict DONE_WITH_CONCERNS — all findings folded in) · **Target version:** 3.1.0
(additive) · **Depends on:** the 3.0.0 namespace rename (`.swingle`, `$SWINGLE_*`,
`swingle-models`).

## 1. Purpose

A user-invoked onboarding and health-check skill that owns the setup concerns currently
scattered across README prose, pack sections, harness adapters, and migration docs — with
no single owner and no first-run moment:

| Concern | Owner today |
| --- | --- |
| Seed the model tiering registry (user or project layer) | README paragraph + a once-per-session nudge in the dispatch skills |
| Create a config file (`config.json` / `.swingle.json`) | **none — no creation path, no template, schema documented only inline in skill prose** |
| CLI detection, auth readiness, version drift summary | re-derived inside each dispatch skill's Step-0, per session, never summarized to the user |
| Provider baselines (e.g. agy headless permission baseline) | pack prose, surfaced only when a dispatch STOPs on it |
| Driving-harness install steps (e.g. opencode `skills.paths` generation) | per-harness install docs |
| 2.x → 3.0 migration (legacy `.sdd-dispatch` paths) | a runbook the user must find and follow by hand |

`swingle-setup` makes one front door: inspect the environment, report its state, offer
each fix individually, and hand off what it must not do itself.

## 2. Boundary against the existing skills

- **`swingle-setup` checks the environment**: paths, config, registry layers, CLI
  presence/auth/versions, migration residue, harness install state.
- **`swingle-verify` probes provider behavior**: the P1–P13 dispatch suite. Setup NEVER
  dispatches a probe; where it finds version drift it *recommends* `swingle-verify <id>`.
- **`swingle-sdd` / `swingle-delegate` consume the environment**: their Step-0 remains
  self-sufficient (a dispatch must never require setup to have run). Setup changes
  nothing about their read-only stance toward user config; it is the one skill with a
  mandate to write config, because the user summoned it for exactly that.

**The setup↔verify criterion (review finding I3)**: a pack-declared setup precondition is
in setup's scope **iff it is a local-state inspection** — a file, environment-variable,
or process read requiring no model dispatch (e.g. agy's baseline check is
`grep 'permissions' ~/.gemini/antigravity-cli/settings.json` — local). Any precondition
whose confirmation requires dispatching a model is a Phase D hand-off to
`swingle-verify <id>`, exactly like version drift; §6.4's "apply as the pack specifies"
is conditioned on the same criterion. (Verified at spec time: no shipped pack's baseline
requires a dispatch; the criterion governs future packs.)

The dispatch skills' once-per-session no-override-layer nudge changes from naming the raw
script to naming this skill: "run `swingle-setup` to seed the machine-wide registry."

## 3. Invocation

Explicit user invocation only: `/swingle-setup`, or natural-language asks ("set up
swingle", "check my swingle install", "migrate my swingle config", "swingle doctor").
The skill never auto-runs on install, on session start, or as a side effect of a
dispatch skill. Frontmatter `name: swingle-setup` (flat-namespace safe). Idempotent:
safe to re-run at any time; on a healthy environment it is purely a status report — an
already-seeded registry layer or already-applied baseline is an OK line, never a
failure (see §6.1).

**Argument scoping (review finding M1)** — the argument is natural-language text, so the
rules are stated, not assumed: tokens are lower-cased and matched against installed
provider ids; an unknown token → run Phase A unscoped and surface "could not scope to
`<token>`" as a finding; multiple provider ids → inspect all named, sequentially;
the reserved keyword `migrate` jumps to §6.3 and always wins over a hypothetical
provider of the same name (provider ids are validator-constrained, so the clash cannot
ship).

## 4. Operating phases

Strictly ordered; Phase A is always read-only, and every write in Phase C is
individually consented.

### Phase A — Inspect (read-only, always runs in full unless scoped)

1. **Root + trust gate**: resolve `<root>` (grandparent rule), run
   `python3 <root>/scripts/validate-packs --root <root>`; a non-zero exit is reported as
   the first finding. Setup continues inspecting — unlike dispatch, whose trust gate is
   a hard stop — but Phase C offers no writes while the validator fails, and **the
   report must mark every provider row "validation failed — enumeration skipped" rather
   than rendering an empty table that reads as "no providers installed"** (review
   finding M4).
2. **Environment health via the script, not skill prose** (review finding I2): run
   `scripts/validate-packs --health` (new mode, §7) — one call that emits, per pack:
   installed (CLI on PATH), installed version vs `verified-version`, bounded readiness
   probe result (timeout-bounded; a hang is a finding), and the resolving registry
   layer per provider via the existing `resolve_models` walk. The skill executes no
   manifest argv itself — the script is the single implementation of env inspection,
   shared with the dispatch skills' Step-0.
3. **Config discovery**: walk `$SWINGLE_CONFIG` → `<project>/.swingle.json` →
   `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`. Report which layer (if any)
   wins, and validate the found file with the existing
   `validate-packs --check-config` (§7). **Malformed config is a finding with an
   offered fix, never a STOP** — setup is the tool the dispatch skills' STOP points to.
   Enumerated cases mirror the dispatch STOP list exactly (review finding M2):
   malformed/wrong-typed file, unknown provider id in `disable`/`default_provider`/
   `providers_by_lane`, disabled routing target, and **set-but-unreadable
   `$SWINGLE_CONFIG`** (finding wording matches the dispatch STOP; offered fix: unset
   or repair).
4. **Registry layer record** (review finding I4): from the `--health` output, record
   the **currently-resolving layer per provider** before any Phase C offer is
   composed — offers are computed against this record (§6.1).
5. **Legacy namespace residue**: presence of `<project>/.sdd-dispatch.json`,
   `<project>/.sdd-dispatch/`, `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, and set
   `$SDD_DISPATCH_CONFIG` / `$SDD_DISPATCH_MODELS` env vars. For a legacy project
   directory, classify its contents now: **pure-untracked vs contains-tracked-files**
   (`git ls-files .sdd-dispatch/` non-empty), and whether the new-name target already
   exists — §6.3 branches on both.
6. **Harness/provider baselines**: each installed provider's pack-declared,
   local-state-only (§2 criterion) setup preconditions, read from the pack at run
   time. The driving harness's own install state (e.g. opencode `skills.paths`
   pinning) per its harness adapter.
7. **Workspace ignore state**: whether `.swingle/` scratch is covered by
   `info/exclude`/`.gitignore` in the current repo (informational; the dispatch skills
   self-heal this).

### Phase B — Report

One summary table, then findings grouped as **OK / ACTION AVAILABLE / HAND-OFF**:

```
provider  cli     installed  verified  auth      registry-layer  baseline
codex     codex   0.144.3    0.144.3   ready     default         —
opencode  opencode 1.18.5    1.17.18   ready     user            —
agy       agy     1.1.6      1.1.5     ready     default         MISSING
grok      —       not on PATH
config: none found (dispatch uses built-in defaults)      legacy paths: ~/.config/sdd-dispatch/ EXISTS
```

Every ACTION AVAILABLE line names the exact change it would make; every HAND-OFF line
gives the exact command the user must run themselves.

### Phase C — Offer & apply (consent per item)

Each item is offered individually (harness question tool where available, plain
question otherwise — and a plain-question fallback must re-state the specific item in
the question so a "yes" can never be read as blanket consent); "yes to all" is
acceptable input for non-destructive items but **never covers a destructive option**
(§6.1 `--force`, any overwrite). §6 defines the write inventory. After applying, re-run
the relevant Phase A check and show the before → after line — a write is confirmed by
re-inspection, never by assumption.

### Phase D — Hand-offs (never performed by the skill)

- **Interactive auth**: hand the user the CLI's login command (from pack/credentials
  doc); never drive an OAuth flow.
- **Version drift**: recommend `swingle-verify <id>` per drifted provider.
- **Dispatch-requiring baselines** (§2 criterion): recommend `swingle-verify <id>`.
- **Shell profile / CI env-var edits** (legacy `$SDD_DISPATCH_*`, shadowing
  `$SWINGLE_MODELS`): print the exact replacement lines; edit profiles only on an
  explicit user request naming the file.
- **Project-tracked-file changes** (a `.gitignore` entry rename, a tracked legacy
  directory): present the exact `git mv`/diff sequence from `docs/migration-3.0.0.md`
  for the user's own commit — setup never commits and never edits project-tracked
  files.

## 5. What setup must never do

No model dispatches. No commits. **No writes to project-tracked files** (offer the
`git mv`/diff for the user's own commit instead) — consented writes *outside* the
project repo, such as a provider's persisted settings file in §6.4 or user-level config
in §6.2, are legitimate Phase C writes, not exceptions to this rule (review finding
M3). No uninvited writes of any kind — every filesystem change is individually
consented in Phase C. No auth flows. No provider-specific command strings hardcoded in
the skill — every CLI name, argv, and baseline procedure is read from pack
manifests/prose at run time (purity boundary: `skills/**` stays free of model ids and
invocation strings, enforced by the structural tests).

## 6. Write inventory (Phase C)

### 6.1 Registry seeding

Offers are computed against the Phase A layer record (review finding I4): **only offer
to seed a layer that would actually win the walk** for that provider. If `$SWINGLE_MODELS`
or a project layer already shadows the target layer, say so explicitly and route to the
Phase D env-var/profile hand-off instead of seeding a file that resolution will never
read. Re-inspection after a seed compares the recorded layer to the new
`swingle-models which` output; "seeded but still shadowed" is a contradiction to
surface, never a silent success.

- User layer: `scripts/swingle-models init --user` (all providers) or `init <id> --user`.
- Project layer: `scripts/swingle-models init <id> --project <repo>` (committable —
  remind the user it is theirs to commit).
- **Idempotency** (review finding M5): the script's "`<path>` exists — pass `--force`
  to overwrite" exit is reported as **already seeded — OK**, not as a failure.
  `--force` overwrites user customizations; it is offered only behind an explicit,
  item-specific confirmation and is never covered by "yes to all".

### 6.2 Config scaffolding
- Offer user layer (`~/.config/swingle/config.json`) or project layer
  (`<project>/.swingle.json`), scaffolded from the canonical template in
  `docs/config.md` (§7) with all keys present but neutral (empty `disable`, no
  `default_provider`, `require-verified-version: false`), then walk the user through
  the keys they asked about. A malformed existing file is shown verbatim alongside the
  schema; the fix is applied only after the user picks the corrected content.

### 6.3 Migration (legacy residue found)

Branch on the Phase A classification (review findings I5, I6):

- **Pure-untracked legacy paths, new-name target absent**: apply the
  `docs/migration-3.0.0.md` moves one consented `mv` at a time
  (`.sdd-dispatch` → `.swingle`, config-file rename,
  `~/.config/sdd-dispatch` → `~/.config/swingle`), each with a post-move
  `swingle-models which` confirmation.
- **New-name target already exists (partial prior migration)**: NEVER run a bare
  `mv <src> <existing-target>` — on Linux it nests the source *inside* the target
  (`.swingle/.sdd-dispatch/`), silently corrupting the layer walk. List the
  conflicting children, offer a per-item merge (move children that don't collide;
  ask per collision), and leave the emptied legacy dir's removal as its own consented
  step.
- **Legacy dir contains tracked files** (committed `models/` overrides under the old
  name): project-tracked content is a Phase D hand-off — print the exact `git mv`
  sequence from the migration runbook for the user's own history-preserving commit.
  Setup moves only the untracked remainder (if any) after the user's `git mv`.

Env vars are always Phase D hand-offs.

### 6.4 Provider/harness baselines
- Apply a pack-documented, local-state-only (§2 criterion) baseline exactly as the pack
  specifies it (e.g. agy's persisted permission settings — a consented write outside
  the project repo, per §5), quoting the pack section in the offer. Where the driving
  harness has a generator script (opencode `skills.paths`), offer to run it. A baseline
  whose confirmation would require a model dispatch is never applied here — Phase D.

## 7. Canonical artifacts and script changes

### `docs/config.md` (new)

Single source of truth for the config schema, extracted from (and then referenced by)
the dispatch skills' Step-0 prose:

- Keys: `disable` (list of provider ids), `default_provider` (id),
  `providers_by_lane` (lane → id map), `require-verified-version` (bool).
- Layer walk and whole-file-wins semantics; the STOP conditions as the dispatch skills
  enforce them; the neutral template JSON block the setup skill scaffolds from.
- Both SKILL.md files link here instead of re-deriving the schema; their inline STOP
  conditions remain (they are load-bearing at dispatch time) but the key-by-key
  explanation lives only in `docs/config.md`.

### `validate-packs --check-config` (existing — no new mode; review finding I1)

Config validation **already exists**: `validate-packs --check-config <file>` drives
`load_config`, which checks JSON parse, root type, wrong-typed values, unknown provider
ids, and disabled `default_provider`/lane targets. **Unknown keys are a stderr warning
and are dropped, by design** — the dispatch skills' STOP list does not include unknown
keys, and setup must not elevate them (a config the dispatch skills accept must never
fail setup). Setup consumes the existing mode as-is; the only change is documentation:
`docs/config.md` cites it as the validation entry point.

### `validate-packs --health` (new mode; review finding I2)

The env-inspection logic Phase A needs, as a script mode rather than skill prose —
detection (`command -v` per manifest), installed-vs-verified version, bounded readiness
probe, and resolving registry layer per provider, with **no route selection** (the
existing `--step0` injects a route-selection finding and exits 1 when no role is given,
so it cannot serve as a health check). Reuses the existing manifest parsing,
`resolve_models`, and probe plumbing; covered by unit tests alongside the existing
resolver tests. The dispatch skills MAY later adopt it, but their Step-0 contract is
unchanged by this spec.

## 8. Skill layout and distribution

```
skills/swingle-setup/
  SKILL.md              # name: swingle-setup
  agents/openai.yaml    # display metadata, implicit invocation OFF (explicit-only skill)
```

- README: new Skills-table row; the install section gains one line ("after installing,
  run `swingle-setup` for a guided environment check"). Registry-onboarding prose in
  Model tiering points at the skill first, raw script second.
- CLAUDE.md skills table: add the row (`swingle-setup` | `skills/swingle-setup/` |
  environment onboarding, config/registry scaffolding, migration, health report).
- Codex/opencode surfaces: covered automatically by the `./skills/` pointer and the
  flat-namespace-safe name; `codex/INSTALL.md` mentions the skill in Prerequisites.
- Structural tests: extend the skill-structure suite — frontmatter name, purity
  boundary (no model ids/invocation strings; auto-covered by the existing
  `skills/*/SKILL.md` globs), the no-superpowers rule (setup, like delegate, has no
  superpowers dependency), and a **precisely-scoped boundary guard** (review finding
  I7): no line of `skills/swingle-setup/SKILL.md` may match a P1–P13 probe label
  (`P\d+ —`) or contain a timeout-bounded probe invocation, while the bare hand-off
  recommendation `swingle-verify <id>` is explicitly permitted — a discriminator in the
  style of the existing `_cli_invocation` helper, not a naive substring ban on the
  skill's name.

## 9. Versioning and gate

- 3.1.0 (additive skill + `--health` script mode + docs; no behavior change to existing
  skills beyond the nudge rewording and config-schema link-out).
- Both plugin manifests + README version line in sync; full hard gate
  (`validate-packs && codex-smoke`) chained to the commit; test suite extended
  (`--health` unit tests + setup structural tests), all green before PR.
- The new `docs/config.md` and every link the skills add to it fall under the
  validator's existing link/anchor scan — broken anchors fail the hard gate (review
  finding M6).

## 10. Out of scope (backlog candidates)

- `--json` machine-readable report mode for CI health checks (natural extension of
  `--health`).
- Editing shell profiles / CI variable stores automatically.
- A guided auth walkthrough that shells into interactive logins.
- Harness-settings sync (e.g. auto-adding the per-target-CLI allow rule on agy).
- Dispatch skills adopting `--health` for their own Step-0 (kept out of 3.1.0 to hold
  the "no behavior change to existing skills" line).

Each is a real capability with a consumer story; file as issues on acceptance of this
spec rather than trimming them silently.

## Review record

Adversarially reviewed 2026-07-25 as delegate job 017: GLM 5.2 (opencode,
`--variant high`), design-reviewer contract, verdict **DONE_WITH_CONCERNS** — 0
Critical, 7 Important (I1–I7), 6 Minor (M1–M6), all folded into this revision; full
verdict at `.sdd-dispatch/delegate/017-review.md` (session workspace). Key
adjudications: I1 verified against `scripts/validate-packs` (`--check-config`
pre-exists; unknown-keys-as-warning preserved); I3's open assumption closed by
inspecting every shipped pack's baseline section (all local-state-only).
