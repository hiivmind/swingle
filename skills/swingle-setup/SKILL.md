---
name: swingle-setup
description: >-
  Manage Swingle-owned configuration, preferences, and ledgers with explicit consent for
  writes. Use for explicit setup or migration requests; it does not inspect provider auth,
  versions, readiness, or permissions. Explicit invocation only.
---

# Set Up Swingle-Owned State

## Scope and boundary

This skill manages only Swingle configuration, grounding policy, liveness policy, and
ledger placement. It never probes provider authentication, readiness, CLI version metadata,
permissions, or controller installation. See
[references/isolation.md](../../references/isolation.md) for the grounding boundary:
local cache and ledger decisions remain in the controller while live provider mechanics
may be isolated. Resolve `<root>` as
`Path(<this SKILL.md>).parents[2]`; it must contain `skills/`, `scripts/`, `contracts/`,
and `providers/`. Run every Swingle-owned command as `python3 <root>/scripts/swingle`.

The known-provider set is the live directory listing of `<root>/providers/`, one entry per
subdirectory. Read the selected provider's `pack.md` before grounding model names or
mechanics. The pack note is operational guidance, not authority for a model preference:
the live provider CLI is the authority.

The stages are **Inspect**, **Propose**, **Write**, and **Verify**. Inspect is read-only.
Propose stops for a decision. Write requires explicit consent for that specific
configuration change. Verify reports what changed. A successful write returns to Propose
with the updated findings; the session ends only when the user declines further changes.

## Stage 1 — Inspect (read-only)

Run:

```bash
python3 <root>/scripts/swingle config show --project <project>
```

Report exactly the resolved layer and path, errors, and warnings. If no layer exists,
say so plainly. Do not turn a configuration error into a provider-availability claim.
If the user asks to inspect ledger state, use the explicit project ledger directory:

```bash
python3 <root>/scripts/swingle ledger show --dir <project>/.swingle/delegate/ledger/
```

The command may show an empty directory as absent; Inspect does not create an empty ledger
or a readiness marker.

If the user asks about workspace readiness, inspect the nearest existing parent of
`<project>/.swingle/delegate/` for writability and report a non-writable parent plainly.
Inspect does not create the workspace during inspection.

Only after an approved routing or model change names a provider, report executable
presence with the harness command lookup. Summarize the result, for example
`all known providers resolve` or `codex is missing`; do not turn this into an
authentication, readiness, version, or permission probe.

## Stage 2 — Propose (stop and wait)

Explain Swingle in plain words when the user asks or when an empty configuration needs
context:

> Swingle steers delegated work to provider CLIs already installed on this machine.
> Contracts provide the fixed briefing for each kind of work; routing preferences say
> whom to try first. Each direct delegation records activity under
> `.swingle/delegate/ledger/`. Raw provider artifacts remain local and are never
> committed.

Offer decisions about work rather than config keys. Use the Stage 1 findings and name
only providers whose executables were observed. A routing choice resolves in this order:

1. **Contract** — the role and fixed briefing for the work.
2. **Tier** — `cheapest`, `standard`, or `most-capable`.
3. **Provider** — the installed coding agent.
4. **Model and effort** — the provider's model and effort pair.

Offer at most one sentence per direction plus a concrete example, then stop. Restate the
selected direction in plain words and as exact commands, including the destination layer.
An ambiguous answer is not consent; ask again.

### Targeted repair offers

When a delegate returns `next_action=setup_repair`, explain the exact blocker and offer
only the matching repair. The five repair targets are:

- `repair=config-error` — repair malformed or misplaced Swingle configuration after
  inspecting the reported path and error.
- `repair=provider-routing` — repair a named default or contract route after checking the
  named executable; do not substitute another provider.
- `repair=grounding-policy` — repair a grounding TTL or requested scope policy after
  showing the current configuration.
- `repair=liveness-policy` — repair a liveness policy value after showing its current
  fields; this does not run a provider.
- `repair=provider-grounding` — obtain fresh mechanics for the named provider only after
  named consent. A repair is not complete when refresh merely invalidates the cache:
  the controller must run `grounding refresh`, ground every returned scope, record the
  observations, then run `grounding show` and confirm usable status with a non-null expiry.
  Only that refresh → live grounding → record → show sequence may return `REPAIRED`.
Return only one of the following outcomes, followed by the exact unresolved blocker when
applicable:
A delegated repair preserves the task, role, tier, provider intent, explicit model and
effort, `$REPO_ROOT`, ledger directory, config path, and blocker in controller context.
It does not silently change the requested work. After one verified repair, return directly
to the suspended delegate flow.
```text
REPAIRED
DECLINED
BLOCKED
```

`DECLINED` returns `NEEDS_CONTEXT` to the delegate. One failed verified repair returns
`BLOCKED`; it does not start an automatic setup loop.

Proactive provider grounding has its own named-consent gate. Safe grounding required by
an already-authorized direct delegation needs no extra consent. Every configuration write
has a separate consent gate, including a write proposed after grounding.

## Stage 3 — Write (explicit consent)

A menu selection is not write consent. Before each write, state the exact command, the
destination layer, and the value being changed; obtain consent for that write alone.
If the destination has no file, create it as part of that approved write:

```bash
python3 <root>/scripts/swingle config init --project <project>
```

Project routing belongs in `<project>/.swingle.json`; user-wide habits belong in the
user layer. Apply approved values with `config set`, for example:

```bash
python3 <root>/scripts/swingle config set \
  --path <config-path> <key> '<json-value>'
```

Setup may show and edit default routing, `providers_by_contract`, model preferences,
grounding TTL, and liveness policy. It may run `grounding show` for diagnosis. It does
not probe authentication, readiness, CLI version metadata, permissions, or installation.

Before writing `default_provider` or `providers_by_contract`, check executable presence
for each named provider. Before writing a `model_preferences` entry, read
`<root>/providers/<provider>/pack.md` and run its documented model-discovery command (or
the documented help form when no listing exists). Store only the live CLI's model name;
when the user states an effort preference, verify that effort against live help before
storing the `{ "model": ..., "effort": ... }` value. Show warnings from malformed
optional preferences.

The first cache write is handled by Python: it creates
`.swingle/grounding/.gitignore` containing an ignore-all rule while retaining that
ignore file. The first `begin-direct` run creates
`.swingle/delegate/artifacts/.gitignore`; raw artifacts never committed. Setup never
offers to commit cache or artifact files. It separately offers commit or ignore for
`.swingle/delegate/ledger/`, because ledger events are project activity history.

Do not create a cache, ledger, or marker merely because setup was invoked. A configuration
failure never establishes that an external provider is unavailable.

## Stage 4 — Verify

After each approved configuration write, run:

```bash
python3 <root>/scripts/swingle config show --config <config-path>
```

Report the resulting values, errors, and warnings in one short block. For grounding
repair, run the matching `grounding show` and report its next action. For ledger
placement, inspect the explicit directory and report its path. If the written file is
`<project>/.swingle.json`, identify it as a repository file and let the user choose
commit or ignore. Return to Stage 2 with what remains unset.

## Explicit migration

Run migration only when the user asks. Inspect old overrides in precedence order:
`$SWINGLE_MODELS`, project `.swingle/models/`, then the user model directory. Retain
`disable`, `default_provider`, and compatible `providers_by_contract` routing; map a
legacy `providers_by_lane` entry to the contracts its lane held. Convert clear winning
`verified` or `experimental` rows into ordered model preferences by provider and tier.
Show cross-layer or contract-routing conflicts as ambiguous rows before a write. Apply
approved values with `config set`. Remove each old key, directory, or environment
reference only after explicit approval.
