<p align="center">
  <img src="docs/images/hero-banner.svg" alt="Swingle" width="100%">
</p>

# Swingle

Swingle lets the coding-agent harness you are already driving (Claude Code, Codex, opencode,
Grok, Pi, Antigravity) dispatch work to the other agent CLIs installed on the same machine.
You ask in natural language — *"ask Grok for ideas on this"*, *"review this in GLM 5.2"*,
*"spec this in Kimi and Codex and merge the results"* — and the harness turns the ask into a
briefed dispatch to the right CLI at an appropriate model tier, then checks the result before
trusting it. There is no command syntax to learn and no re-authentication: each target CLI is
one you have already installed and authenticated.

The name: a *swingletree* is the pivoting crossbar in a draught harness that spreads one load
across more than one animal. Swingle spreads coding work across the agent CLIs you already
run. That buys two things your harness's own subagents cannot: another provider's frontier
model for a second opinion or an independent review, and delegation to a model whose tokens
come out of a different quota than the harness you are driving.

**Version:** 3.0.0 · [v2.0.0 release](https://github.com/hiivmind/swingle/releases/tag/v2.0.0) · config/state paths renamed `sdd-dispatch` → `swingle`: [docs/migration-3.0.0.md](docs/migration-3.0.0.md)

## Vocabulary

- **Harness** — the unit of dispatch: a coding-agent CLI (Claude Code, Codex, Antigravity,
  Grok, Pi, opencode). Distinct from both "provider" and "model".
- **Provider** — the billing entity behind a harness (Anthropic, OpenAI, Google, xAI, …).
- **Model** — the weights a harness runs, and the light/medium/heavy tier picked per task.

On-disk pack directories keep the historical name `providers/<id>/`; each pack describes one
harness.

## How a dispatch works

Every ask becomes a briefed subagent before the target CLI runs:

1. **Role** — implementer, reviewer, or explorer, inferred from the ask.
2. **Model tier** — matched to the task's difficulty and passed explicitly, never left to the
   CLI's default.
3. **Operating contract + instructions** — the target CLI receives a brief: what to do, what
   not to do, the context, the interfaces it touches.
4. **Return contract** — a fixed status vocabulary (`DONE`, `DONE_WITH_CONCERNS`,
   `NEEDS_CONTEXT`, `BLOCKED`) and a required report shape.
5. **Liveness + evidence gate** — the run is watched for stalls, and after a write-lane job
   the controller checks the working tree (staged + untracked + `HEAD`-unchanged) and re-runs
   the covering tests before committing.

A single named delegation runs end to end inside the `swingle-delegate` skill. Naming a model
or fanning out across several CLIs is composition by the driving harness: it routes a model
name to a CLI that serves it (there is no automatic model-to-CLI discovery inside
`swingle-delegate`; pin
the target with `via opencode`), or runs several dispatches and merges the results. Whatever
the harness picks is recorded in the ledger, so the run reproduces.

### What a dispatch returns

A returned report (an implementer job, trimmed):

```markdown
# Job 002 — grok pack self-smoke report

## What was implemented
End-to-end smoke of the `providers/grok` pack dispatch path...

## Files changed
| File | Action |
| --- | --- |
| `.swingle/delegate/002-smoke-marker.txt` | created |

No files outside `.swingle/delegate/` were modified. No git commit or push was
performed (implementer contract).

## Self-review
- Completeness: both brief requirements satisfied.
- Discipline: stayed in-repo; did not commit.

## Issues or concerns
None.
```

The ledger records every dispatch — role, harness, model, session id, and returned status:

```text
002 dispatched: provider=grok model=grok-4.5 attempt=1
002 session: attempt=1 019f8f64-8d1d-7db3-99f8-addae0933d63
002 complete: status=DONE outcome=answer-returned
model-attempt: job=002 phase=worker attempt=1 role=transcription-implementer provider=grok model=grok-4.5 class=scope outcome=ok
```

## Scope

Swingle is not an LLM router or a model-endpoint aggregator. A router hands you an endpoint
or a model, and you still author the harness around it — agent loop, tools, sandbox, file
edits, session resume, return contract. Swingle dispatches complete harnesses you have
already installed and authenticated, with their own scaffolding intact.

It is also distinct from a harness's built-in subagents, which run that harness's own model
inside its own loop. Swingle covers the case those cannot: dispatching to a different
harness — a different vendor's CLI, a different model — without leaving the one you are
driving.

## Requirements & install

- The **`superpowers`** plugin, if you use the `swingle-sdd` skill: `swingle-sdd` augments
  superpowers' own subagent-driven-development routines with external-CLI dispatch (see
  [Skills](#skills)).
- No superpowers for `swingle-delegate`: it handles direct, one-off interactions on its own.
- Whichever dispatch CLIs you use, on `PATH`: `claude`, `codex`, `opencode`, `agy`, `grok`,
  `pi` — each authenticated once. Auth modes, CI consequences, and seat economics:
  [docs/credentials.md](docs/credentials.md). An OAuth-only harness will not run in headless
  CI as-is; Claude and Grok also accept an API key and can.

**Harness support.** Two roles: a harness you **drive from** needs a controller adapter under
`skills/sdd/harnesses/`; a harness you **dispatch to** needs a pack under `providers/`. Each
pack is verified end-to-end against a specific CLI version; re-verify on a version bump with
`swingle-verify <id>`.

| Harness | CLI | Verified against | Drive from? | Dispatch to? |
| --- | --- | --- | --- | --- |
| Claude Code | `claude` | 2.1.218 | ✅ | ✅ |
| Codex | `codex` | 0.144.3 | ✅ | ✅ |
| opencode | `opencode` | 1.17.18 | ✅ | ✅ |
| Grok | `grok` | 0.2.111 | ✅ | ✅ |
| Pi | `pi` | 0.81.1 | ✅ | ✅ |
| Antigravity | `agy` | 1.1.5 | ✅ | ✅ |

Swingle's packs, contracts, and routing doctrine ship in this repository and are discovered
from the repo tree; no machine-specific paths are baked into the packs. The external pieces —
the `superpowers` plugin (for `swingle-sdd`) and each CLI's own auth — are called out where they
apply, not bundled here.

### Claude Code

```text
/plugin marketplace add hiivmind/swingle
/plugin install swingle@swingle-marketplace
```

(A local checkout works too: `/plugin marketplace add /path/to/swingle`.)

### Codex

This repository is also a Codex plugin (`.codex-plugin/plugin.json`) with a self-hosted
marketplace:

```bash
codex plugin marketplace add hiivmind/swingle
codex plugin add swingle@swingle-marketplace
```

Manual alternative and full details: [codex/INSTALL.md](codex/INSTALL.md). The Codex entry
point is `skills/sdd/SKILL.md`.

### opencode

opencode loads plugins as skills trees (it has no Claude Code plugin loader). The recommended
route generates version-pinned `skills.paths` from Claude Code's own install registry:

```bash
scripts/opencode-skills-path --merge ~/.config/opencode/opencode.json   # global
```

opencode's install has known pitfalls: a plugin-cache trap that silently loads mismatched
versions, two environment-variable caveats, and a `grep` verification step. They are
documented in [skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md); read it
before your first opencode dispatch. opencode registers skills under bare frontmatter names
with name-based dedupe; Swingle's skill names are all `swingle-`-prefixed, so they do not
collide with other skills' generic names on that harness.

After installing, run `swingle-setup` for a guided environment check.

## Skills

| Skill | Purpose |
| --- | --- |
| `swingle-sdd` | Execute an implementation plan through the active harness and harness packs |
| `swingle-delegate` | Directly dispatch an explicitly requested one-off job or homogeneous batch — no plan required |
| `swingle-setup` | Environment onboarding and health check — paths, config, registry, CLI auth, harness setup |
| `swingle-verify` | Re-run the CLI probe suite when versions bump or models release |

Skill names are `swingle-`-prefixed because several harnesses register skills in a flat,
first-wins namespace; the skills live in `skills/sdd/` and `skills/delegate/` on disk.

`swingle-sdd` wraps
[`superpowers:subagent-driven-development`](https://github.com/obra/superpowers) and requires
the superpowers plugin. Swingle supplies the external-CLI dispatch, packs, tiering, and
gates; SDD is the methodology it applies, maintained upstream. `swingle-delegate` is the
standalone path: it invokes no superpowers skill and has no `.superpowers/` dependency, which
is why one-line asks route through `swingle-delegate`, not `swingle-sdd`.

## Direct delegation

`swingle-delegate <task>` dispatches a self-contained job (or homogeneous batch) with the full pack
doctrine — role inference, model tiering, liveness, evidence gates, controller commits, and
session resume — without plan-execution machinery. Levers (`via <harness>`, `floor it` /
`play it safe`, `with review`, `read-only`, `supervised`) and the full lifecycle are in
[skills/delegate/SKILL.md](skills/delegate/SKILL.md). Artifacts and the ledger live in
`.swingle/delegate/`. The boundary is semantic: multi-task implementation plans go to
the `swingle-sdd` skill regardless of how they arrived; tasks below the triviality floor stay inline
unless delegation was explicitly requested.

## Safety & trust

Swingle spawns agentic CLIs that run tools, edit files, and execute commands, on task text a
model authored. The full threat model is [docs/safety.md](docs/safety.md); the essentials:

- The gates are not a sandbox. A dispatched agent reads, writes, and runs commands the way
  you can. `read-only` is an opt-in lane, not the default.
- Only `codex` and `grok` sandbox at the OS level. The rest rely on the gate plus your
  review.
- The evidence gates surface effects, not correctness. They show what an agent did (or
  didn't) so the controller can adjudicate; they do not prove the work is right.
- Prompt injection is a real surface. Review dispatched changes as you would a pull request
  from a stranger.

## Model tiering & economics

Each task is tiered: a cheap model for a review or trivial edit, the strongest for a hard
implementation. `floor it` (the cheapest model clearing each task's bar) is the default.
Model tables, override precedence, and `swingle-models`:
[docs/model-tiering.md](docs/model-tiering.md).

The tier→model tables ship in each provider pack, and dispatches resolve from those pack
defaults until you seed an override layer. To stand up the machine-wide registry, run
`swingle-setup` (or `scripts/swingle-models init --user` directly; no provider argument seeds
every shipped provider; pass an id for just one), then edit `~/.config/swingle/models/<id>.yaml`.
For a committable per-project table, `scripts/swingle-models init <id> --project <repo>` seeds
`.swingle/models/<id>.yaml`. `scripts/swingle-models which` shows which layer each
provider currently resolves from.

A measured token/cost delta on a real plan has not yet been published; measuring it is
tracked in [#17](https://github.com/hiivmind/swingle/issues/17). The handoff itself —
briefing, tiering, contract, evidence gate — does not depend on that number.

## Adding a harness pack

Routing is manifest-driven; adding a pack requires no edits to `core/`. Add one directory
under `providers/` satisfying the pack contract (`pack.md`, `models.yaml`, `models.md`,
`verification-log.md`) and run the validator that ships with the repo:

```bash
python3 scripts/validate-packs --root .
```

The manifest grammar, the `report-transport` field, and the enforcement invariants are in
[docs/pack-authoring.md](docs/pack-authoring.md).

## Reporting verification findings

The packs are living documents: CLIs change behavior between patch releases, models come and
go, and every live dispatch is evidence. Where a finding gets recorded depends on what you
can write to (full rules: `core/verification-protocol.md` §Recording and the `swingle-verify`
skill):

- writable checkout → append to the pack's `verification-log.md` and commit;
- clone but no push → commit locally and open an issue or PR;
- installed copy only →
  [open an issue](https://github.com/hiivmind/swingle/issues/new?template=verification-finding.md)
  using the **Verification finding** template.

Search existing issues first; 👍 an equivalent issue rather than filing a duplicate. A
finding recorded only in an installed cache is invisible upstream.

## Subscription seats

Swingle's economics work best driving CLIs you already run under flat-rate subscription seats
rather than metered API keys. Note that unattended use can approach some providers'
acceptable-use limits. The framing, the API-key degradation route, and what happens when a
seat hits its cap: [docs/credentials.md](docs/credentials.md).

## Layout

```
skills/sdd/                       # plan-execution skill and harness adapters
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
skills/swingle-verify/            # CLI re-verification skill
core/                             # shared doctrine, playbook, roles, and logs
providers/<id>/                   # self-contained harness packs
contracts/                        # implementer, task-reviewer, design-reviewer, reader contracts
docs/                             # user reference (safety, pack-authoring, model-tiering, credentials) + migration guides + hero image
codex/INSTALL.md                  # Codex installation instructions
scripts/validate-packs            # pack validator, resolver, and link/anchor check
scripts/codex-smoke               # Codex layout and validator smoke test
scripts/opencode-skills-path      # opencode skills.paths from installed Claude Code plugins
archive/                          # superseded v1.x pack snapshots (historical)
references/                       # cross-harness reference material
```
