---
name: sdd-dispatch-verify
description: Re-verify one SDD dispatch provider pack, or all active packs, against this plugin's living knowledge base. Use when a CLI version bump is observed, a vendor releases new models, a dispatch behaves contrary to documented gotchas, or the user asks to verify the dispatch reference.
---

# SDD Dispatch Verification

## Invocation and scope

The argument names exactly one provider id, or `--all-active`. A single-provider round
edits only `<root>/providers/<id>/` and appends only that pack's
`verification-log.md`. `--all-active` runs isolated single-provider rounds for every active
pack. After two or more packs have results worth comparing, append the cross-provider
synthesis to `<root>/core/verification-log.md`; never put provider-specific evidence there.

Knowledge base (all paths are relative to the plugin tree root `<root>`):

- `<root>/core/verification-protocol.md` — portable probe and benchmark requirements
- `<root>/core/verification-log.md` — append-only cross-provider synthesis
- `<root>/providers/<id>/pack.md` — provider facts, version stamp, and canonical dispatch
- `<root>/providers/<id>/models.md` — provider model inventory and statuses
- `<root>/providers/<id>/verification-log.md` — provider-specific append-only verdicts

## Procedure

1. **Validate before probing.** Run `scripts/validate-packs --root <root>` and proceed only
   when it passes. The validator and repository fixtures are the portable gate.

2. **Read the selected pack first.** Read the verification protocol, then its `pack.md`,
   `models.md`, and verification log. Compare the manifest's `version-argv` output with
   `verified-version`, and identify the affected models and trigger.

3. **Run live smoke probes where the CLI exists.** P1–P12 are environment smoke tests, not
   portable assertions: run them only in an environment with the selected provider CLI.
   Work in a session scratchpad and follow the pack's canonical dispatch template. Never
   mask exit codes with pipes; verify side effects on disk; bound every probe with
   `timeout`; and use the cheapest eligible model.

4. **Qualify new models for their lane.** Before adding a new review-lane model, dispatch it
   with the standard task-reviewer contract against `tests/fixtures/p13/defect.diff` and its
   README context. It must satisfy P13 at the specified severity; a false-clean excludes it
   from review lanes. Before adding a new implement-lane model, run a small-implementer
   probe and verify its real working-tree result.

5. **Record only the active pack.** Append a dated verdict matrix with raw evidence to
   `providers/<id>/verification-log.md`. Update only that pack's `pack.md` and `models.md`
   when evidence changes facts, versions, or model status. Never rewrite earlier log entries.

6. **Synthesize only across providers.** If this round supplies a comparison spanning two or
   more packs, append the dated synthesis to `core/verification-log.md`. Otherwise leave the
   core log unchanged.

7. **Clean up and release.** Remove scratchpad artifacts and any test writes outside the
   workspace. For every verification commit, bump the plugin version by one patch and keep
   the repository version references aligned.

## Cautions

- Never assume a provider's permission or sandbox behavior survived a version bump.
- These probes can write: run only in the scratchpad, on a clean tree, and inspect the diff
  afterward.
- `--all-active` is orchestration, not permission to blend pack facts or logs.
