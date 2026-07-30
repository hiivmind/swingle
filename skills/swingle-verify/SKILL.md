---
name: swingle-verify
description: Re-verify one Swingle harness pack, or all active packs, against this plugin's living knowledge base. Use when a CLI version bump is observed, a vendor releases new models, a dispatch behaves contrary to documented gotchas, or the user asks to verify the dispatch reference.
---

# Swingle Verification

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
- `<root>/providers/<id>/models.yaml` — provider model table of record (statuses); `models.md` — narrative inventory
- `<root>/providers/<id>/verification-log.md` — provider-specific append-only verdicts

## Procedure

0. **Resolve the WRITABLE SOURCE tree before touching anything.** The `<root>` this skill
   loaded from may be an installed plugin cache (Claude Code:
   `~/.claude/plugins/cache/...`; Codex: `~/.codex/plugins/cache/...` or
   `~/.codex/.tmp/marketplaces/...`) — a throwaway snapshot that the next
   upgrade/reinstall silently clobbers. **Never record verification results into an
   installed copy.** Distinguish them:
   - SOURCE: `git -C <root> rev-parse --is-inside-work-tree` succeeds AND the path is not
     under a plugin cache; edits there are committable.
   - INSTALLED: cache path, or no git work tree. Locate the source checkout instead
     (the repo for `https://github.com/hiivmind/swingle` on this machine;
     ask the user for its path if unknown — clone it if absent). Run the round against
     the source tree's `<root>`, commit per the repo's CLAUDE.md, then refresh the
     installed copies (Claude Code: reinstall/reload the plugin; Codex:
     `codex plugin marketplace upgrade swingle-marketplace` +
     `codex plugin add swingle@swingle-marketplace`).
   The probes may READ the installed copy's manifests to identify what a user is running,
   but every write — pack facts, logs, version bumps — targets the source tree only.

   **No writable source? Raise a GitHub issue instead of dropping the finding.** When no
   source checkout exists on the machine, or the user lacks push rights to the source
   repository, file each finding as an issue on the upstream project
   (`gh issue create --repo hiivmind/swingle --label verification ...`,
   or the web form — the repo ships a "Verification finding" issue template at
   `.github/ISSUE_TEMPLATE/verification-finding.md`). One issue per independent finding,
   with the probe-grade fields filled: CLI version, plugin version, copy type, trigger,
   assertion under test, verdict, verbatim evidence (secrets redacted), impact. A finding
   recorded only in an installed cache is a finding lost.

   Recording ladder, in order: (1) writable source checkout → edit + commit there;
   (2) source clone possible but no push rights → commit locally AND open an issue (or a
   PR) carrying the log entry; (3) no source tree at all → issue only.

   **Deduplicate before filing.** Search existing issues first —
   `gh issue list --repo hiivmind/swingle --label verification --state all
   --search "<cli> <key terms of the finding>"` — and choose by what your evidence adds:
   - **Same finding already open** → add a 👍 reaction to weight its prioritisation
     (`gh api repos/hiivmind/swingle/issues/<n>/reactions -f content='+1'`)
     and file nothing.
   - **Same finding, new angle or wrinkle** (different CLI version, different failure
     signature, a workaround, a narrower repro) → comment on the existing issue with just
     the new evidence; do not open a duplicate.
   - **Closed issue, finding recurs** on a version at or above the fix → comment on the
     closed issue asking for reopen, with the fresh evidence.
   - **Genuinely distinct** → new issue from the template.

1. **Validate before probing.** Run `scripts/validate-packs --root <root>` and proceed only
   when it passes. The validator and repository fixtures are the portable gate.

2. **Read the selected pack first.** Read the verification protocol, then its `pack.md`,
   `models.yaml`, `models.md`, and verification log. Compare the manifest's `version-argv` output with
   `verified-version`, and identify the affected models and trigger.

2b. **Read the vendor changelog before probing.** Every pack carries a `Changelog` row
   (agy: https://antigravity.google/changelog?tab=cli; codex and opencode: their GitHub
   releases pages). Read the entries between `verified-version` and the installed version
   FIRST — they tell you which probes to weight and what new surface exists, and they
   date behavior changes precisely (e.g. agy 1.1.4's "headless honors persisted
   settings.json policies" explained a permission regression the probe suite initially
   misattributed to 1.1.5). Quote the relevant changelog lines in the verification-log
   entry alongside the observed evidence.

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
   `providers/<id>/verification-log.md`. Update only that pack's `pack.md` and `models.yaml`
   when evidence changes facts, versions, or model status (stamps land in models.yaml — the
   table of record; models.md keeps the narrative entry). Never rewrite earlier log entries.
   If the round produced an **operating instruction** — something a future dispatcher
   must do differently on this version and forward — record it per the guidance
   convention in `core/verification-protocol.md` Recording (house style
   `**Guidance (<lanes>):** …` directly under the entry heading; lifting a standing
   restriction is itself guidance). A round that found nothing to instruct adds no
   guidance line — the entry's prose and verdict matrix are the record.

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
