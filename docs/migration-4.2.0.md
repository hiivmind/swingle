# Migration to 4.2.0

4.2.0 replaces lane-based provider routing with contract-keyed routing (the routing
framework matrix). Nothing stops working: an old `providers_by_lane` key still loads and
expands, and ledgers written by earlier versions remain valid records. This guide covers
the recommended rewrites.

## Rewrite `providers_by_lane` as `providers_by_contract`

The supported routing key is now `providers_by_contract`. Its keys are the role names
under `contracts/` (`reader`, `implementer`, `task-reviewer`, `design-reviewer`,
`independent-review`, `fact-checker`, `general-task`), not lanes. A value is either a
single provider ID or a map from tier to provider ID.

A legacy lane entry expands to the contracts its lane held:

| Old lane | Expands to |
| --- | --- |
| `implement` | `reader`, `implementer` |
| `review` | `task-reviewer`, `design-reviewer` |

So this old configuration:

```json
{
  "providers_by_lane": {
    "implement": "codex",
    "review": "grok"
  }
}
```

becomes the supported equivalent:

```json
{
  "providers_by_contract": {
    "reader": "codex",
    "implementer": "codex",
    "task-reviewer": "grok",
    "design-reviewer": "grok"
  }
}
```

While a legacy key is present, every load reports a warning naming what it expanded to —
use that to check your rewrite. Once rewritten under `providers_by_contract`, remove the
`providers_by_lane` key.

To write entries one at a time:

```bash
python3 scripts/swingle config set --path <path/to/config.json> providers_by_contract.implementer '"<provider-id>"'
python3 scripts/swingle config set --path <path/to/config.json> providers_by_contract.fact-checker '{"cheapest":"<provider-id>","most-capable":"<provider-id>"}'
python3 scripts/swingle config validate <path/to/config.json>
```

An authored entry always beats lane expansion: any role you name explicitly is no longer
affected by a leftover `providers_by_lane` entry.

## Tier-keyed routing

A `providers_by_contract` value can be keyed by tier (`cheapest`, `standard`,
`most-capable`) instead of naming one provider. Tiers are advisory intent labels; see
[Model preference guidance](../references/model-tiering.md). A tier-map entry without a
tier you dispatch at falls back to `default_provider`.

## Ledger allocations carry `tier=`

New allocated events include `tier=<cheapest|standard|most-capable>`:

```text
NNN allocated: role=<role> task=<summary> contract=<path> tier=<cheapest|standard|most-capable>
```

Include it on new allocations. Ledgers written before 4.2.0 keep their historical lines
as records of the old format — do not rewrite or delete them. No conversion is needed.

## New contracts

Three roles were added: `independent-review` (judge a stated position),
`fact-checker` (verify external claims against sources), and `general-task` (the
catch-all when a request resists classification). Classify through the matrix in
[Operating surface concepts](../references/concepts.md); nothing else about delegation
changed.
