# Swingle configuration

Swingle reads one JSON configuration file. The first available path wins as a whole file;
keys are not merged between paths:

1. `$SWINGLE_CONFIG`
2. `<project>/.swingle.json`
3. `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`

If no file exists, Swingle uses an empty configuration. Use the Python CLI to create and
manage the file:

```bash
python3 scripts/swingle config init --user
python3 scripts/swingle config show
python3 scripts/swingle config validate <path/to/config.json>
python3 scripts/swingle config set --path <path/to/config.json> <key> <json-value>
```

## Schema

The target schema is:

```json
{
  "disable": [],
  "providers_by_lane": {},
  "model_preferences": {
    "<provider>": {
      "cheapest": ["<preferred-model>"],
      "standard": ["<preferred-model>"],
      "most-capable": ["<preferred-model>"]
    }
  }
}
```

`default_provider` is optional. The supported keys are:

- **`disable`** — an array of provider IDs that the user explicitly disables. Swingle
  honors this policy.
- **`default_provider`** — an optional provider ID used when no provider is explicit and
  no lane preference applies.
- **`providers_by_lane`** — an optional mapping from `implement` or `review` to a
  preferred provider ID.
- **`model_preferences`** — optional ordered model names for each provider and advisory
  tier (`cheapest`, `standard`, or `most-capable`). Preferences steer selection; they do
  not define availability.

Provider IDs come from the provider directories. Model names are not checked against a
cached catalog. The live provider CLI supplies model reality.

## Warnings and fallback

Malformed JSON, a non-object root, invalid types, unknown provider IDs in routing keys, or
a disabled routing target are configuration errors. `config validate` reports the errors,
and dispatch must stop until the file is corrected.

Unknown keys and malformed optional `model_preferences` produce warnings. Swingle ignores
the affected preference and continues; an installed provider remains available. If a
preferred provider executable is missing, the LLM surfaces that fact rather than silently
substituting another provider.

Model preferences are ordered hints. The LLM uses the first preferred model exposed by the
current CLI. A stale preference falls through to the next live preference or the provider's
default. An explicit user model goes directly to the provider CLI, which accepts or rejects
it. No preference can exclude a live model.
