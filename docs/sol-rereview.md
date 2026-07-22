## Re-review of the 12 findings

| # | Verdict | Evidence from rev 2 |
|---|---|---|
| 1 | **PARTIALLY RESOLVED** | The neutral entry skill and two adapters now map five harness concerns ([design:66](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:66)), but native model selection and the supervised-subagent model are still not mapped for Codex. |
| 2 | **PARTIALLY RESOLVED** | Physical-SKILL-relative paths and whole-tree Codex installation are specified ([design:82](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:82)), but the Codex discovery location remains circular (“where its skill discovery can find…”), and its release check is only “on paper.” |
| 3 | **PARTIALLY RESOLVED** | A deterministic provider precedence now exists ([design:157](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:157)), but `native-subagents` is placed in provider selection even though it selects no provider, and later fallback rules contradict the no-silent-reroute rule. |
| 4 | **PARTIALLY RESOLVED** | Shell-string detection was replaced with validated fields and argv arrays ([design:98](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:98)), but validation does not require argv element 0 to equal `cli`; a copied pack can still cause an arbitrary executable to run during version/readiness probing. |
| 5 | **RESOLVED** | Status eligibility, exact-lane-before-`any`, priority ordering, and explicit no-candidate failure are now unambiguous ([design:130](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:130)). |
| 6 | **PARTIALLY RESOLVED** | Failure classes, ledger persistence, reset scope, and a fallback cap are introduced ([design:170](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:170)), but the ledger key and executable fallback algorithm remain underspecified and cross-provider fallback contradicts the resolver. |
| 7 | **PARTIALLY RESOLVED** | `installed`, `compatible`, `ready`, and `active` are separated ([design:182](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:182)), but version comparison and bounded readiness probing lack operational definitions and manifest support. |
| 8 | **PARTIALLY RESOLVED** | Config now has an external search order, schema, and several fail-closed cases ([design:194](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:194)), but types/nested enums, unreadable explicit paths, and disabled `providers_by_lane` targets are not covered. |
| 9 | **RESOLVED** | Core is now expressly limited to invariants and abstract procedures, with provider-specific resume and command details assigned to packs ([design:217](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:217)). |
| 10 | **PARTIALLY RESOLVED** | The revision adds a heading-level migration manifest and verbatim archive before splitting ([design:265](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:265)), but its “exactly one destination” rule conflicts with archival copies, pack copies, and split multi-destination history. |
| 11 | **PARTIALLY RESOLVED** | Exact tombstones, a named removal version, link rewrites, and a link check are required ([design:278](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:278)), but the validator’s declared link scope excludes `references/`, `archive/`, `docs/`, `contracts/`, and `codex/INSTALL.md`. |
| 12 | **PARTIALLY RESOLVED** | A deterministic validator, resolver, fixture packs, and stub executables are now in scope ([design:235](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:235)), but its only declared runtime mode accepts an already-chosen provider and therefore cannot exercise most promised routing/config/state fixtures. |

No original finding remains wholly **UNRESOLVED**, but only findings 5 and 9 are fully closed.

## New issues introduced or exposed by rev 2

### Critical

1. **Fallback rules directly contradict routing and resolution rules.**  
   Resolution says never substitute providers automatically ([design:154](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:154)); failure handling says channel failures may automatically reroute providers ([design:172](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:172)). Reapplying the precedence ladder would also reselect an explicitly requested failed provider because no provider-exclusion input exists.

2. **The manifest remains an execution trust boundary.**  
   Schema validation only checks argv types and placeholders, not executable identity or argument safety. For example, `version-argv: ["sh", "-c", "..."]` passes the stated checks. Require at minimum `argv[0] == cli`, define a pack trust/approval policy, and constrain commands executed before trust is established.

3. **The validator cannot implement its advertised test matrix.**  
   `--resolve <role> <provider>` bypasses detection, active-set construction, routing precedence, configuration, version checks, and readiness. Yet fixtures promise tests for zero/multiple active providers, malformed config, disabled defaults, and version mismatch. The spec needs a Step-0/route mode with explicit fixture root, config, environment/PATH, exclusions, and state outputs.

### Important

4. **`native-subagents` is not a provider.**  
   It must branch out before provider selection into the harness-native path. As written, the “which provider” algorithm can select a value that cannot be passed to `--resolve <role> <provider>`.

5. **Fallback cannot be derived from the exact resolution algorithm.**  
   The resolver has no exclusion/attempt-state input. It does not define whether exhausted exact-lane candidates permit `any`, how “next priority” is selected, or whether two fallbacks means two or three total attempts.

6. **The ledger record is not sufficient to restore fallback state.**  
   `model-attempts: <role> <model> <failure-class>` lacks provider, task/dispatch identity, outcome, attempt order, and exclusion scope. The same model ID may occur in multiple providers, while “per role per session” could incorrectly poison later tasks using the same role.

7. **Readiness is not representable for every provider.**  
   `session-list-argv` exists only for `session-list`; `exec-output` and `conversation-id` providers have no `readiness-argv`, auth probe, timeout, expected exit status, or output predicate. A session-list command also does not necessarily prove model access or authentication.

8. **Compatibility is not a defined comparison.**  
   The spec does not say how to extract a version from CLI output, whether matching is exact or range-based, or what command failure/unparseable output means. It also calls a provider `active` even when `require-verified-version` should hard-block it.

9. **“YAML” conflicts with the stdlib-only validator unless a grammar is defined.**  
   Python’s standard library does not parse YAML. Either use JSON front matter or specify a deliberately restricted YAML subset and its parsing rules.

10. **Config validation is incomplete.**  
    Define types and closed keys for nested objects, valid `providers_by_lane` keys, duplicate handling, missing/unreadable `$SDD_DISPATCH_CONFIG`, and the result of a lane mapping that points to a disabled provider. “Unknown provider ids” is too broad to settle those cases.

11. **The migration manifest’s cardinality is contradictory.**  
    “Every heading … to exactly one destination” conflicts with the same paragraph’s “core log archive note + pack models history sections,” and with provider entries being both archived and copied. Distinguish archival preservation from one primary live owner, with optional indexed mirrors.

12. **Validation omits artifacts carrying migration and portability claims.**  
    Link checking must also cover tombstones in `references/`, `docs/migration-1.2.0.md`, `archive/`, contracts, and `codex/INSTALL.md`. Core purity likewise does not catch the existing provider-specific Codex statement in the nominally provider-agnostic implementer contract.

13. **The Codex harness check is too weak for the stated portability goal.**  
    “Repo checkout discovered” is not a concrete installation contract, and “resolution walk on paper” cannot establish skill discovery, Superpowers loading, contract copying, or controller dispatch. A minimal real Codex discovery/root-resolution smoke check is needed even if full end-to-end execution stays backlog.

## Overall verdict

**Not ready for plan rewrite.**

Rev 2 has the right architecture and substantially improves all 12 areas, but the fallback contradiction, executable-manifest trust gap, and validator/test-interface mismatch are design blockers. Resolve those first, tighten readiness/config/migration semantics, then rewrite the deliberately stale implementation plan from the corrected specification.