---
name: swingle-setup
description: >-
  Manage Swingle-owned configuration, preferences, and ledgers with explicit consent for
  writes. Use for explicit setup or migration requests; it does not inspect provider auth,
  versions, readiness, or permissions. Explicit invocation only.
---

# Set Up Swingle-Owned State

## Scope

This skill manages Swingle configuration, preferences, and ledgers.
It does not inspect provider auth, versions, readiness, permissions, or controller installation.
Resolve `<root>` as `Path(<this SKILL.md>).parents[2]`. It must contain `skills/`, `scripts/`, `contracts/`, and `providers/`.
Run every Swingle-owned command as `python3 <root>/scripts/swingle`.

## Procedure

1. Run `python3 <root>/scripts/swingle config show --project .` for the current project.
2. If no configuration exists, offer `python3 <root>/scripts/swingle config init` at the user or project layer.
3. Before writing `default_provider` or `providers_by_lane`, report executable presence for the named provider(s) with the harness command lookup, so the routing choice points at something actually installed.
4. Before writing a `model_preferences` entry, inspect the target provider's current `--help` (or its model-listing subcommand, if it has one) so the preferred model name comes from what the live CLI names now, never a guess. This is the same help-first grounding `swingle-delegate` applies before a dispatch.
5. Apply requested preference changes with `python3 <root>/scripts/swingle config set`.
6. Show warnings from malformed optional preferences.
7. If requested outside a preference write, report executable presence for known providers with the harness command lookup.
8. Initialize or inspect a ledger with `python3 <root>/scripts/swingle ledger`.

A configuration failure never establishes that an external provider is unavailable.

## Explicit migration

Run migration only when the user asks for it.
Inspect the old override walk in precedence order: `$SWINGLE_MODELS`, project `.swingle/models/`, then the user model directory.
Retain `disable`, `default_provider`, and compatible lane routing.
Convert clear winning `verified` or `experimental` rows into ordered model preferences by provider and tier.
Show cross-layer or lane conflicts as ambiguous rows before a write.
Apply approved values with `python3 <root>/scripts/swingle config set`.
Remove each old key, directory, or environment reference only after explicit approval.
