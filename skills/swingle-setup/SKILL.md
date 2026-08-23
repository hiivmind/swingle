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
The known-provider set is the live directory listing of `<root>/providers/`, one entry per
subdirectory. List it fresh each run; never recall or assume the set from memory, an
earlier session, or a prior config file. Adding or removing a provider pack directory
changes this set.
See [references/concepts.md](../../references/concepts.md) for how the classification
matrix, contract, tier, provider, model, and effort relate.

Work runs in four stages: **Inspect** (read-only), **Propose** (stop and wait for a
decision), **Write** (explicit consent), **Verify**. Never skip from Inspect to Write:
a status report is not a proposal, and a proposal is not consent.

## Stage 1 — Inspect (read-only)

1. Run `python3 <root>/scripts/swingle config show --project .` for the current project.
2. Report exactly three things: the resolved layer and path, any errors, any warnings.
   If no configuration exists at any layer, say so plainly.
3. Report executable presence only when an approved write names providers or the user
   asks for availability. Summarize the result (`all known providers resolve`,
   `codex is missing`) rather than listing every path.
4. Initialize or inspect a ledger on request with `python3 <root>/scripts/swingle ledger`.

## Stage 2 — Propose (stop and wait)

If the findings would be new to this user — empty config, first run, hesitation about a
term — offer a quick explanation of how Swingle works, and give it in plain words when
they accept:

> Swingle steers work you delegate to provider CLIs already installed on this machine —
> codex, claude, and so on actually do the job; Swingle only advises who gets it. Each
> kind of work (writing code, reviewing, research) has one fixed briefing called a
> contract, so every dispatch of that kind is held to the same standard. Your choices
> here are advice, not locks: they say whom to try first, and anything installed stays
> usable no matter what. Every delegation leaves one line in a ledger file kept under
> `.swingle/` in your project, so you can always see what ran, where, and how it ended.
> That folder is local activity history — if you would rather not commit it, add
> `.swingle/` to `.gitignore`.

Keep it to that scale — a few sentences, no schema vocabulary unless the user asks.
Then present the findings and offer directions as decisions about *work*, not about
config keys. A human understands questions like these:

- **Who does the work when nothing specific applies?** In config this is
  `default_provider`.
- **Who writes code, who reviews it, who does lookups?** In config this is
  `providers_by_contract`: `implementer` writes or changes code, `task-reviewer`
  checks completed changes, `design-reviewer` critiques proposed ones, `reader` does
  research and reports, `fact-checker` verifies outside claims against sources,
  `independent-review` judges an argued position, `general-task` catches everything
  else.
- **Which model for which weight of work?** In config this is `model_preferences`:
  for one provider, a preferred model per weight — quick mechanical jobs, everyday
  work, the hardest long-context jobs.

For each direction you offer, build a concrete example **from the Stage 1 findings** and
say in one line why you suggest it. Name only providers whose executables resolved;
use only the roles listed above; never invent a role to fit something the user said.
Example shape (values come from your inspection, not from this text):

> Nothing routes yet and both codex and claude are installed. A common start: codex
> does the coding, claude reviews it — I'd write those two mappings plus nothing else
> until you want more.

Offer at most one sentence per direction plus its example, then stop.

When the user answers, bind the answer to exactly the option's text:

- Restate the selected direction in plain words and as the exact commands you will run,
  name the destination layer, and proceed only on that basis.
- An ambiguous or out-of-scope reply ("2" when you offered different options, "yes"
  to a status report) means re-ask, never improvise a nearby action.
- Do not write because the user answered a menu. A menu selects a topic; only your
  restated commands, approved, are consent.

## Stage 3 — Write (explicit consent)

1. If the destination layer has no file yet, run `config init` for that layer first —
   as part of the approved write, saying so in one line. Creating a layer is a
   precondition of an approved write, never a substitute for one and never a standalone
   surprise.
2. If the user did not name a layer, ask before writing. Repo-specific routing belongs
   in the project layer (`<project>/.swingle.json`); machine-wide habits belong in the
   user layer.
3. Before writing `default_provider` or `providers_by_contract`, report executable
   presence for the named provider(s) with the harness command lookup, so the routing
   choice points at something actually installed. Keys are role stems under `contracts/`
   (`implementer`, never `implementer-contract`); a value is a single provider ID or a
   map from tier to provider ID; never write an invented role name to fit a task
   description the user gives.
4. Before writing a `model_preferences` entry, inspect the target provider's current
   `--help` (or its model-listing subcommand, if it has one) so the preferred model name
   comes from what the live CLI names now, never a guess. This is the same help-first
   grounding `swingle-delegate` applies before a dispatch. `model_preferences` stores a
   model name only; effort is never a config field, and a request that names an effort
   level or reasoning depth belongs to the dispatch itself, not to this write.
5. Apply the change with `python3 <root>/scripts/swingle config set`.
6. Show warnings from malformed optional preferences.

A configuration failure never establishes that an external provider is unavailable.

## Stage 4 — Verify

Run `config show` scoped to the written layer and report the resulting values in one
short block. If the written file is `<project>/.swingle.json`, note that it is a repo
file and let the user decide whether to commit it or gitignore it.

## Explicit migration

Run migration only when the user asks for it.
Inspect the old override walk in precedence order: `$SWINGLE_MODELS`, project `.swingle/models/`, then the user model directory.
Retain `disable`, `default_provider`, and compatible `providers_by_contract` routing; a legacy `providers_by_lane` entry maps to the contracts its lane held.
Convert clear winning `verified` or `experimental` rows into ordered model preferences by provider and tier.
Show cross-layer or contract-routing conflicts as ambiguous rows before a write.
Apply approved values with `python3 <root>/scripts/swingle config set`.
Remove each old key, directory, or environment reference only after explicit approval.
