# CLAUDE.md — swingle plugin

Swingle is a skills plugin for delegating work through coding-agent provider CLIs. The
LLM controls each dispatch; Python provides shared configuration, ledger, and authoring
structure. Keep the Claude Code, Codex, and plain skills distribution surfaces aligned.

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

Use the Python CLI for universal Swingle state and deterministic structure:

```bash
python3 scripts/swingle config init --user
python3 scripts/swingle config show --project .
python3 scripts/swingle config validate <path/to/config.json>
python3 scripts/swingle config set --path <path/to/config.json> <key> <json-value>
python3 scripts/swingle ledger init --path <path/to/ledger.md>
python3 scripts/swingle ledger show --path <path/to/ledger.md>
python3 scripts/swingle check --root .
```

The `--project .` flag makes the project-layer (`.swingle.json`) file visible.

Configuration uses one JSON file selected with whole-file precedence. Model preferences
are advisory ordered hints. An absent or stale preference must never make a live provider
or model unavailable. See [docs/config.md](docs/config.md) and
[docs/model-tiering.md](docs/model-tiering.md).

## Provider notes

When a provider has a real, non-obvious failure that changes recovery, add one evidence-backed
row to that provider's gotcha table. Follow [docs/pack-authoring.md](docs/pack-authoring.md).
Inspect the provider's current help before documenting behavior that is unclear. Git supplies
history; the note remains a living document and does not become a certification log.

## Change discipline

Keep contracts, the ledger format, configuration behavior, and authoring checks compatible
with their existing callers. Do not add provider-specific policy to Python or skills when the
LLM can use a provider note. Automation may respond to an observed failure, but it must not
periodically certify a provider.

Before committing documentation or code, run the focused checks for the changed contract:

```bash
python3 scripts/swingle check --root .
git diff --check
```

The integration branch is `develop`; changes land through a pull request. Release version
changes are owned by the release branch. Do not change plugin versions in ordinary work.
