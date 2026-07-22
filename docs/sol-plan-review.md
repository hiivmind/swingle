1. **Critical — There is no controller-harness abstraction**

   **Sections:** Design “Skill changes” ([design:156](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:156)); Plan “Task 6: `skills/sdd/SKILL.md`” ([plan:175](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:175)).

   The design separates provider CLIs but still conflates the controlling harness with Claude Code. Concepts such as invoking a skill through the Skill tool, Agent-tool dispatch, “all Claude,” and “cheap Claude supervisor” have no defined Codex equivalent. In Codex, the adapted Superpowers workflow uses native skill loading and `spawn_agent`; “all Claude” should instead mean “use native harness subagents.”

   **Recommendation:** Make `skills/sdd/SKILL.md` the harness-neutral entry point and add thin adapters such as `skills/sdd/references/harnesses/claude-code.md` and `codex.md`. Define mappings for:

   - Loading `superpowers:subagent-driven-development`
   - Native subagent dispatch (`Agent` versus `spawn_agent`)
   - Task tracking (`TodoWrite` versus `update_plan`)
   - Background-job monitoring/result collection
   - Native model selection

   Rename the routing lever to `native-subagents`, retaining “all Claude” only as a Claude-specific alias. Keep `controller_harness` and external `provider` as separate session concepts.

