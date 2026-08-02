# Warm-start validation receipt — design

**Status:** design (2026-08-02) · **Branch:** `discreteds/streamline-init` · **Target:** `develop`

## Problem

The first dispatch of every session pays the full Step-0-lite battery in both
`swingle-delegate` and `swingle-sdd`. Measured on this checkout:

| Step-0 call | cold | warm (OS file cache) |
| --- | --- | --- |
| `validate-packs --root` (repo lint) | 0.75s | 0.08s |
| `validate-packs --step0` (route one role) | **4.0s** | — |
| `validate-packs --health` (all six) | 5.1s | — |

The repo lint is noise. **Essentially all of the ~4s is live CLI subprocess
spawns inside `--step0`:** a `version-argv` (`<cli> --version`) for *every active
provider* — of which only one is ever routed, so the rest are pure waste — plus one
`readiness-argv` for the routed provider. The cost recurs once per session because
Step-0 treats every input as session-volatile and re-probes it from scratch, even
though `swingle-setup` (via `--health`) already validated the identical environment
and recorded nothing durable.

## Key observation: four validation scopes on four clocks

Today's Step-0 conflates checks that change on very different clocks. Separating
them is the whole design.

| Layer | Invalidated by | Cheaply detectable without a subprocess? | Disposition |
| --- | --- | --- | --- |
| **Install** — repo lint, manifest/models validity, registry integrity | plugin upgrade; `providers/` edit | yes — plugin version + a content signature over `providers/` | **cache** |
| **CLI version / drift** | CLI upgrade | yes — the CLI binary's path + mtime + size (a version proxy that needs no `--version` spawn) | **cache** |
| **Config + model resolution** | edit to the resolved config / `models.yaml` | yes — resolved path + mtime | **cache** |
| **Auth / readiness** | token expiry, logout | **no** — nothing on disk changes | **do not cache — live-probe** |
| **Doctrine reads** — `roles.md`, `playbook.md`, `safety-doctrine.md`, `liveness.md`, routed registry body, log shards, contract copies | plugin content change | n/a — cheap local reads; caching them is the playbook's documented "staleness footgun" | **stays per-session, uncached** |

Consequence: every genuinely heavy check is either **deterministically
fingerprintable** (cache it, invalidate it exactly) or is the **single routed
provider's readiness probe** (~0.5s, unavoidable by design). Nothing needs a
time-based TTL — a TTL only ever made sense for the auth layer, and the auth
layer is precisely the one we refuse to cache.

### Why no auth TTL

`readiness-argv` is a real auth/session call for only two of six packs
(`grok models`, `opencode session list`); the other four fall back to
`version-argv`, so "readiness" there is a second local `--version` with no auth
character at all. Because the routed readiness probe is one cheap process and auth
liveness has no on-disk signal, the honest choice is to **never cache the readiness
verdict and always live-probe the single routed provider before its first
dispatch.** This preserves the fail-fast guarantee, sidesteps stale-token risk, and
keeps the receipt free of any time-based field.

## The receipt

A machine-generated **cache** — categorically distinct from `config.json` (user-curated)
and the `superpowers` availability records (environment facts). It is regenerable state,
so it lives under the XDG *cache* root, not the config root:

```
${XDG_CACHE_HOME:-~/.cache}/swingle/receipt.json
```

```jsonc
{
  "schema": 1,
  "root": "/abs/path/to/plugin-tree",         // fingerprint anchor
  "plugin_version": "3.5.0",                   // from .claude-plugin/plugin.json
  "install_sig": "<sha256 over providers/ manifests + models.yaml + core/ + contracts/>",
  "install_validated": "2026-08-02T..Z",       // the --root lint verdict this signature stands for
  "config": { "layer": "user", "path": ".../config.json", "mtime": 1730000000 },
  "providers": {                               // per-provider, independently fingerprinted + independently valid
    "codex": {
      "installed": true,
      "cli_path": "/usr/local/bin/codex",
      "cli_mtime": 1730000000, "cli_size": 88123456,   // version-drift proxy, no spawn
      "version": "0.146.0", "verified": "0.146.0", "drift": false,
      "models_layer": "default", "models_path": ".../models.yaml", "models_mtime": 1730000000,
      "validated": "2026-08-02T..Z"
    }
    // ... one entry per installed provider that has been validated
  }
}
```

The receipt is **per-provider incremental**: each provider entry is self-fingerprinted
and self-valid. The install layer is a single global verdict keyed by
`plugin_version + install_sig`. Writes are atomic (temp file + `rename`) so
concurrent sessions never observe a half-written receipt.

## Fingerprint & invalidation (deterministic, no TTL)

On the warm path the skill asks the script to compare, using pure filesystem stats
(no subprocess):

- `root` and `plugin_version` match → the shipped install is unchanged.
- `install_sig` recomputed over `providers/` + `core/` + `contracts/` matches → the
  `--root` lint verdict still holds; **skip the repo lint.** The signature walks the
  **working tree** (real directory contents), not `git ls-files`, so an untracked new
  provider dir or any modified/added file changes it → cold path → re-lint, which also
  re-surfaces the trust gate's untracked/modified-provider approval (the security check
  is preserved, never bypassed by a warm hit). In an installed copy these files are
  immutable within a plugin version, so `plugin_version` alone would suffice;
  `install_sig` makes the dev-checkout case correct for free.
- For the routed provider: `cli_path` still resolves to the same file and its
  `mtime`+`size` match → the recorded `version`/`drift` verdict still holds; **skip
  the `--version` spawn.** A CLI upgrade rewrites the binary → stat mismatch → re-probe
  just that provider.
