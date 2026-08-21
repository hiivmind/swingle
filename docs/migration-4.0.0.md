# Migrating to Swingle 4.0.0

Swingle 4.0.0 changes the ownership boundary. The LLM controls the current provider CLI;
Swingle keeps universal configuration, contracts, ledgers, and deterministic authoring checks.
There is no compatibility reader for the removed runtime facts or registry formats.

## Removed skills and commands

The scheduled verification and provider-certification workflow is removed. The removed
skill and command surfaces are:

- `swingle-verify`
- `scripts/validate-packs`
- `scripts/swingle-models`
- `scripts/shard-logs`
- `scripts/codex-smoke`
- `scripts/opencode-skills-path`

These replaced the old validation-gate, Step-0, readiness/version probe, static
model-resolution, controller-cache, and provider-health workflow. The remaining skills are:

- `swingle-delegate` for explicitly requested one-off jobs and batches.
- `swingle-setup` for setup and configuration migration.
- `swingle-sdd` for the small wrapper around a written SDD plan.

Use `python3 scripts/swingle` for configuration, ledger, and authoring checks. Do not call
the removed command surfaces.

## Removed configuration keys and paths

Remove these keys and paths from your configuration and automation:

- `require-verified-version`
- `superpowers`
- `note`
- `$SWINGLE_MODELS`
- `<project>/.swingle/models/`
- `${XDG_CONFIG_HOME:-~/.config}/swingle/models/`

The supported file is one JSON configuration file selected with whole-file precedence:
`$SWINGLE_CONFIG`, then `<project>/.swingle.json`, then
`${XDG_CONFIG_HOME:-~/.config}/swingle/config.json`. The supported keys are `disable`,
optional `default_provider`, `providers_by_lane`, and advisory `model_preferences`.

## Convert old model overrides

`swingle-setup` can inspect old model overrides in all three locations:

1. `$SWINGLE_MODELS` environment overrides.
2. Project model overrides under `<project>/.swingle/models/`.
3. User model overrides under `${XDG_CONFIG_HOME:-~/.config}/swingle/models/`.

Convert a clear winning row for each provider and task-intent tier to the ordered
`model_preferences` lists in the supported JSON file. Keep the intent labels `cheapest`,
`standard`, and `most-capable`. Do not copy static availability or verification status into
the new file.

Provider and lane choices can conflict across old layers. Review each conflict and choose
the intended `disable`, `default_provider`, `providers_by_lane`, and model preference values.
A preference is advisory: a stale model falls through to the next live preference or the
provider CLI default, and no preference can exclude a live model.

## Remove old references explicitly

`swingle-setup` is the supported migration aid for Swingle-owned configuration and
provider-state references. It can surface those references and request approval before
removing them. It does **not** inspect controller installation paths; search for and remove
those separately.

Explicitly remove every old reference from shell startup files, CI, scripts, editor settings,
project configuration, and personal notes, including:

- provider version registries and verification-log paths;
- model-table and cached-readiness paths;
- `$SWINGLE_MODELS` and both model override directories.

Do not leave an empty compatibility directory or a fallback environment variable. Git retains
history for removed notes and registries; runtime Swingle does not read them.

## After migration

Run the `swingle-setup` skill, then run:

```bash
python3 scripts/swingle config show
python3 scripts/swingle config validate <path/to/config.json>
python3 scripts/swingle check --root .
```

Then review one real delegation. The live provider CLI is the authority for its current
models and behavior. Record only evidence-backed recovery gotchas in the provider note; do
not recreate a catalog or certification log.
