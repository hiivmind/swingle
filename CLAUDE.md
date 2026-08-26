# CLAUDE.md — swingle plugin

Swingle is a skills plugin for delegating work through coding-agent provider CLIs. The
LLM controls each dispatch; Python provides shared configuration, ledger, and authoring
structure. Keep the Claude Code, Codex, and plain skills distribution surfaces aligned.

## Design Principles (MANDATORY)

**You MUST read the relevant principle document before** adding or removing a provider
surface, changing configuration/ledger behavior, modifying the ownership boundary
(what Python manages vs what the LLM owns), or changing how automation responds to
an issue.

This is not advisory. Do not rely on summaries, memory, or assumptions — read the actual
principle document.

**Principles location:**
`/Users/nathanielramm/git/hiivmind/swingle-central/01.principles/swingle/`

See
[PRINCIPLES.md](../swingle-central/01.principles/swingle/PRINCIPLES.md)
for governance: statuses, category precedence, how to add new principles.

### a. Ownership

| Document | Scope | Status | Summary |
|----------|-------|--------|---------|
| llm-as-controller.md | core | ENFORCED | The LLM owns every dispatch; Swingle provides guidance, not a runtime |
| live-cli-as-authority.md | core | ENFORCED | The installed CLI is the authority for its own operation, never cached facts |
| python-boundary.md | core | ENFORCED | Python manages only universal state and structure; never runs provider/controller binaries |

### b. Guidance

| Document | Scope | Status | Summary |
|----------|-------|--------|---------|
| preference-never-availability.md | core | ENFORCED | Preferences steer selection but never define availability |
| provider-notes-structured-guidance.md | core | ADOPTED | Provider notes hold reactive gotchas and proactive dispatch guidance, both evidence-backed |
| help-first-recovery.md | core | ADOPTED | Inspect current help before documenting or recovering from provider behavior |

### c. Automation

| Document | Scope | Status | Summary |
|----------|-------|--------|---------|
| contracts-and-ledger-retained.md | core | ENFORCED | Contracts and the ledger remain; they improve quality and auditability |
| automation-observes-failures.md | core | ENFORCED | Automation responds to observed failures, never certifies on a schedule |

## Swingle Ownership Doctrine

- The LLM is the controller.

- The live provider CLI is the authority for provider operation.
- Never gate a provider with cached versions, models, auth results, readiness results, or controller facts.
- Python code can manage only universal Swingle state and deterministic Swingle structure.
- Provider notes contain only real, non-obvious failure guidance that changes recovery.
- Preferences steer selection. Preferences never define availability.
- Healthy delegation checks executable presence, briefs the task, records the ledger, and runs.
- Keep contracts and the ledger because they improve quality and auditability.
- Automation responds to observed product failures. It never certifies providers on a schedule.
- If CLI behavior is unclear, inspect current help before you add guidance.

## What the repository owns

The three shipped skills are deliberately small:

| Skill | Directory | Responsibility |
| --- | --- | --- |
| `swingle-delegate` | `skills/delegate/` | An explicitly requested one-off job or homogeneous batch. |
| `swingle-setup` | `skills/swingle-setup/` | Configuration migration, environment setup, and ledger setup. |
| `swingle-sdd` | `skills/sdd/` | The small wrapper that executes a written SDD plan through delegation. |

`contracts/` contains the reusable role contracts. `.swingle/delegate/` contains
workspace-local delegation artifacts and the ledger. Provider `pack.md` files contain
identity and gotchas, not inventories or certification records.

## Configuration and state

The Python CLI exposes read-only dispatch context plus typed grounding and ledger state/inspection commands:

```bash
python3 scripts/swingle dispatch context --project <project-root> --role <role> --tier <tier>
python3 scripts/swingle grounding show --project <project-root> --provider <provider-id>
python3 scripts/swingle ledger show --dir <ledger-directory> --format text
python3 scripts/swingle ledger validate --dir <ledger-directory>
```

The session-ledger directory is
`<project-root>/.swingle/delegate/ledger/`. Each session is an NDJSON stream selected
by its controller-session ID. A job's artifact directory is
`<project-root>/.swingle/delegate/artifacts/<run-id>/<job-id>/`; retain raw provider
output, reports, and authored evidence there for review.

Grounding cache files live under `<project-root>/.swingle/grounding/` and create a
cache-local `.gitignore`; raw cache and artifact files are ignored by default. Keep
ledger commits and source changes under separate Git decisions. A legacy ledger can be
inspected with `ledger show --legacy-path <legacy-ledger>`. Use the generic
[liveness reference](references/liveness.md) for controller policy terms.

The controller transports the exact authored prompt, including fenced literals, quotes,
blank lines, trailing newlines, dollar signs, backticks, and shell metacharacters. The
LLM composes provider commands from current grounding and guidance; Python does not
render commands or parse provider output. Interpret results dynamically from observed
provider evidence, then perform mandatory independent repository verification for every
mutation.

Configuration uses one JSON file with whole-file precedence. `disable`, an optional
`default_provider`, `providers_by_contract`, advisory `model_preferences`,
`grounding_cache`, and `liveness` are documented in
[references/config.md](references/config.md). Model preferences are advisory; the live
CLI supplies model reality. See [references/model-tiering.md](references/model-tiering.md).

## Contracts

Each role (`reader`, `implementer`, `task-reviewer`, `design-reviewer`,
`independent-review`, `fact-checker`, `general-task`) has one transport-neutral operating
contract under `contracts/`, selected in `skills/delegate/SKILL.md` step 1 through the
classification matrix in [references/concepts.md](references/concepts.md). A new contract
is a new role in the matrix; it must justify itself as improving delegated quality or
auditability, must never mention a provider, its transport, or sandboxing, and must carry
the mandatory current-working-directory element. Follow
[docs/contract-authoring.md](docs/contract-authoring.md).

## Provider notes

When a provider has a real, non-obvious operating fact, reactive (an observed failure and
its recovery) or proactive (a verified dispatch-mechanics fact, without a failure), add one
evidence-backed row to the matching table. Follow
[docs/pack-authoring.md](docs/pack-authoring.md). Inspect the provider's current help before
documenting behavior that is unclear. Git supplies history; the note remains a living
document and does not become a certification log.

## Change discipline

Keep contracts, the ledger format, and configuration behavior compatible with their
existing callers. Do not add provider-specific policy to Python or skills when the LLM can
use a provider note. Automation may respond to an observed failure, but it must not
periodically certify a provider.

Before committing documentation or code, run the test suite and the whitespace check:

```bash
python3 -m pytest -q
git diff --check
```

The integration branch is `develop`; changes land through a pull request. Release version
changes are owned by the release branch. Do not change plugin versions in ordinary work.