2. **Critical — Path resolution and packaging remain Claude-only**

   **Sections:** Plan Task 6 Steps 1–2 ([plan:184](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:184)); Task 8 files/version bump ([plan:217](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:217)); Design “Layout” ([design:29](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:29)).

   `${CLAUDE_PLUGIN_ROOT}` is undefined under a Codex controller, so provider discovery and contract copying fail. The release task updates only `.claude-plugin/plugin.json`, and Task 5 updates only the existing Claude-oriented README layout—not Codex installation or discovery.

   **Recommendation:** Add an explicit packaging/path task:

   - Keep `skills/`, `core/`, `providers/`, and `contracts/` as one canonical tree.
   - Resolve assets relative to the physical selected `SKILL.md`; use `${CLAUDE_PLUGIN_ROOT}` only inside the Claude adapter. Do not make it the pack contract.
   - For native Codex plugin packaging, add `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, and `.codex/INSTALL.md`, with synchronized versions. Alternatively document a whole-repository Codex skill-discovery installation; copying only `SKILL.md` is insufficient because the shared assets would be missing.
   - Add Codex discovery and root-resolution smoke tests to Task 8.
   - Update README installation and invocation sections for both harnesses.

3. **Critical — Provider selection is undefined when multiple packs are active**

   **Sections:** Design “Detection & resolution flow” ([design:138](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:138)); Plan Task 6 Step 2 ([plan:185](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:185)).

   Detection produces an active set, but resolution suddenly refers to “the active pack.” If all three providers are active and neither the plan nor override supplies `prefer`, no rule selects a provider. Also, `prefer` names a provider but is described as setting a “default lane,” colliding with `implement|review|any`.

   **Recommendation:** Specify deterministic routing precedence, for example:

   1. Explicit task/provider directive
   2. Session routing lever
   3. Per-lane local policy
   4. Built-in per-lane default
   5. Otherwise stop with a route-selection error

   Rename `prefer` to `default_provider`, optionally with `providers_by_lane: {implement, review}`. Define that priority fallback is within one provider; crossing providers requires explicit policy or user approval.

4. **Critical — A copied pack can execute arbitrary shell during discovery**

   **Sections:** Design “The pack contract” and `detect` field ([design:51](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:51)); “Detection & resolution flow” ([design:140](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:140)); Plan Task 8 detection command ([plan:225](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:225)).

   The shareability promise says users can copy a provider directory, after which Step 0 executes its arbitrary `detect:` shell string. `version-probe` and `resume` are also free-form shell/prose values with inline comments and placeholders. This is both a trust-boundary problem and an unreliable machine interface.

   **Recommendation:** Make the manifest declarative:

   - Add `schema-version` and a safe provider ID matching the directory name.
   - Represent commands as argv arrays/templates with defined placeholders, not `bash -c` strings.
   - Derive ordinary detection from a validated executable name rather than executing pack-provided shell.
   - Validate identifiers, allowed enums, placeholders, and paths before any command runs.
   - If custom detection scripts are unavoidable, require explicit trust/opt-in and constrain them to a declared pack-local script.

5. **Important — `(tier, lane, priority)` resolution is contradictory and ambiguous**

   **Sections:** Design `models.md` contract ([design:75](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:75)); Design Testing item 3 ([design:186](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:186)); Plan Global Constraints ([plan:15](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:15)).

   An exact row such as `(standard, review, 1)` and wildcard `(standard, any, 1)` both match a review. The design does not say which wins. It alternately forbids duplicate priorities “within a tier,” requires one priority 1 per `(tier,lane)`, and tests for one priority 1 per tier. The proposed opencode pack necessarily has multiple priority-1 rows in a tier.

   Status handling is likewise unsafe: only `rejected` is excluded, so `listed`, `listed (superseded)`, or an unavailable model remains resolvable.

   **Recommendation:** Define the algorithm exactly:

   1. Filter to eligible statuses.
   2. Use exact-lane candidates if any exist.
   3. Only otherwise use `any`.
   4. Sort by unique positive priority within that selected candidate set.
   5. Fail explicitly if no eligible row exists.

   Define a closed status enum and eligibility policy, such as `verified`, `experimental`, `unavailable`, `superseded`, and `rejected`. Put documentary rejected/watch-list models outside the resolvable table or allow null tier/lane/priority explicitly.

6. **Important — Fallback state and failure semantics are unspecified**

   **Sections:** Design alternate-model semantics ([design:91](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:91)); Plan resolution procedure ([plan:192](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:192)).

   “Unavailable” and “has just failed a task in this session” are not defined. An auth error, startup stall, model-not-found error, agent `BLOCKED`, test failure, and low-quality implementation should not all trigger the same fallback. Nor is the attempted-model state persisted in the SDD ledger, so compaction can retry a failed default.

   **Recommendation:** Define failure classes and routing consequences. Persist attempts and exclusions in the session ledger. Limit automatic fallback to capability/channel failures; quality failures should escalate tier or request adjudication. Specify reset scope and maximum attempts.

7. **Important — Detection checks installation, not compatibility or readiness**

   **Sections:** Design “Detection & resolution flow” ([design:138](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:138)); Design Testing ([design:179](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:179)).

   `command -v` can mark a provider active despite an incompatible CLI version, missing authentication, exhausted balance, or unavailable selected model. Yet pack behavior is version-stamped and some documented providers fail silently when unauthenticated.

   **Recommendation:** Model separate states: `installed`, `compatible`, `ready`, and `active`. Add verified version/range fields and compare the installed version at Step 0. Run a bounded readiness/model preflight only for the selected provider. A version mismatch should warn or block according to policy and point to `sdd-dispatch-verify`.

8. **Important — `providers.local.json` is in the wrong lifecycle and lacks error policy**

   **Sections:** Design override flow ([design:140](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:140)); Plan Global Constraints and override test ([plan:17](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:17), [plan:226](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:226)).

   A gitignored file inside an installed plugin/cache can be read-only, replaced on upgrade, or duplicated across harness installations. The design also omits malformed JSON, unknown providers, a preferred-but-disabled provider, an empty active set, and project-specific routing.

   **Recommendation:** Define a stable config search order, such as explicit `SDD_DISPATCH_CONFIG`, project config, then user/XDG config. Validate against a schema and fail closed with actionable errors. Define precedence and merge rules, including empty-set and invalid-preference behavior.

9. **Important — The proposed `core/` is not actually provider- or harness-free**

   **Sections:** Design “Core contents” ([design:108](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:108)); Plan Task 1 Steps 2–4 ([plan:35](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:35)).

   The plan copies most of liveness and playbook content verbatim. That material contains provider-specific resume commands and Codex behavior, plus Claude-specific Agent-tool, supervisor-model, and `${CLAUDE_PLUGIN_ROOT}` instructions ([playbook:62](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/references/sdd-external-dispatch.md:62), [playbook:95](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/references/sdd-external-dispatch.md:95)). Keeping dispatch templates in the skill while declaring pack templates canonical also creates two sources of truth and means a new provider can still require a core edit.

   **Recommendation:** Keep only invariants and abstract procedures in `core/`. Move command syntax, resume/session acquisition, output handling, sandbox details, and provider-specific liveness into packs. Move Agent/Skill/path terminology into harness adapters. Remove duplicate CLI templates from the skill. Expand provider-free validation beyond `core/roles.md` to all core files.

10. **Important — The zero-information-loss migration is incomplete and misclassifies history**

   **Sections:** Design “Migration plan” ([design:167](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:167)); Plan Task 1 Step 6 and provider log tasks ([plan:39](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:39), [plan:81](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:81)).

   Concrete gaps include:

   - The model-catalog release history ([model catalog:82](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/references/model-catalog.md:82)) has no destination.
   - The dispatch-reference change history ([dispatch reference:251](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/references/dispatch-reference.md:251)) has no destination.
   - Moving verification-log lines 36–57 into the codex pack also moves the cross-provider synthesis at lines 51–55 into a provider log.
   - The opencode-only smoke-run incident at lines 78–128 is assigned wholesale to the core log, leaving pack warnings without pack-local evidence.

   **Recommendation:** Check in a migration manifest mapping every source heading/range to one destination; do not rely on commit messages. Define log ownership as either whole-entry primary ownership plus links, or preserve the original log unchanged under an archive and start indexed split logs from v1.2.0.

11. **Important — Moves will create broken links, and tombstones do not provide compatibility**

   **Sections:** Plan Task 1 Steps 4–5 ([plan:37](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:37)); Task 5 tombstones ([plan:149](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:149)).

   After moving `sdd-external-dispatch.md` into `core/`, its relative `dispatch-reference.md` and `model-catalog.md` links resolve to nonexistent core files. The moved verification protocol has the same problem. Existing greps look for `references/` strings and will not detect these bare relative links.

   The generic tombstone text also cannot guide a stale skill to the exact replacement, and “delete next release” has no scheduled task or compatibility criterion.

   **Recommendation:** Rewrite every link during migration and run a Markdown link checker. Give each tombstone exact clickable destinations, retain it through a named compatibility version, and add a checked-in migration document. Test old entry references against the new layout.

12. **Important — Validation cannot establish the claimed architecture**

   **Sections:** Design “Testing” and validator exclusion ([design:179](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:179), [design:192](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/specs/2026-07-22-provider-packs-design.md:192)); Plan Tasks 3, 7, and 8 ([plan:117](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:117), [plan:211](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:211), [plan:225](/home/nathanielramm/git/mountainash-io/mountainash/sdd-dispatch-plugin/docs/superpowers/plans/2026-07-23-provider-packs.md:225)).

   Grep and field counts do not parse YAML or model tables. The opencode awk check omits the Lane column and therefore will not match the specified schema. The override is “walked by hand,” and release validation assumes all three real CLIs are installed on one maintainer machine. There is no Codex-controller test.

   **Recommendation:** Bring a small deterministic validator/resolver into scope, even if runtime remains documentation-driven. Test with fixture packs and stub executables:

   - Zero, one, and multiple active providers
   - Exact-lane versus `any`
   - Duplicate priorities and missing P1
   - Invalid statuses and rejected-only candidates
   - Malformed/contradictory overrides
   - Version and readiness failures
   - Fallback state
   - Both Claude Code and Codex installation, skill discovery, root resolution, Superpowers loading, contract copying, and one end-to-end role resolution

   Keep real CLI probes as optional environment smoke tests rather than universal release gates. P13 should use a human-confirmed, versioned defect fixture rather than “a defect a trusted model caught.”

## Overall verdict

**Not ready for implementation.** Provider packs are the right decomposition, but the current design remains a Claude Code plugin with provider directories, not a harness-portable SDD wrapper. Codex operation is blocked by packaging, path resolution, and controller-tool assumptions; independently, provider selection and wildcard/priority resolution are nondeterministic. Revise the specification first, then update the plan around a harness-neutral entry skill, explicit controller adapters, a declarative validated pack contract, and fixture-based resolution tests.