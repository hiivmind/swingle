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
  },
  "grounding_cache": {
    "ttl_seconds": 604800,
    "by_provider": {
      "<provider-id>": {"ttl_seconds": 86400}
    }
  },
  "liveness": {
    "default": {
      "check_interval_seconds": 60,
      "startup_grace_seconds": 300,
      "silence_warning_seconds": 300,
      "hard_timeout_seconds": null
    },
    "by_tier": {
      "most-capable": {"startup_grace_seconds": 600}
    },
    "by_provider": {
      "<provider-id>": {
        "default": {"silence_warning_seconds": 600},
        "by_tier": {
          "standard": {"check_interval_seconds": 30}
        }
      }
    }
  }
}
```

`grounding_cache.ttl_seconds` is the default cache lifetime in seconds
(`604800` is seven days). A provider branch
(`grounding_cache.by_provider.<provider-id>.ttl_seconds`) takes precedence over the
global TTL; an explicit TTL supplied to a grounding operation takes precedence over
both. TTL `0` disables cache reuse and cache writes for that operation.

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
- **`model_preferences`** — optional ordered preferences for each provider and advisory
  tier (`cheapest`, `standard`, or `most-capable`). Preferences steer selection; they do
  not define availability. An entry is either a model name or a joined
  `{"model": ..., "effort": ...}` object carrying an effort preference (reasoning depth,
  thinking level) alongside the model. Effort stays advisory like the model name: the
  live CLI decides what it accepts, and an explicit user or task statement outranks the
  stored preference at dispatch time. See [concepts.md](concepts.md).
- **`grounding_cache`** — optional cache policy for observed provider mechanics and
  advisory model inventory. The cache is local project state, not a provider-availability
  gate. The provider-specific `ttl_seconds` branch wins over the global value.
- **`liveness`** — optional controller policy for one provider attempt. Fields are
  `check_interval_seconds`, `startup_grace_seconds`, `silence_warning_seconds`, and
  `hard_timeout_seconds`; positive integers are valid, and `hard_timeout_seconds` may be
  `null` to disable elapsed-time termination. Liveness diagnoses an attempt; it never
  certifies a provider or result. See the generic [liveness reference](liveness.md).

Provider IDs come from the provider directories. Model names are not checked against a
cached catalog. The live provider CLI supplies model reality.

`config set` takes a dotted key. A `model_preferences` write always names one provider
and tier, with a JSON list as the value. A `providers_by_contract` write names one
contract with either a JSON provider-ID string or a full JSON object keyed by tier, or
names one contract and tier with a provider-ID string:

```bash
python3 scripts/swingle config set --path <path/to/config.json> model_preferences.codex.cheapest '["<model-name>"]'
python3 scripts/swingle config set --path <path/to/config.json> model_preferences.codex.most-capable '[{"model":"<model-name>","effort":"<effort>"}]'
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

Optional branches are advisory and fail soft. Unknown provider IDs under
`grounding_cache.by_provider` or `liveness.by_provider`, unknown tiers, unknown fields,
and invalid optional branch values produce warnings; Swingle drops the affected branch
and continues with the remaining policy or built-in defaults. These warnings do not make
an installed provider unavailable.
The optional-policy rule is simple: unknown providers and invalid optional branches
produce warnings; they do not disable a provider or stop a dispatch.

Liveness resolution uses this precedence for each field, from highest to lowest:

1. An explicit liveness policy supplied for this dispatch.
2. `liveness.by_provider.<provider-id>.by_tier.<tier>`.
3. `liveness.by_provider.<provider-id>.default`.
4. `liveness.by_tier.<tier>`.
5. `liveness.default`.
6. The built-in policy for the tier.

An invalid explicit liveness policy is different from an invalid optional branch: it is
an explicit request that cannot be honored, so the controller stops before dispatch and
reports the error. It must not silently fall back to a built-in policy.
Therefore, invalid explicit liveness policy stops before dispatch.

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