- `config.path`+`mtime` and the routed provider's `models_path`+`mtime` match → the
  recorded config-validity and resolution still hold; **skip re-parsing/re-resolving.**

Any mismatch is a **cold miss** for the affected scope. The install layer is global;
a provider miss is scoped to that provider. There is no wall-clock expiry: the receipt
is trusted exactly as long as its fingerprint inputs are unchanged.

## Script surface (`scripts/validate-packs`)

The script keeps its role as the single implementation of environment inspection;
skills stay free of CLI-invocation strings (purity boundary, test-enforced). Two
additions, both preserving the existing typed outcome contract
(`STOP:`/`ASK:`/`CHANNEL:`/`warning:`) so the skills adjudicate identically:

1. **`--step0 … --write-receipt <path>`** — the cold path. Runs today's `--step0`
   pipeline unchanged and, on a clean route (exit 0), writes/merges the routed
   provider's entry plus the install layer into the receipt as a side effect. No
   redundant second validation.

2. **`--check-receipt <path> --role <r> --project <repo> [--config <f>] [--task-provider <id> | --lever native-subagents]`**
   — the warm path. Loads the receipt, recomputes the fingerprint inputs above
   (filesystem only). On a full match it **replays routing + model resolution from the
   cached data** (no probing), then runs the **routed provider's readiness probe only**,
   and emits the same `installed:`/`active:`/`provider:`/`model:`/`ready:` lines and
   typed outcomes as `--step0`. On any mismatch it emits `cold: <scope> <reason>` and
   exits non-zero-but-typed so the skill falls through to `--step0 --write-receipt`.

`swingle-setup` gets an authoritative full write: extend its existing `--health`
pass with `--write-receipt <path>` (or an `--emit-receipt <path>` sibling) that
populates **every installed provider** at once, so a later session routing any
provider starts warm. Setup already probes all six for its report, so the write is
free.

## Skill Step-0 changes (delegate + sdd, in lockstep)

Both skills carry the identical Step-0 skeleton; both change together (the CLAUDE.md
living-document rule). The revised session-gate flow:

1. Doctrine reads (`roles.md`, `playbook.md`, `safety-doctrine.md`, `liveness.md`,
   routed registry body, logs, contract copies) — **unchanged**, still once per
   session, still uncached.
2. **Warm-first:** run `validate-packs --check-receipt <path> …`.
   - `warm` (exit 0, `provider:`/`model:`/`ready:`): proceed on the cached route +
     the single fresh readiness verdict. The `--root` trust gate and the `--step0`
     probe battery are both skipped.
   - `cold: <scope> <reason>`: run today's trust gate (`--root`) as needed for the
     install scope, then `--step0 --write-receipt <path>`, adjudicate its typed
     outcome exactly as today, and self-heal the receipt on success.
   - receipt absent: treated as a whole-receipt cold miss.
3. Self-heal is silent cache maintenance (mirroring the existing silent
   `.git/info/exclude` self-heal); mention it once per session, like the current
   "run `swingle-setup` to seed the registry" nudge — recast as "environment cached
   for fast start; run `swingle-setup` to pre-warm all providers."

The Step-0 **outcome table** in both skills gains the `check-receipt` rows
(`warm` → proceed; `cold: …` → fall through to `--step0`), keeping the table
normative and the script its executable rendering.

## Setup changes (`swingle-setup`)

- **Phase A** already runs `--health`; it additionally computes the fingerprint
  inputs so it can report receipt freshness (present / stale-scope / absent) as an
  OK/ACTION line.
- **Phase C** offers one consented item: "cache the validated environment for fast
  delegation" → the authoritative `--write-receipt` covering all installed providers.
  Consistent with setup's consent-per-item doctrine; the receipt is a cache write
  under `~/.cache`, outside both the project repo and the config dir.

## Non-goals / explicit boundaries

- **No manifest field.** The receipt is runtime state, not a pack fact; `REQ`,
  `OPTIONAL`, `ENUMS` and the shipped packs are untouched.
- **No TTL / no wall-clock expiry.** Trust is fingerprint-exact.
- **Doctrine reads are never cached to disk.** They are cheap and safety-critical;
  caching them across sessions is the exact staleness footgun `playbook.md` warns
  against.
- **Readiness is never cached.** Always live-probed for the one routed provider.
- **Purity preserved.** All CLI spawning stays in `validate-packs`; `skills/**`
  gains no CLI-invocation string (enforced by `tests/test_delegate_skill.py`).

## Testing

- `tests/test_validate_packs.py`: `--write-receipt` produces a well-formed receipt;
  `--check-receipt` returns `warm` on an untouched fingerprint and `cold:` on each
  mutation class (plugin version bump, `install_sig` change, CLI binary
  mtime/size change, config mtime change, `models.yaml` mtime change, absent receipt);
  atomic write leaves no partial file; per-provider incremental merge.
- `tests/test_delegate_skill.py` / `tests/test_setup_skill.py`: the single-mention
  disclaimers and purity assertions still hold after the Step-0 edits.
- Hard gate unchanged: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`.

## Open implementation details (resolved during planning)

- Exact `install_sig` input set and hashing (stat-signature vs content sha) — pick the
  cheapest that is still exact for the dev-checkout case.
- Whether setup's authoritative write reuses `--health` internals or a dedicated
  `--emit-receipt`; either keeps the all-providers semantics.
- `--check-receipt` exit-code convention for `cold:` (typed non-zero vs exit 0 with a
  `cold:` line) — align with how the skills already branch on `--step0` output.
