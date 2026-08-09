# Design — Dispatch setup check-by-exception fast path

**Status:** Delivered 2026-08-09 — owner selected “Step0-gated + per-plugin-version cache”; implementation on `bugfix/dispatch-setup-fast-path` verified with 25 focused tests, 165 full-suite tests, `validate-packs --root`, and a live clean `--step0` Codex route.

## Problem

A one-job targeted read-lane dispatch performs a long unconditional preamble before it launches: orientation shell commands; trust validation; duplicated CLI version probing; and proactive reads of controller, role, playbook, safety, liveness, pack, log, local-record, and contract documents. The observed Codex review had not dispatched after this setup sequence.

The existing streamlining round made `scripts/validate-packs --step0` the single deterministic implementation for routing, readiness, config gating, and drift detection. The skills nevertheless retained a second, prose-driven “read every policy document first” gate. This duplicates work and defeats exception-based checking.

## Decision

`validate-packs --step0` is the mandatory fast gate. It remains preceded by the pack trust gate. It is the authority for provider selection, model readiness, config STOP/ASK conditions, and provider-version drift. The skills must not pre-explore the plugin tree or independently repeat `--version` after this gate.

Core doctrine is read by need, not prophylactically:

- `roles.md`: only when role classification or tier/lane resolution is genuinely ambiguous, or a deterministic gate identifies a role problem.
- `playbook.md`, `safety-doctrine.md`, and `verification-protocol.md`: only when a specific exception, containment decision, recovery decision, or drift finding needs policy beyond the skill’s inline rules.
- `liveness.md`: at the first actual background launch for the controller/provider version, immediately before constructing the wrapper.
- The routed provider’s manifest/body and the applicable role contract: still read before the first dispatch to that provider/role, at the point where their canonical command shape and output protocol are needed.
- Provider log guidance and the user’s provider record: read when `--step0` reports drift or when the routed provider body requires a lane-specific preflight/guidance lookup; never as an unconditional startup sweep.

Within a controller session, a document read for the installed plugin version is reused; the skill must not re-read it for later jobs unless the relevant input/version changes. No persisted cross-session fingerprint is introduced.

## Scope

Modify both `skills/delegate/SKILL.md` and `skills/sdd/SKILL.md` so their Setup/Step 0 procedures express this sequence symmetrically. Update skill contract tests to prevent restoration of an unconditional core-document wall and to preserve the registry-resolution text and hard `--step0` gate.

## Invariants

- Keep `validate-packs --root` trust validation and modified-provider explicit-approval requirement.
- Keep `validate-packs --step0` before every first routed dispatch, including STOP, ASK, CHANNEL, readiness, and drift semantics.
- Keep routed provider body/manifest and role contract as a pre-dispatch requirement.
- Keep clean-tree, liveness, evidence, containment, controller-adjudication, and controller-test/commit gates unchanged.
- Do not add persistent setup state or configuration schema.
- Shell-less controllers retain the existing prose fallback for the same deterministic outcome table.

## Verification

Add behavioral contract tests that inspect both skills for: `--step0` as the mandatory gate; explicit prohibition of orientation/duplicate probing; exception-only core-document policy; and retained provider-body, role-contract, liveness-at-launch, trust-gate, and registry-resolution requirements. Run the focused skill test module and the full Python test suite.
