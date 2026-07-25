# Design spec — `swingle-setup` skill

**Status:** draft for adversarial review · **Target version:** 3.1.0 (additive) ·
**Depends on:** the 3.0.0 namespace rename (`.swingle`, `$SWINGLE_*`, `swingle-models`).

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

The dispatch skills' once-per-session no-override-layer nudge changes from naming the raw
script to naming this skill: "run `swingle-setup` to seed the machine-wide registry."

## 3. Invocation

Explicit user invocation only: `/swingle-setup`, or natural-language asks ("set up
swingle", "check my swingle install", "migrate my swingle config", "swingle doctor").
The skill never auto-runs on install, on session start, or as a side effect of a
dispatch skill. Frontmatter `name: swingle-setup` (flat-namespace safe). Idempotent:
safe to re-run at any time; on a healthy environment it is purely a status report.

An optional argument scopes the run: a provider id (`swingle-setup agy`) limits
inspection and offers to that provider; `migrate` jumps straight to §6.3.

## 4. Operating phases

Strictly ordered; Phase A is always read-only, and every write in Phase C is
individually consented.

### Phase A — Inspect (read-only, always runs in full unless scoped)

1. **Root + trust gate**: resolve `<root>` (grandparent rule), run
   `python3 <root>/scripts/validate-packs --root <root>`; a non-zero exit is reported as
   the first finding (setup continues inspecting — unlike dispatch, whose trust gate is
   a hard stop — but Phase C offers no writes while the validator fails).
2. **CLI detection**: per pack manifest, `command -v -- "<cli>"` (data-only manifests;
   never execute manifest strings as shell).
3. **Version drift**: `version-argv` output vs `verified-version` per installed CLI.
4. **Readiness**: each installed provider's bounded `readiness-argv` probe (these are
   local list/status commands from the manifest, not model dispatches). Timeout-bounded;
   a hang is a finding, not a stall.
5. **Config discovery**: walk `$SWINGLE_CONFIG` → `<project>/.swingle.json` →
   `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`. Report which layer (if any)
   wins, and validate the found file (§7). **Malformed config is a finding with an
   offered fix, never a STOP** — setup is the tool the dispatch skills' STOP points to.
6. **Registry discovery**: `scripts/swingle-models which` — the resolving layer per
   provider.
7. **Legacy namespace residue**: presence of `<project>/.sdd-dispatch.json`,
   `<project>/.sdd-dispatch/`, `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, and set
   `$SDD_DISPATCH_CONFIG` / `$SDD_DISPATCH_MODELS` env vars.
8. **Harness/provider baselines**: each installed provider's pack-declared setup
   preconditions (e.g. agy's headless permission baseline check), read from the pack at
   run time. The driving harness's own install state (e.g. opencode `skills.paths`
   pinning) per its harness adapter.
9. **Workspace ignore state**: whether `.swingle/` scratch is covered by
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
question otherwise); "yes to all" is acceptable input but never the default. §6 defines
the write inventory. After applying, re-run the relevant Phase A check and show the
before → after line — a write is confirmed by re-inspection, never by assumption.

### Phase D — Hand-offs (never performed by the skill)

- **Interactive auth**: hand the user the CLI's login command (from pack/credentials
  doc); never drive an OAuth flow.
- **Version drift**: recommend `swingle-verify <id>` per drifted provider.
- **Shell profile / CI env-var edits** (legacy `$SDD_DISPATCH_*`): print the exact
  replacement lines; edit profiles only on an explicit user request naming the file.
- **Tracked-file changes** (a `.gitignore` entry rename): present the diff for the
  user's own commit — setup never commits and never edits tracked files silently.

## 5. What setup must never do

No model dispatches. No commits. No tracked-file writes (offer diffs instead). No
uninvited writes of any kind — every filesystem change is individually consented in
Phase C. No auth flows. No provider-specific command strings hardcoded in the skill —
every CLI name, argv, and baseline procedure is read from pack manifests/prose at run
time (purity boundary: `skills/**` stays free of model ids and invocation strings,
enforced by the structural tests).

## 6. Write inventory (Phase C)

### 6.1 Registry seeding
- User layer: `scripts/swingle-models init --user` (all providers) or `init <id> --user`.
- Project layer: `scripts/swingle-models init <id> --project <repo>` (committable —
  remind the user it is theirs to commit).

### 6.2 Config scaffolding
- Offer user layer (`~/.config/swingle/config.json`) or project layer
  (`<project>/.swingle.json`), scaffolded from the canonical template in
  `docs/config.md` (§7) with all keys present but neutral (empty `disable`, no
  `default_provider`, `require-verified-version: false`), then walk the user through
  the keys they asked about. A malformed existing file is shown verbatim alongside the
  schema; the fix is applied only after the user picks the corrected content.

### 6.3 Migration (legacy residue found)
- Apply `docs/migration-3.0.0.md` moves for **untracked** paths only
  (`mv .sdd-dispatch .swingle`, config-file rename, `~/.config/sdd-dispatch` →
  `~/.config/swingle`), one consented `mv` at a time, with a post-move `swingle-models
  which` confirmation. Tracked `.gitignore` entries and env vars are Phase D hand-offs.

### 6.4 Provider/harness baselines
- Apply a pack-documented baseline exactly as the pack specifies it (e.g. agy's
  persisted permission settings), quoting the pack section in the offer. Where the
  driving harness has a generator script (opencode `skills.paths`), offer to run it.

## 7. New canonical artifact: `docs/config.md`

Single source of truth for the config schema, extracted from (and then referenced by)
the dispatch skills' Step-0 prose:

- Keys: `disable` (list of provider ids), `default_provider` (id),
  `providers_by_lane` (lane → id map), `require-verified-version` (bool).
- Layer walk and whole-file-wins semantics; the STOP conditions as the dispatch skills
  enforce them; the neutral template JSON block the setup skill scaffolds from.
- Both SKILL.md files link here instead of re-deriving the schema; their inline STOP
  conditions remain (they are load-bearing at dispatch time) but the key-by-key
  explanation lives only in `docs/config.md`.

### Supporting script change: `validate-packs --check-config <file>`

Config validation currently exists only as skill prose. Add a `--check-config` mode to
`scripts/validate-packs` (the single implementation of resolution/validation logic)
that validates a config file: JSON parse, unknown keys, wrong types, unknown provider
ids, disabled `default_provider`/lane targets. Setup uses it in Phase A step 5; the
dispatch skills MAY cite it in their STOP messages. Covered by unit tests alongside the
existing resolver tests.

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
  boundary (no model ids/invocation strings), the no-superpowers rule (setup, like
  delegate, has no superpowers dependency), and a negative assertion that setup's
  SKILL.md contains no `swingle-verify` probe instructions (boundary guard).

## 9. Versioning and gate

- 3.1.0 (additive skill + script mode + docs; no behavior change to existing skills
  beyond the nudge rewording and config-schema link-out).
- Both plugin manifests + README version line in sync; full hard gate
  (`validate-packs && codex-smoke`) chained to the commit; 66-test suite extended, all
  green before PR.

## 10. Out of scope (backlog candidates)

- `--json` machine-readable report mode for CI health checks.
- Editing shell profiles / CI variable stores automatically.
- A guided auth walkthrough that shells into interactive logins.
- Harness-settings sync (e.g. auto-adding the per-target-CLI allow rule on agy).

Each is a real capability with a consumer story; file as issues on acceptance of this
spec rather than trimming them silently.
