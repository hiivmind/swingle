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
