# Leaner delegate/sdd Step-0 — design (v2)

**Status:** design, reworked after review (2026-08-02) · **Branch:** `discreteds/streamline-init` · **Target:** `develop`

> **Revision note.** v1 proposed a broad "validation receipt" caching install, version,
> and config/resolution facts. A codex `gpt-5.6-sol` design review returned **Needs rework**
> (`.swingle/delegate/001-report.md`): a fingerprint cache can bypass the hard trust gate,
> miss routing-affecting environment changes, and report providers "ready" without testing
> auth. Independently, this very session demonstrated the *other* half of the cost — the
> ceremony and fragile root/adapter resolution a one-off dispatch must pay before it can
> run. v2 reframes the problem around **total Step-0 fixed overhead** and fixes the bulk of
> it *structurally, without any cache*; a cross-session cache survives only as an optional,
> evidence-gated second phase with honest semantics. Finding dispositions are in
> [Review history](#review-history).

## Problem — Step-0 fixed overhead has two sources

A first dispatch in `swingle-delegate` / `swingle-sdd` pays a fixed overhead that is
disproportionate to a small one-off job. It has two distinct sources.

### 1. Redundant live probing (latency)

Measured on this checkout:

| Step-0 call | cold | warm (OS cache) |
| --- | --- | --- |
| `validate-packs --root` (repo lint) | 0.75s | 0.08s |
| `validate-packs --step0` (route one role) | **4.0s** | — |
| `validate-packs --health` (all six) | 5.1s | — |

The repo lint is noise. **Essentially all of the ~4s is live CLI subprocess spawns inside
`--step0`:** a `version-argv` (`<cli> --version`) for *every active provider* — of which
only one is ever routed — plus one `readiness-argv` for the routed provider. Five of six
version probes are pure waste on a single-role dispatch.

### 2. Ceremony and fragile resolution (turns, not seconds)

Observed first-hand this session, dispatching a single design review:

- **Root/adapter resolution is fragile.** `<root>` is "the skill dir's grandparent," but the
  running skill loaded from an installed cache
  (`~/.claude/plugins/cache/.../swingle/3.4.0/`) while the work lived in a separate source
  checkout — two candidate roots with different contents. The adapter path guessed wrong
  twice (`controllers/<h>.md` vs `skills/sdd/harnesses/<h>.md`; a `claude-code.md` read and
  a `pi.md` read both 404'd) before landing on the real layout. Each wrong guess is a wasted
  turn, and none of it is the user's problem.
- **The mandatory pre-dispatch read-set is large.** "Never dispatch from memory" requires
  reading `roles.md`, `playbook.md`, `safety-doctrine.md`, `liveness.md`, the routed pack,
  the contract, and the harness adapter — 7–8 files — before the first dispatch, every
  session, even for a trivial job. The reads are individually cheap; the tax is their number
  and the turns spent locating them when resolution is ambiguous.

The latency source is fixable by doing less redundant work. The ceremony source is *not*
fixable by caching — a fresh session has no memory, and the "never dispatch from memory"
reads are a safety feature, not waste. It is fixable by making resolution **robust and
self-verifying** and by keeping the mandatory read-set **minimal and precisely located**.

## Design principle (the line the v1 review drew)

> **Run every cheap, security-relevant, or routing-relevant check live, every session.
> Cache only expensive probe results — and never cache authentication.**

Concretely, these stay **live and uncached** because caching them is either unsafe or
pointless (they cost milliseconds):

- the `--root` structural lint (validates manifests, model tables, plugin metadata, and
  repo-wide links — more than a `providers/` hash covers) and the `git status --porcelain
  providers/` untracked/modified-provider approval — the **hard trust gate**, never
  bypassable by a cache hit;
- **provider detection** (which CLIs are on PATH) and the full **routing decision** — a
  newly installed, uninstalled, or PATH-reordered provider changes routing while any single
  provider's fingerprint is unchanged, so routing must be recomputed from the live provider
  universe every time;
- **layered config + model resolution** — the winning layer changes when a
  higher-precedence override appears or `SWINGLE_MODELS`/`XDG_CONFIG_HOME` changes, none of
  which a stored path+mtime detects; recompute the precedence walk every time.

Only genuinely expensive work — spawning provider CLIs — is a candidate for caching, and
even then auth is excluded (below).

## Part A — Structural fix (no cache): probe only what the route needs

This removes the bulk of the latency with **zero staleness risk**.

1. **`--step0` version-probes only the routed provider**, not every active provider. The
   full active-set version loop runs **only** under config `require-verified-version`, which
   genuinely needs the incompatible set to filter it. In the common case (no
   `require-verified-version`) this drops five of six `--version` spawns.
2. **The routed provider still gets one live readiness probe** before its first dispatch —
   unavoidable and correct (auth is live evidence, never cached).
3. `--root` + the git-status approval run every session (they are ~0.1s).

Expected effect: the ~4s `--step0` collapses to the routed provider's one-or-two probes
(~0.5–1s), which for four of six packs is a single `--version` call because their
`readiness-argv` *is* `version-argv`. **Rebenchmark after this change** — it likely makes
Part C unnecessary.

**Control flow reorder.** Without `require-verified-version` this changes Step-0 from
loop-then-route to **route first, then probe only the routed provider's version +
readiness**; the full active-set loop still precedes routing *only* under
`require-verified-version`. State the reorder explicitly so an implementer does not
preserve the old full loop.

**Drift semantics narrow — say so.** Dropping the non-routed version probes means the
five non-routed `warning: incompatible:` lines no longer fire in `--step0`. This is
intended and arguably more correct: only the routed provider's drift bears on a
channel-failure finding. Redefine both skills' "`warning:` ⇒ note **drift is in effect**"
state to mean *the routed provider is in drift*. Non-routed drift remains reachable where
it matters — the `require-verified-version` full loop, and `swingle-setup`'s `--health`
sweep — so nothing is lost, only deferred to where it is relevant.

## Part B — Honest readiness/auth semantics

The v1 claim "always live-probe readiness ⇒ fail-fast auth" is false for the four packs
(`agy`, `claude`, `codex`, `pi`) whose `readiness-argv` falls back to `version-argv`:
`<cli> --version` succeeds while logged out, so a dead-auth provider would be reported
`ready:`. Fixes, in order of preference:

1. **Give every dispatchable provider a real, bounded, non-mutating authenticated
   `readiness-argv`** in its manifest (the field already exists; `grok models` and
   `opencode session list` are the pattern). This is a manifest-completeness task, gated on
   confirming each CLI exposes a cheap authenticated command — tracked as a follow-up, not
   assumed here.
2. **Until (1) lands, report honestly.** Detection rule: `fm.get("readiness-argv")`
   present ⇒ a real authenticated probe ⇒ `ready:` / `CHANNEL: provider not ready`;
   absent ⇒ readiness falls back to `version-argv` ⇒ report `available (auth unverified)`,
   not `ready`. This is a **new third readiness outcome** and the living-document rule
   binds it: both `skills/delegate/SKILL.md` and `skills/sdd/SKILL.md` outcome tables gain
   a row for `available (auth unverified)` with the exact action — "proceed; auth is
   unverified, so a channel failure on this dispatch is a provider-wide STOP, not a
   candidate glitch." A dead-auth dispatch is then caught by the existing first-dispatch
   Failure-handling, not masked by a false green; the controller gate never treats CLI
   availability as authentication.

## Part C — Optional cross-session probe cache (second phase, evidence-gated)

Only after Part A is measured. If a residual per-session probe cost still justifies it, a
**narrow** cache of expensive probe results — never gates, never routing, never auth:

- Location: `${XDG_CACHE_HOME:-~/.cache}/swingle/receipt.json` (regenerable cache, not
  config).
- Stores per-provider **version/drift advisory** results only, keyed by a **strong
  identity**: the resolved executable target (`realpath` of the CLI, following symlinks;
  resolution stops at the real binary and does not chase a shebang interpreter) + the
  `version-argv` output token + the pack's manifest `verified-version` (so a re-verify
  that bumps `verified-version` without changing the installed CLI still invalidates the
  cached drift verdict). Path+mtime+size is only a heuristic, not version identity
  (in-place replace and stable-wrapper cases defeat it). For the four providers where
  readiness == version-argv, parse the version from the already-live readiness call rather
  than caching a separate one. The untrusted-path ownership rule: the receipt file must be
  a regular file owned by the current user with non-group/other-writable permissions, else
  cold miss.
- **Provider-universe aware**: records the full installed set (including absent providers) so
  an install/uninstall/PATH change is a cold miss even when the routed provider is unchanged.
- **Never caches readiness/auth.**
- **Concurrency**: read–merge–write under a lock, or an optimistic generation/CAS re-read
  before rename; atomic rename alone allows lost updates between two sessions adding
  different entries. Tested with simultaneous writers, not just partial-file avoidance.
- **Untrusted/edge cases are cold misses, never fatal**: malformed JSON, unknown schema,
  wrong ownership/permissions, symlinked receipt path, or a failed self-heal write → treat
  as no cache and proceed with the live path (self-heal is best-effort maintenance, warned,
  never blocking a valid dispatch).
- **Warm-check interface is fully specified**: `--check-receipt` takes an explicit trusted
  `--root`; the algorithm is field-by-field — validate inputs, recompute routing and current
  precedence live, reuse only matching cached probe results, then perform the live routed
  readiness probe. Nothing about routing or the gate is taken from the cache.
- Ownership: setup writes it with consent (all installed providers); delegate/sdd self-heal
  the routed provider's entry after a live probe.
- **Marginal benefit under Part A is small — decide on measurement, not v1's framing.**
  After Part A only the routed provider is probed, and for the four fallback providers its
  version is parsed from the live readiness call; so the cache saves at most one
  `version-argv` spawn for a routed `grok`/`opencode` dispatch. Rebenchmark after Part A
  and state that number before building Part C.

## Friction responses (the ceremony source)

1. **Robust, self-verifying root/adapter resolution.** Resolve `<root>` as the
   **grandparent of the running skill's directory** — for `skills/delegate/SKILL.md` that
   is `dirname(dirname(dirname(SKILL.md)))` (three levels up from the file: file →
   `skills/delegate` → `skills` → `<root>`); a two-`dirname` formula lands on `skills/` and
   every sibling read fails. The harness adapter documents the package/cache cases; prefer a
   writable source tree over a cache path when both resolve. Before reading a harness adapter, **glob
   the adapter directory and verify the file exists** rather than guessing
   `controllers/` vs `skills/sdd/harnesses/`; a missing expected file is a stated finding,
   not a silent 404-and-retry. The skills already name the sibling layout — this makes the
   resolution check explicit instead of assumed.
2. **Minimal, precisely located mandatory read-set.** Keep the "never dispatch from memory"
   safety reads, but the skill enumerates the exact files and their resolved paths up front
   so they are read once, in one batch, from known locations — no discovery turns.
3. **SDD per-task rerun preserved.** `--check-receipt`/`--step0` reruns for **every task
   whose effective routing inputs differ** (role, provider directive, native directive,
   lane); "once per session" never authorizes reusing task 1's route for a task with
   different levers.
4. **Doctrine read ordering.** Global doctrine (`roles`, `playbook`, `safety-doctrine`,
   `liveness`) is read first and uncached; provider-specific reads (pack, registry/log,
   contract) come **after** route selection, since the routed provider is unknown until
   routing completes.

## Non-goals / boundaries

- **No caching of any gate, routing input, or auth verdict.** Only expensive probe results,
  and only in the optional Part C.
- **No new manifest field for the cache.** (Part B may *populate* the existing
  `readiness-argv` field for more providers — that is manifest content, not a new field.)
- **No caching of doctrine reads.** They are per-session context loads; the fix is
  robust location, not caching.
- **Purity preserved.** All CLI spawning stays in `validate-packs`; `skills/**` gains no
  CLI-invocation string (enforced by `tests/test_delegate_skill.py`).
- **Living-document lockstep.** Any Step-0 change updates both skills' outcome tables and the
  script together.

## Testing

- `tests/test_validate_packs.py`: `--step0` probes only the routed provider without
  `require-verified-version`, and the full set with it; the routed readiness probe still
  runs; honest `available (auth unverified)` vs `ready` labeling. Part C (if built):
  cold-miss on each mutation class (provider install/uninstall, PATH reorder, strong-identity
  change), concurrent-writer merge (no lost update), malformed/untrusted receipt → cold miss,
  self-heal failure → non-fatal.
- `tests/test_delegate_skill.py` / `tests/test_setup_skill.py`: single-mention disclaimers
  and purity assertions hold after Step-0 edits.
- Hard gate unchanged: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`.

## Review history

Codex `gpt-5.6-sol` (effort high), enforced read-only, design-reviewer contract. Verdict:
**Needs rework**. Disposition of findings:

- **Critical 1 — auth not tested by `--version` fallback** → Part B (honest labeling +
  real `readiness-argv` follow-up).
- **Critical 2 — routing depends on the whole provider universe, not the routed
  fingerprint** → design principle + Part A (routing always recomputed live) + Part C
  provider-universe awareness.
- **Critical 3 — `install_sig` cannot stand in for the hard gate** → dropped; `--root` +
  git-status approval run live every session (they are cheap).
- **Important 1 — layered resolution not captured by path+mtime** → recompute the
  precedence walk live every time (design principle).
- **Important 2 — path/mtime/size is not version identity** → Part C strong identity +
  parse version from the live readiness call.
- **Important 3 — concurrent lost updates** → Part C lock/CAS.
- **Important 4 — SDD per-task rerun** → Friction response 3.
- **Important 5 — warm interface underspecified** → Part C explicit `--root` + field-by-field
  algorithm.
- **Minor 1 — doctrine read ordering** → Friction response 4.
- **Minor 2 — malformed/edge-case receipt behavior** → Part C untrusted-is-cold-miss +
  non-fatal self-heal.
- **Assumptions to verify**: each fallback provider's authenticated readiness command
  (Part B follow-up); platform rename/timestamp/symlink assumptions (Part C); rebenchmark
  after Part A to confirm Part C is worth building.
