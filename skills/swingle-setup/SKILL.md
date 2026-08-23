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
changes this set. Each provider directory also holds one living `pack.md` operating note —
read the target provider's note before grounding model names; it documents how to ask that
CLI what models it has (and flags the providers where no listing exists).
See [references/concepts.md](../../references/concepts.md) for how the classification
matrix, contract, tier, provider, model, and effort relate.

Work runs in four stages: **Inspect** (read-only), **Propose** (stop and wait for a
decision), **Write** (explicit consent), **Verify**. Never skip from Inspect to Write:
a status report is not a proposal, and a proposal is not consent.

Stages 2–4 form a loop, not a straight line: after each verified write, return to
Stage 2 with the updated findings and offer the next decision. A setup session ends
only when the user declines further changes — never after the first successful write.
A typical first run covers several rounds (default provider → contract routing →
model preferences → ledger) before closing.

## Stage 1 — Inspect (read-only)

1. Run `python3 <root>/scripts/swingle config show --project .` for the current project.
2. Report exactly three things: the resolved layer and path, any errors, any warnings.
   If no configuration exists at any layer, say so plainly.
3. Report executable presence only when an approved write names providers or the user
   asks for availability. Summarize the result (`all known providers resolve`,
   `codex is missing`) rather than listing every path.
4. Initialize or inspect a ledger on request with `python3 <root>/scripts/swingle ledger`.
   The ledger commands take an explicit `--path`; delegate's default is
   `<project>/.swingle/delegate/ledger.md`.

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

If the user asks for guidance on what the configuration actually controls, explain how
a request is routed — four choices, resolved in this order:

> 1. **Contract** — what kind of work the job is: writing code, reviewing changes,
>    research. The contract fixes the briefing the job receives, so every task of
>    that kind is held to the same standard.
> 2. **Tier** — how heavy the job is: quick mechanical work, everyday work, or the
>    hardest long-context jobs.
> 3. **Provider** — which installed coding agent runs the job: codex, claude, grok,
>    and so on.
> 4. **Model and effort** — within that agent, which model handles it and how hard it
>    thinks, decided together because they shape cost and quality as one.

Setting defaults in config pins these choices once, so every future delegation routes
the same way without deciding case by case. Keep it to that scale too.

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
4. Before writing a `model_preferences` entry, read `<root>/providers/<provider>/pack.md`
   and run the model-discovery command it documents (or inspect current `--help` where
   the note records that no listing exists), so the preferred model name comes from what
   the live CLI names now, never a guess — and never from the pack's orientation list,
   which is a cold-start hint only, not authority. This is the same help-first grounding
   `swingle-delegate` applies before a dispatch. `model_preferences` stores a model name
   only; effort is never a config field, and a request that names an effort level or
   reasoning depth belongs to the dispatch itself, not to this write.
5. Apply the change with `python3 <root>/scripts/swingle config set`.
6. Show warnings from malformed optional preferences.

A configuration failure never establishes that an external provider is unavailable.

## Stage 4 — Verify

Run `config show` scoped to the written layer and report the resulting values in one
short block. If the written file is `<project>/.swingle.json`, note that it is a repo
file and let the user decide whether to commit it or gitignore it.

Then loop: return to Stage 2 with the updated findings and offer what is still unset
(contract routing, model preferences for the providers now in play, ledger init). When
the user declines further changes, close with a one-line summary of every layer written
this session plus the commit-or-gitignore note — that closing summary is the only place
the session ends.

## Explicit migration

Run migration only when the user asks for it.
Inspect the old override walk in precedence order: `$SWINGLE_MODELS`, project `.swingle/models/`, then the user model directory.
Retain `disable`, `default_provider`, and compatible `providers_by_contract` routing; a legacy `providers_by_lane` entry maps to the contracts its lane held.
Convert clear winning `verified` or `experimental` rows into ordered model preferences by provider and tier.
Show cross-layer or contract-routing conflicts as ambiguous rows before a write.
Apply approved values with `python3 <root>/scripts/swingle config set`.
Remove each old key, directory, or environment reference only after explicit approval.
