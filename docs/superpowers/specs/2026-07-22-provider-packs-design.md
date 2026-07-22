# Provider-Pack Architecture — sdd-dispatch v2 design

Date: 2026-07-22 (rev 4, 2026-07-23 — after Sol reviews: docs/sol-plan-review.md, docs/sol-rereview.md, docs/sol-final-review.md)
Status: final — Sol round-3 minimal changes applied
Target version: 1.2.0

## Problem

Provider knowledge (dispatch incantations, gotchas, model inventories, verification
history) for codex / opencode / agy is interleaved across shared reference files, and the
whole plugin assumes Claude Code as the controlling harness. This blocks four goals:

1. **Extensibility** — adding a provider means editing every shared file.
2. **Machine-local relevance** — nothing skips providers absent from this machine.
3. **Shareability** — no self-contained unit another user can take safely.
4. **Harness portability** — the sdd skill must wrap superpowers:subagent-driven-development
   from BOTH Claude Code and Codex CLI as controller (superpowers itself ships a Codex
   platform adaptation).

## Decisions

| Fork | Decision |
| --- | --- |
| Unit of split | Provider packs inside this plugin (`providers/<name>/`); core stays shared. |
| Availability | Derived detection from a declarative manifest (no pack-authored shell) + layered config. |
| Policy table | Core defines roles→(tier, lane); each pack maps (tier, lane)→models with explicit priority. |
| Harness | Harness-neutral entry skill + thin per-harness adapters. Controller harness and external provider are separate session concepts. |
| Validation | A deterministic validator/resolver script + fixture packs is IN scope; real-CLI probes remain environment smoke tests, not universal release gates. |

## Layout

```
sdd-dispatch-plugin/
  core/
    roles.md                  # SDD role → (tier, lane) + judgment bar (provider- and harness-free)
    liveness.md               # invariants only: self-reaping wrapper, effort-scaled thresholds,
                              #   evidence rules, kill-is-checkpoint (stall-signal semantics abstract)
    safety-doctrine.md        # hard gate, controller commits, clean-tree/diff, trust rules
    playbook.md               # dispatch flavours & economics, E-rules — harness terms abstracted
    verification-protocol.md  # probe suite P1–P13
    verification-log.md       # cross-provider/cross-harness incidents + synthesis (new entries only)
  providers/
    codex/    pack.md  models.md  verification-log.md
    opencode/ pack.md  models.md  verification-log.md
    agy/      pack.md  models.md  verification-log.md
  contracts/                  # implementer + task-reviewer contracts (provider/harness-agnostic)
  skills/
    sdd/
      SKILL.md                # harness-NEUTRAL entry point
      harnesses/
        claude-code.md        # Claude Code adapter (the ONLY place ${CLAUDE_PLUGIN_ROOT} appears)
        codex.md              # Codex CLI adapter
    sdd-dispatch-verify/SKILL.md
  scripts/
    validate-packs            # deterministic manifest+models validator and resolver (python3 stdlib)
  tests/
    fixtures/                 # fixture packs + stub executables + defect fixture for P13
  archive/
    v1.1/                     # the five pre-split reference files, verbatim (history preserved)
  docs/
    migration-1.2.0.md        # checked-in migration manifest: every old heading → new home
  .claude-plugin/             # Claude packaging (plugin.json, marketplace.json)
  codex/INSTALL.md            # Codex packaging: install & discovery instructions
```

## Harness abstraction

`skills/sdd/SKILL.md` is the harness-neutral entry: process skeleton, Step-0 procedure,
dispatch overrides, flavour choice, controller rules — written without harness-specific
tool names. It begins with: "identify your harness; read `harnesses/<harness>.md` first."

Each adapter defines the mapping for exactly five concerns:

| Concern | claude-code.md | codex.md |
| --- | --- | --- |
| Load superpowers SDD skill | Skill tool (`superpowers:subagent-driven-development`) | native skill loading per superpowers' codex adaptation |
| Native subagent dispatch | Agent tool | `spawn_agent` |
| Task tracking | TodoWrite | `update_plan` |
| Background jobs & notifications | Bash `run_in_background` + task notifications | shell job + polling pattern |
| Asset root resolution | `${CLAUDE_PLUGIN_ROOT}` | repo-relative from the physical SKILL.md |

