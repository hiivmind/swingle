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
python3 scripts/swingle config show --project .
python3 scripts/swingle config validate <path/to/config.json>
python3 scripts/swingle config set --path <path/to/config.json> <key> <json-value>
```

Use `--project .` to make the project-layer (`.swingle.json`) file visible.

## Schema

The target schema is:

```json
{
  "disable": [],
  "providers_by_contract": {},
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
  no contract preference applies.
- **`providers_by_contract`** — an optional mapping from a role (the contract name under
  `contracts/`) to a preferred provider. The value is either a single provider ID
  (preferred for every tier) or a map from tier (`cheapest`, `standard`, `most-capable`)
  to a provider ID, so a role can steer differently at different tiers; tiers not named in
  the map fall back to `default_provider`. See [concepts.md](concepts.md).
- **`model_preferences`** — optional ordered model names for each provider and advisory
  tier (`cheapest`, `standard`, or `most-capable`). Preferences steer selection; they do
  not define availability. A preference names a model only; effort (reasoning depth,
  thinking level) is never a config field, since how a provider CLI accepts it varies and
  is resolved live at dispatch time. See [concepts.md](concepts.md).

Provider IDs come from the provider directories. Model names are not checked against a
cached catalog. The live provider CLI supplies model reality.

`config set` takes a dotted key. A `model_preferences` write always names one provider
and tier, with a JSON list as the value. A `providers_by_contract` write names one
contract with either a JSON provider-ID string or a full JSON object keyed by tier, or
names one contract and tier with a provider-ID string:

```bash
python3 scripts/swingle config set --path <path/to/config.json> model_preferences.codex.cheapest '["<model-name>"]'
python3 scripts/swingle config set --path <path/to/config.json> providers_by_contract.implementer '"<provider-id>"'
python3 scripts/swingle config set --path <path/to/config.json> providers_by_contract.fact-checker '{"cheapest":"<provider-id>","most-capable":"<provider-id>"}'
python3 scripts/swingle config set --path <path/to/config.json> providers_by_contract.fact-checker.most-capable '"<provider-id>"'
```

Setting a single tier on a contract whose current value is a plain string converts that
entry to a tier map containing the named tier; other tiers then fall back to
`default_provider`.

Get `<model-name>` from the provider's own current `--help` or model-listing output, not
from memory or an older config — see [model preference guidance](model-tiering.md).

## Warnings and fallback

Malformed JSON, a non-object root, invalid types, or a disabled routing target are
configuration errors regardless of which command reads the file. `config validate` and
`config set` additionally check that a provider ID named in `disable`, `default_provider`,
`providers_by_contract`, or `model_preferences` exists under `providers/`, catching a typo
at config-authoring time. `config show`, the read `swingle-delegate` uses on every dispatch,
skips that live directory check: the provider set is dev-time-static, and a bad reference
that slipped past authoring still surfaces the normal way, as a missing executable at
dispatch, rather than being re-litigated on every read.

Unknown keys and malformed optional `model_preferences` produce warnings. Swingle ignores
the affected preference and continues; an installed provider remains available. If a
preferred provider executable is missing, the LLM surfaces that fact rather than silently
substituting another provider.

The retired `providers_by_lane` key still loads: each entry expands to the contracts its
lane held (`implement` → `reader`, `implementer`; `review` → `task-reviewer`,
`design-reviewer`) with a warning naming what was expanded, and never reaches the roles
introduced after lanes were retired (`independent-review`, `fact-checker`,
`general-task`). Authored `providers_by_contract` entries always win over expanded ones.
Rewrite the preferences under `providers_by_contract`; the expansion exists so old files
keep steering until you do.

Model preferences are ordered hints. The LLM uses the first preferred model exposed by the
current CLI. A stale preference falls through to the next live preference or the provider's
default. An explicit user model goes directly to the provider CLI, which accepts or rejects
it. No preference can exclude a live model.
