# Swingle Configuration Schema

`docs/config.md` is the canonical reference for Swingle configuration files (`config.json` and `.swingle.json`).

## Layered Configuration Walk & Precedence

Swingle loads configuration from a layered search walk using whole-file precedence. The first file found wins (no key-by-key merging across layers):

1. **Environment override**: `$SWINGLE_CONFIG` (if set)
2. **Project layer**: `<project>/.swingle.json`
3. **User layer**: `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`

If no configuration file exists at any of these paths, Swingle uses built-in defaults (no disabled providers, no default provider override, no lane routing overrides, and `require-verified-version: false`).

## Configuration Keys

The configuration object supports the following top-level keys:

### `disable`
- **Type**: `array` of `string`s
- **Default**: `[]`
- **Semantics**: List of provider IDs to disable for session dispatches (e.g. `["grok"]`). Any provider ID listed in `disable` will be excluded from provider detection and selection. All entries must name valid, known provider IDs.

### `default_provider`
- **Type**: `string`
- **Default**: `null` (omitted)
- **Semantics**: Sets the default provider ID to route dispatches to when no explicit provider or lane directive is given (e.g. `"codex"`). Must name a valid, known provider ID and must not be a disabled provider.

### `providers_by_lane`
- **Type**: `object` (mapping `string` lane name to `string` provider ID)
- **Default**: `{}`
- **Semantics**: Maps specific execution lanes (`"implement"` or `"review"`) to target provider IDs (e.g. `{"implement": "codex", "review": "opencode"}`). Target provider IDs must name valid, known provider IDs and must not be disabled.

### `require-verified-version`
- **Type**: `boolean`
- **Default**: `false`
- **Semantics**: When `true`, enforces strict CLI compatibility. If an installed provider's CLI version does not match the provider pack's `verified-version`, the provider is marked incompatible and excluded.

## Unknown Keys Semantics

Top-level keys not recognized in the schema (keys other than `disable`, `default_provider`, `providers_by_lane`, `require-verified-version`, and `note`) are treated as warnings:
- A warning is printed to `stderr`.
- The unknown key is dropped/ignored.
- Loading **succeeds** (unknown keys do not trigger a STOP condition).

## Dispatch STOP Conditions

The `swingle-sdd` skill inline statement is the canonical source for dispatch STOP conditions, which `docs/config.md` quotes verbatim:

> `disable/steer only; malformed/wrong-typed config, an unknown provider ID in disable, default_provider, or any providers_by_lane value, a disabled default_provider or providers_by_lane target, or set-but-unreadable $SWINGLE_CONFIG = STOP with the error.`

Dispatch skills (`swingle-sdd` and `swingle-delegate`) enforce a STOP when:
1. The configuration file is malformed JSON or unreadable.
2. The root JSON structure is not an object.
3. Any recognized key has an invalid data type.
4. An unknown provider ID is referenced in `disable`, `default_provider`, or `providers_by_lane`.
5. `default_provider` or a `providers_by_lane` value names a provider listed in `disable`.
6. `$SWINGLE_CONFIG` is set but the specified file cannot be read.

## Neutral Template JSON

When scaffolding a new configuration file (e.g., via `swingle-setup`), use the neutral template with all keys present in a neutral state:

```json
{
  "disable": [],
  "providers_by_lane": {},
  "require-verified-version": false
}
```

## Validation Entry Point

Validate configuration files using `validate-packs --check-config`:

```bash
python3 scripts/validate-packs --check-config <path/to/config.json>
```

This command parses the configuration file, verifies object structure and types, checks provider ID validity against installed packs, and reports any malformed fields or invalid references.