**Path rule:** everywhere outside `harnesses/claude-code.md`, asset references are
relative to the plugin tree root, resolved from the physical location of the selected
SKILL.md (`<root>/skills/sdd/SKILL.md` → `<root>/…`). `${CLAUDE_PLUGIN_ROOT}` never
appears in core/, providers/, contracts/, or the neutral SKILL.md.

**Lever rename:** "all Claude" becomes **`native-subagents`** (dispatch via the
controller harness's own subagent mechanism; superpowers stock behavior). "all Claude"
remains documented in the claude-code adapter as an alias.

**Packaging:** one canonical tree serves both harnesses. Claude Code installs via
`.claude-plugin/` marketplace as today. Codex installs by cloning the whole repository
(the skill is useless without core/ and providers/ siblings); `codex/INSTALL.md` gives
the CONCRETE discovery steps per superpowers' own codex adaptation
(`superpowers/skills/using-superpowers/references/codex-tools.md`): where to register the
skill so codex loads it, and how `<root>` is derived (three dirname steps up from the
physical `skills/sdd/SKILL.md`). A `scripts/codex-smoke` check (part of validate-packs
`--step0` or standalone) verifies from a fresh checkout: SKILL.md at the expected
relative path, `harnesses/codex.md` present, root derivation resolves core/ and
providers/, validator passes — runnable WITHOUT codex installed; full codex-driven
end-to-end remains backlog. Version lives in `.claude-plugin/plugin.json` and is
mirrored in the README header; a validator check keeps them in sync.

## The pack contract

A directory under `providers/` is a valid pack iff it contains `pack.md`, `models.md`,
`verification-log.md`, and `pack.md` starts with a **declarative** front-matter manifest
— data only, no executable shell strings:

```yaml
---
schema-version: 1
id: opencode                    # MUST equal the directory name; [a-z0-9-]+
cli: opencode                   # executable NAME only ([a-z0-9-]+); detection = PATH lookup of this name
verified-version: "1.17.18"     # version the pack's facts were verified against
version-argv: ["opencode", "--version"]
resume-argv: ["opencode", "run", "-s", "{session_id}"]   # {session_id} is the only placeholder
fork-flag: "--fork"             # optional
session-source: session-list    # enum: session-list | exec-output | conversation-id
session-list-argv: ["opencode", "session", "list"]       # required iff session-source: session-list
stall-signal: log-age           # enum: log-age | process+print-timeout
sandbox: none                   # enum: enforced | none
readiness-argv: ["opencode", "session", "list"]   # optional; default = version-argv
readiness-timeout-seconds: 30   # optional; default 30
---
```

**Front-matter grammar (not general YAML):** a restricted `key: value` grammar — keys
`[a-z-]+`; values are unquoted/double-quoted scalars or JSON arrays of strings on one
line. This is exactly what the stdlib validator parses; anything else is a validity error.

**Executable-identity rule:** for EVERY `*-argv` field, `argv[0]` MUST equal `cli`.
Remaining elements must be flags/subcommands/placeholders (no absolute paths, no shell
metacharacters `;|&<>$` — validator-enforced). Combined with the PATH-lookup detection
rule this means a pack can only ever cause the declared CLI binary to run.
**Trust gate:** Step 0 refuses to use any pack tree that does not pass
`scripts/validate-packs` (cheap, stdlib, runs in <1s).
**Trust policy (approval, not just validation):** the git-tracked state of the plugin
repo is the trust anchor — the user controls what lands in the repo, so packs that are
tracked and unmodified (`git status --porcelain providers/` clean for that dir) are
trusted. Any provider directory that is untracked, locally modified, or outside the
tracked tree requires EXPLICIT user approval at Step 0 before its manifest argv or prose
is followed. Independently of trust, `validate-packs` rejects `cli` values naming
interpreters/launchers (denylist: sh bash dash zsh ksh env python python3 perl ruby node
deno bun npx uv uvx xargs nice timeout sudo doas) — a pack must declare a real provider
CLI, and empty argv arrays are invalid.

- **Detection executes nothing pack-authored**: Step 0 does a PATH lookup of the
  validated `cli` name (`command -v -- "<cli>"` after the validator confirms the name
  matches `[a-z0-9-]+`). Argv fields are executed only after full schema validation
  (including the argv[0]==cli rule), only for providers that pass detection, with the
  closed placeholder set, under `readiness-timeout-seconds`.
- The body of `pack.md` is prose (version-stamped): canonical dispatch template, verified
  behavior, gotchas, auth notes, output conventions. The pack's template is the ONLY
  dispatch template for that CLI — the skill carries the abstract dispatch shape, not
  per-CLI incantations.

### `models.md`

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |

- **Tier** ∈ `cheapest | standard | most-capable` (from core/roles.md).
- **Lane** ∈ `implement | review | any`.
- **Status** closed enum: `verified | experimental | unavailable | superseded | rejected`.
  **Eligible for resolution: `verified`, `experimental` only.**
- Documentary content — rejected models, watch list, superseded history — lives in
  separate sections BELOW the resolvable table (rejected/watch rows there carry evidence
  links into the pack's verification-log; they are outside resolution by construction).
- Validity: within each (tier, lane) pair, priorities are unique positive integers and
  exactly one row has priority 1. Row order carries no meaning.

### Resolution algorithm (exact)

Input: role, provider, exclusions (a possibly-empty set of (provider, model) pairs from
this session's ledger). Steps:
1. role → (tier, lane) via core/roles.md (lane is `implement` for implementer roles,
   `review` for reviewer roles).
2. In the provider's resolvable table, filter to Status ∈ {verified, experimental} and
   drop excluded (provider, model) pairs.
3. **Candidate order** = rows matching (tier, lane) exactly, ascending priority, followed
   by rows matching (tier, `any`), ascending priority.
4. Resolve to the FIRST candidate. Fallback (below) means advancing to the next candidate
   in this same order — the order is the complete fallback sequence.
5. If no candidate exists → explicit resolution error, surfaced to the user. Never
   substitute across tiers automatically; never substitute across providers automatically
   (see Failure classes — cross-provider moves are always a user decision).

### Routing precedence (which provider)

**Step 0 of routing — before provider selection:** if the `native-subagents` lever (or a
per-task native directive) is in effect, external dispatch is bypassed entirely — the
harness's native subagent mechanism (per the adapter) handles the task and NO provider is
selected. `native-subagents` is a dispatch mode, not a provider, and is never an input to
resolution.

Otherwise, the provider for a dispatch is chosen by the first match:
1. Explicit per-task provider directive in the plan.
2. Session routing lever ("via agy", "delegate mechanical to opencode").
3. Config `providers_by_lane` (per-lane provider map), then config `default_provider`.
4. Built-in default: `codex` if active (structured-review contract, sandbox), else the
   only active provider **iff exactly one is active**.
5. Otherwise: stop with a route-selection question to the user.

Naming an INACTIVE provider at any step → surface to the user (reroute or abort); never
silently reroute.

### Failure classes & fallback state

- **Channel/capability failures** (auth failure, model-not-found, startup stall,
  repeated zero-output hang): automatic fallback IS allowed — advance to the next
  candidate in the resolution order (same provider; the order already encodes exact-lane
  then `any`). Maximum **3 total dispatch attempts** per (task, role); exhausting them, or
  any need to change PROVIDER, is a user question — cross-provider rerouting is never
  automatic, consistent with the routing rule.
- **Ledger record** (one line per attempt, in the SDD progress ledger):
  `model-attempt: task=<N> role=<role> provider=<id> model=<id> class=<channel|quality> outcome=<failed|ok>`
  Exclusion scope: a `channel`-failed (provider, model) pair is excluded session-wide
  (channel failures are provider/model-level, not task-level); `quality` failures create
  NO exclusion — they route to escalation. Post-compaction sessions rebuild exclusions
  from these ledger lines.
- **Quality failures** (implementer BLOCKED, reviewer rejects repeatedly, gate failures):
  NEVER any automatic fallback — escalate tier or adjudicate with the user, per the
  superpowers status-handling rules.

## Provider states & readiness

`command -v` proves installation, not usability. Step 0 models four states:
- **installed** — PATH lookup of `cli` succeeds.
- **compatible** — run `version-argv` (bounded by `readiness-timeout-seconds`); extract
  the first `[0-9]+(\.[0-9]+)+` match from its output; compatible iff it string-equals
  `verified-version`. Mismatch, command failure, or no parseable version → WARN (pack
  facts may be stale; point to `sdd-dispatch-verify <id>`). With config
  `require-verified-version: true`, a provider that is not compatible is removed from the
  ACTIVE set (hard block), and Step 0 says so.
- **ready** — run `readiness-argv` (default: `version-argv`) with the timeout; ready iff
  exit 0. Checked lazily, ONLY for the provider actually selected, before its first
  dispatch. Not-ready → channel-class failure (user question or documented fallback —
  never silent). A readiness probe proves the CLI answers; it does not guarantee model
  access — model-not-found at dispatch remains a channel failure.
- **active** — installed ∧ not disabled by config ∧ (compatible if required by config).

## Configuration (replaces providers.local.json)

Machine/project policy lives OUTSIDE the plugin tree (plugin caches are replaced on
upgrade). Search order, first found wins:
1. `$SDD_DISPATCH_CONFIG` (explicit path)
2. `<project>/.sdd-dispatch.json` (project policy, committable)
3. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/config.json` (user/machine policy)

Schema (all keys optional):
```json
{
  "disable": ["codex"],
  "default_provider": "opencode",
  "providers_by_lane": { "implement": "opencode", "review": "codex" },
  "require-verified-version": false,
  "note": "free text"
}
```
Types (closed): `disable` array of pack ids; `default_provider` pack id;
`providers_by_lane` object with keys ⊆ {implement, review} and pack-id values;
`require-verified-version` boolean; `note` string.
Rules: config can only disable/steer — never enables an undetected CLI. Fail closed
(specific, actionable error; never silently proceed with defaults) on: malformed JSON;
wrong types; unknown provider ids anywhere; `default_provider` or any
`providers_by_lane` value naming a disabled provider; `$SDD_DISPATCH_CONFIG` set but
missing/unreadable. Duplicates in `disable` are ignored. Unknown top-level keys → warn,
ignore. Empty active set after disables → error naming the disables.

## Core contents

Core files contain **invariants and abstract procedures only** — validated by the
provider-free check (no model ids, CLI names, or harness tool names in core/, excepting
`codex` where it names the provider-pack id in routing precedence):
- **roles.md** — role → (tier, lane) table + tiering rules.
- **liveness.md** — self-reaping wrapper (abstract `<cli dispatch>` slot), effort-scaled
  thresholds keyed off the manifest `stall-signal` enum, evidence-first rules, pid-only
  kills, kill-is-checkpoint. Resume mechanics live in packs (`resume-argv`).
- **safety-doctrine.md** — hard gate, controller commits, clean-tree/diff on
  `sandbox: none`, never-trust-self-report.
- **playbook.md** — flavours (inline / sub / ext / supervised) & economics with
  harness-neutral wording (native-subagents, "the harness's subagent mechanism").
- **verification-protocol.md** — P1–P12 + **P13 reviewer known-defect benchmark**: run the
  candidate against the checked-in, versioned defect fixture (`tests/fixtures/p13/`), a
  human-confirmed defect diff with expected findings; false-clean fails the candidate.
- **verification-log.md** — new cross-provider/harness entries from v1.2.0 forward.

## Validator (`scripts/validate-packs`)

python3 stdlib, no third-party deps. Checks (exit non-zero on any failure, one line per
finding):
1. Every `providers/*/` has the three files; manifest parses; schema-version known; all
   required fields present; enums valid; `id` == dirname; `cli` and `id` match `[a-z0-9-]+`;
   argv entries are arrays of strings; only known placeholders.
2. models.md tables parse; Tier/Lane/Status enums valid; per-(tier,lane) unique
   priorities and exactly one P1; documentary sections contain no eligible statuses.
3. Core purity: grep-class check that core/ contains no provider model ids, CLI
   invocations, or harness tool names (allow-list: the routing-precedence mention of
   `codex`).
4. Version sync: plugin.json version == README header version.
5. Markdown link check across ALL tracked .md files (core/, providers/, skills/,
   contracts/, docs/, references/ tombstones, codex/INSTALL.md, README) — `archive/` is
   excluded (frozen history, stale links by design).
5b. Purity check extends to `contracts/`: contracts are provider-agnostic — the check
   fails on provider names/CLI invocations there (the current implementer contract's
   codex-specific line is rewritten sandbox-generically during migration).
6. `--resolve <role> <provider> [--exclude provider:model ...]` mode: prints the
   resolution walk (tier, lane, ordered candidate list, chosen id).
7. `--step0 --root DIR [--config FILE] [--path-dir DIR ...] [--lever NAME]
   [--task-provider ID] [--role ROLE] [--exclude provider:model ...]` mode: runs the
   FULL Step-0 pipeline against a fixture root, in spec order — (a) native-subagents
   bypass check; (b) detection via PATH lookup restricted to the given `--path-dir`s
   (stub executables); (c) config load/validation (all fail-closed cases, search-order
   semantics via --config standing in for the first-found file); (d) compatibility (run
   the stub's version-argv, regex-extract, compare, apply require-verified-version);
   (e) active-set construction; (f) provider routing precedence (task-provider → lever →
   providers_by_lane[lane-of-role] → default_provider → codex-if-active →
   sole-active-iff-one → ask); (g) model resolution for --role with exclusions;
   (h) readiness probe of the chosen provider's stub. Prints each stage's outcome. This
   mode is what the routing/config/state fixtures exercise; `--resolve` alone only
   covers the resolution algorithm.

Test fixtures (`tests/fixtures/`): fixture packs + stub executables covering — zero /
one / multiple active providers (via `--step0 --path-dir`); exact-lane vs `any`;
duplicate priorities; missing P1; rejected-only candidates; exclusion-driven fallback
order; argv[0]≠cli manifests; shell-metacharacter argv; malformed config; wrong-typed
config; disabled default_provider and disabled providers_by_lane target; version
mismatch with and without require-verified-version; native-subagents bypass;
plus the P13 defect fixture. A fixture-driven run of `validate-packs` is the release
gate. Live-CLI probes (P1–P12 against real codex/opencode/agy) remain environment smoke
tests run where those CLIs exist — valuable, but never a portable release gate.

Both-harness checks at release: Claude Code — real install/load smoke on the release
machine (marketplace add + plugin install into a scratch profile, or reinstall in place;
skill invocation reaches Step 0 and the trust gate runs). Codex — `scripts/codex-smoke`
run from a FRESH `git clone` to a temp dir (real discovery-path and root-resolution
check, no codex binary required); full codex-driven end-to-end stays backlog. Live
provider-CLI probes are environment smoke only: absent CLIs are reported, never a
release blocker.

**Codex-as-controller, codex-as-provider:** no prohibition. The codex adapter notes one
verified-risk: nested `codex exec` inside a sandboxed codex session may be blocked by
sandbox policy; the adapter instructs a one-shot nested-exec probe at first codex-lane
dispatch under a codex controller, and on failure treats it as a channel-class failure
(user question). Routing (`codex-if-active`) is unchanged.

## Migration plan

1. **Migration manifest first**: write `docs/migration-1.2.0.md` mapping EVERY heading
   of the five reference files to exactly one **primary live destination** (archive
   copies always exist in addition and are not destinations; a heading may additionally
   list indexed **mirrors**, marked `(mirror)`, when content is deliberately duplicated
   — e.g. a release-history item mirrored into two packs' history sections). Primary
   ownership is what tombstones and links point to. The manifest is the checked-in
   source of truth — not commit messages.
2. **Archive, then split**: copy the five files verbatim to `archive/v1.1/` (history
   preserved unchanged, satisfying append-only). New per-provider logs start at v1.2.0
   with a header line linking to the archive; entries whose content is provider-specific
   are copied (not reworded) into the owning pack log with a `(from archive/v1.1)` tag;
   cross-provider synthesis stays core. Mixed entries (e.g. the codex round's cross-CLI
   synthesis paragraph) are split at paragraph level per the manifest.
3. **Tombstones** at the five old `references/` paths: exact per-file destination lists
   (clickable relative links), the archive path, and "removed at v1.3.0".
4. **Link rewrite + check**: every relative link in moved content is rewritten;
   `validate-packs` link check must pass.
5. Skills/adapters rewritten (harness-neutral + two adapters); README (install for both
   harnesses, new layout, "Adding a provider"); `.gitignore` unchanged (config now lives
   outside the tree); version → 1.2.0.

## Out of scope (backlog)

- Extracting packs into standalone marketplace plugins (layout preserves the option).
- Automated Codex-controller end-to-end test harness.
- Auto-generated cross-provider comparison grid (drift risk; revisit on demand).
- Additional harness adapters (pi, antigravity) — the adapter contract is the extension
  point; superpowers' own platform-adaptation files are the template.
