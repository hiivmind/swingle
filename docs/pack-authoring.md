# Adding a provider pack

The strong, testable claim: **adding a pack requires zero edits to `core/`; routing is
manifest-driven**, and the validator that proves it ships with the repo. This page is the
authoring reference. The README carries the claim and the one command; the field grammar
lives here.

Add one directory under `providers/` satisfying the pack contract — manifest-only `pack.md`,
the version registry in `versions/`, sharded verification logs in `log/`, `models.yaml`
(the model table of record), and `models.md` (documentary narrative) — then run:

```bash
python3 scripts/validate-packs --root .
```

A non-zero exit blocks the pack. The validator is the single enforcement authority for
everything below; this page explains it, it does not re-specify it.

## Manifest fields

The manifest is the YAML front matter of `pack.md`.

**Required:** `schema-version`, `id`, `cli`, `verified-version`, `version-argv`,
`resume-argv`, `session-source`, `stall-signal`, `sandbox`.

**Optional:** `fork-flag`, `session-list-argv`, `readiness-argv`,
`readiness-timeout-seconds`, and:

| Field | Values | Meaning |
| --- | --- | --- |
| `report-transport` | `report-file` (default) · `captured-output` | How an agent's report gets back to the controller |
| `list-models-argv` | argv array | How to enumerate an open-catalog provider's live model list (e.g. pi). Surfaced by `swingle-models init`, never auto-executed |

## `report-transport`: the field to get right

Declare `captured-output` when the CLI cannot reliably write an agent-authored file to a
workspace path. The skills then ask for **no file** and take the full report as the captured
final message, saving it themselves.

Getting this wrong is not cosmetic: on such a provider a report-file request fails
*intermittently* while the exit code stays 0, so the report is silently missing and any
reviewer downstream loses an input. `agy` is `captured-output`; `claude`, `codex`,
`opencode`, `grok`, and `pi` are `report-file`.

This is the worked example of the wider rule — **provider capabilities are manifest fields,
not skill special-cases.** When a CLI behaves differently in a way a skill must branch on,
add a validated manifest field and have the skills read it; never hardcode a provider name in
skill logic. Adding a field means updating `REQ`/`OPTIONAL` and `ENUMS` in
`scripts/validate-packs`, declaring it in every shipped pack, and documenting it here.

## Enforcement invariants

Every value is validator-enforced, and `*-argv` arrays are **data** — `argv[0]` must equal
`cli`, and shell metacharacters are rejected (see [safety.md](safety.md#manifest-injection-is-closed)).
`verified-version` is stamped only by live end-to-end dispatch evidence, recorded in the
pack's `log/` shards. The full verification workflow is the `swingle-verify` skill and
[the Recording doctrine](../core/verification-protocol.md#recording).

## Version registry and logs

`providers/<id>/versions/<version>.md` holds every provider body. Its first line declares
its class with a `> Verified:` or `> Distilled:` header; the manifest's `verified-version`
names the current registry file. Filenames are dotted-numeric (`1.2.3.md`), and the
validator enforces the registry shape and header contract.

Provider evidence is recorded in chronological `providers/<id>/log/YYYY-MM.md` shards.
`verification-log.md` remains a read-only index. The registry lifecycle and resolution
rules are defined by [the Recording doctrine](../core/verification-protocol.md#recording);
do not duplicate them here.
