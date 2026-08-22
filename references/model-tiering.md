# Model preference guidance

Swingle uses three advisory task-intent labels:

- **`cheapest`** — transcription, mechanical implementation, and focused codebase location.
- **`standard`** — adaptation implementation, external synthesis, and task review.
- **`most-capable`** — large or long-context implementation, design review, and final review.

These labels are preferences, not gates. Swingle ships no model catalog. The live provider
CLI supplies model reality and remains the authority for whether a model can run.

## Preference order

Configuration can list preferred models for each provider and tier:

```json
{
  "model_preferences": {
    "<provider>": {
      "cheapest": ["<preferred-model>"],
      "standard": ["<preferred-model>"],
      "most-capable": ["<preferred-model>"]
    }
  }
}
```

Each list is ordered. The LLM tries the first preference that the current provider CLI
exposes, then the next live preference. If none is available, it uses the provider CLI's
default. A stale preference therefore falls through rather than rejecting the provider.

An explicit user model goes directly to the provider CLI. The CLI accepts or rejects it;
Swingle does not pre-check it against cached data. No preference can exclude a live model.

The configuration file follows whole-file precedence. Use the commands below to inspect or
validate the active file:

```bash
python3 scripts/swingle config show --project .
python3 scripts/swingle config validate <path/to/config.json>
```

The `--project .` flag makes the project-layer (`.swingle.json`) file visible.

To write one preference, `config set` takes a dotted `model_preferences.<provider>.<tier>`
key and a JSON list value:

```bash
python3 scripts/swingle config set --path <path/to/config.json> model_preferences.codex.cheapest '["<model-name>"]'
```

Inspect the provider's current `--help` (or its model-listing subcommand, if it has one)
before choosing `<model-name>` — the same live-CLI grounding `swingle-delegate` applies
before a dispatch. Never carry a model name forward from an older config or from memory.

A tier resolves to one model, but the model and its effort (reasoning depth, thinking
level) are a single joined choice at dispatch time, not two independent settings.
`model_preferences` stores only the model name; effort is never written to config. How a
provider CLI accepts model and effort together varies by provider and by CLI version: some
expose a separate effort flag alongside the model flag, some accept effort folded into the
model identifier itself, some route it through a generic config-override mechanism, and
some may expose no CLI-level effort control at all. Inspect the target provider's current
`--help` before combining them; never assume one provider's pattern applies to another. See
[concepts.md](concepts.md).
