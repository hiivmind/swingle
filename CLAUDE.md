# CLAUDE.md — swingle plugin

Controller-neutral plugin for SDD execution via external provider CLIs (codex / opencode / agy / grok / pi / claude).
This repository is simultaneously a **Claude Code plugin** (`.claude-plugin/`), a
**Codex plugin** (`.codex-plugin/` + `.agents/plugins/marketplace.json`), and a plain
skills tree — treat all three distribution surfaces as first-class.

## The one hard gate

Before every commit:

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit ...
```

A non-zero exit blocks the commit. The validator enforces manifest grammar, model-table
shape, resolution order, version sync (the two plugin.json files; a README
`**Version:**` line is checked only if one exists), and the relative-link scan.

**Chain the gate to the commit with `&&`, never `;`.** Written as separate statements the
gate becomes a neighbouring command whose failure you have to notice, and a failing gate
will commit and push anyway — observed 2026-07-23, when a purity violation reached `main`
because the shell used `;`. The gate is a precondition, not a preceding step.

## Living-document rules

- **Step 0 is script-executed where shell exists.** The dispatch skills run
  `scripts/validate-packs --step0` and adjudicate its typed outcomes
  (`STOP:`/`ASK:`/`CHANNEL:`/`warning:`); the skills' outcome table is normative and
  the script is its executable rendering — change them together.
- **Verification logs are append-only.** Provider entries live in chronological
  `providers/<id>/log/YYYY-MM.md` shards; `verification-log.md` is a retained read-only
  index. Follow [the Recording doctrine](core/verification-protocol.md#recording) for
  recording rules.
- **Log entries may carry operating guidance** (`core/verification-protocol.md`
  Recording): an instruction a future dispatcher must follow from that version forward,
  house style `**Guidance (<lanes>):** …` under the entry heading. The verify skill
  writes it; the dispatch skills read the routed provider's log and act on it. Always an
  instruction, never a verdict — an undiagnosed failure is an open issue, not an entry.
- **Purity boundary**: provider *names* may appear in `core/`; model ids and invocation
  strings may NOT — they live in `providers/<id>/`. The validator's link scan and the
  purity adjudication (2026-07-23) are the precedent. This binds `core/` prose *and*
  verification-log entries — write "the cheapest tier", not the slug. It binds
  `skills/**` too, enforced by `tests/test_delegate_skill.py`.
- **Provider capabilities are manifest fields, not skill special-cases.** When a CLI
  behaves differently in a way a skill must branch on, add a validated manifest field and
  have the skills read it — never hardcode a provider name in skill logic.
  `report-transport: report-file | captured-output` (added v1.4.0) is the worked example:
  agy cannot reliably write an agent-authored file to a workspace path, so it declares
  `captured-output` and both skills ask for no file. Adding a field means updating `REQ`
  or `OPTIONAL` plus `ENUMS` in `scripts/validate-packs`, declaring it in every shipped
  pack, and documenting it in the README's "Adding a provider" table.
- **Provider registry layout is structural.** `pack.md` is manifest-only; every provider
  body lives in `providers/<id>/versions/<version>.md` with a declared class header, and
  the manifest's `verified-version` names the current file. Provider evidence lives in
  chronological `providers/<id>/log/YYYY-MM.md` shards, while `verification-log.md` is a
  read-only index. Lifecycle and resolution are defined only in
  [the Recording doctrine](core/verification-protocol.md#recording); the validator enforces
  the structural contract.
- **Prefer structural fixes to prompt workarounds.** A prompt nudge can only lower the
  rate of a misbehaviour; routing around it can remove the failure mode. When you claim a
  fix works, say which kind it is — and do not call a mitigation "verified" off a single
  run when the failure is intermittent (2026-07-23 precedent: a 19-run trial returned
  p = 0.21 and could not support the claim a single green run had seemed to).
- **The plugin version moves once, at the release cut** (adopted 2026-07-31,
  superseding the per-change patch-bump rule): feature/bugfix/docs/automation PRs to
  `develop` — including automated pack-fact PRs — never touch the version. The
  `release/*` branch bumps it exactly once (keeping `plugin.json` and
  `.codex-plugin/plugin.json` in sync), which is what fires the auto-tag on merge to
  `main`. This removes version conflicts between concurrent PRs. (The README no
  longer carries a `**Version:**` line — retired 2026-07-30; the validator still
  enforces sync if one is reintroduced.)
- **On any CLI version bump** (a *maintenance* activity, NOT a per-dispatch gate): read
  the pack's `Changelog` row FIRST (verify skill step 2b), then re-verify with
  `swingle-verify <id>`. Never assume permission or sandbox behavior survived a patch
  release — agy has flipped permission behavior on every one. The `swingle-sdd`/`swingle-delegate` skills
  do not stop a user on drift: the version gate is advisory (warn + proceed), and a
  channel-class dispatch failure *while drift is in effect* is what surfaces a
  drift-triggered verification finding to recommend recording — the real-world trigger for
  a re-verify round.
- `verified-version` in a pack manifest is stamped only by live end-to-end dispatch
  evidence, recorded in that pack's verification log.
- **Core doctrine states requirements.** A rule in `core/` says what to do and when;
  it does not retell the incident, experiment, or date that produced it. Evidence
  lives in verification logs (append-only, dated — that is their job); a rule that
  rests on recorded evidence cites the log entry, never restates its story.
  A **failure mode** — a timeless causal condition, stated without dates, provider
  or version identifiers, sample counts, or observed-run outcomes — may be named in
  one or two sentences when the rule is unintelligible without it. Any of those
  excluded features makes it **failure history**, which never appears in a rule body.

## Layout contract

`skills/sdd/SKILL.md` and `skills/delegate/SKILL.md` both resolve the plugin root as their
grandparent directory — `controllers/`, `core/`, `providers/`, `contracts/` are load-bearing
siblings of `skills/`. `controllers/<controller>.md` documents each CLI in its **driving**
role (skill-loading, native subagents, background jobs, asset root); `providers/<id>/`
documents each CLI as a **dispatch target** (manifest-only pack, version registry, model
tables, and sharded verification logs). The same CLI appears in both, once per role. Anything that breaks that
physical layout (moving skills out alone, flattening the tree) breaks every install route. Codex plugin installs cache the whole repo, so the
layout survives; the symlink route depends on it.

The four skills and what they own (frontmatter names are `swingle-`-prefixed since v2.1.0
because opencode/Codex register skills in a flat namespace; directory names are unchanged):

| Skill | Directory | Owns |
| --- | --- | --- |
| `swingle-sdd` | `skills/sdd/` | executing a written multi-task plan (task reviews, ledger, final review) |
| `swingle-delegate` | `skills/delegate/` | an explicitly requested one-off job or homogeneous batch — no plan, no superpowers dependency; workspace `.swingle/delegate/` |
| `swingle-setup` | `skills/swingle-setup/` | onboarding, environment health checks, config migration, and registry setup |
| `swingle-verify` | `skills/swingle-verify/` | re-probing a CLI on version bumps and model releases |

`swingle-delegate` must stay free of any *operational* superpowers dependency: it never invokes a
superpowers skill, never runs `scripts/sdd-workspace`, and never touches `.superpowers/`.
The structural tests assert exactly one negative-disclaimer mention of each, so adding a
second mention of either string fails the suite.

## Distribution surfaces to keep in sync

| Surface | Files |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| Codex plugin | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` (plugin source stays `local ./` — a git-subdir self-reference fails) |
| Codex skills metadata | `skills/*/agents/openai.yaml` |
| Docs | `README.md` install sections, `codex/INSTALL.md` |

## Git flow for this repo

**`main` is protected by a ruleset (2026-07-23). Everything lands via a PR — including
docs and living-document rounds.** This supersedes the previous standing direction to
commit doc fixes directly to `main`: that exception is withdrawn, because the ruleset now
enforces the PR path and a documented exception that only an admin bypass can satisfy is
worse than no exception at all.

- **`develop` is the integration branch (adopted 2026-07-24).** Any change:
  `feature/*` / `bugfix/*` / `docs/*` / `chore/*` branch → PR to `develop` → merge on the
  owner's instruction. Releases go `develop` → `release/*` → PR to `main` → tag.
- `main` remains protected and release-only: it blocks force-pushes, deletion, and
  non-linear history; conversation resolution is required. The ruleset currently protects
  `main` only — `develop` has no equivalent ruleset yet, so branch protection there is
  convention, not enforcement, until an admin adds one.
- The ruleset lists **repo admin as a bypass actor**, so a direct push to `main` will
  succeed for the owner. That is an emergency escape hatch, not the flow — using it
  silently reintroduces the conflict this section exists to remove.
- Releases are tagged automatically: `.github/workflows/release.yml` runs on every push to
  `main`, reads the version from `.claude-plugin/plugin.json`, and — if `v<version>` is not
  already tagged — validates packs, tags the release head, and creates the GitHub release
  with generated notes. A push that doesn't bump the version is a no-op. Never hand-tag a
  release; bumping the version on the `release/*` branch is what cuts it.

**CI does not replace the hard gate.** `.github/workflows/ci.yml` runs `pytest` only, as
the `tests` required status check; `.github/workflows/release.yml` tags and publishes the
GitHub release on pushes to `main` (see the git-flow section). `pytest` drives `scripts/validate-packs` via subprocess
(`tests/test_validate_packs.py`), so the validator IS enforced on GitHub — but
`./scripts/codex-smoke` is **not** in CI by deliberate choice: it asserts developer-workspace
layout, not repo correctness. Run the full gate locally, chained with `&&`, as above.

## Testing

```bash
uv run --with pytest pytest tests/ -q   # validator + skill-structure suites
```

Fixtures in `tests/fixtures/` (including the P13 reviewer-qualification diff) are
evidence artifacts — do not regenerate them casually.
