<p align="center">
  <img src="docs/images/hero-banner.svg" alt="Swingle — share the load; don't switch coding harnesses to switch models" width="100%">
</p>

# Swingle

**Share the load.**
Don't switch coding harnesses to switch models.

You already drive a coding-agent harness. Swingle lets you **stay in it** and reach the other
CLIs you have installed, in a sentence:

> *"ask Grok for ideas on this."*
> *"review this in GLM 5.2."*
> *"spec this in Kimi and Codex — blend their best ideas."*

You don't leave your harness, learn another CLI, or re-auth mid-thought. You say what you
want; the harness you're driving briefs the right tool at the right model tier and brings back
checked, structured work. The one-line ask is the surface; the **handoff** underneath is where
the value is.

**Version:** 2.0.2 · [v2.0.0 release](https://github.com/hiivmind/swingle/releases/tag/v2.0.0)

## Why "Swingle"?

A *swingletree* is the pivoting crossbar in a draught harness that spreads one load across
more than one animal without over-pulling any single one. That is what Swingle does with
coding work: spread it across the harnesses you already run, sending each task to the right
one instead of overloading a single premium model.

## The delegation handoff

One ask is turned into a **briefed subagent** before the other CLI ever sees it:

1. **Role** — is this an implementer, a reviewer, an explorer? Inferred from the ask.
2. **Model tier** — cheap model for a light task, the strongest for a hard one; matched to
   the job, passed explicitly (never left to default).
3. **Operating contract + instructions** — the target CLI is handed a real brief: what to do,
   what *not* to do, the scene, the interfaces it touches.
4. **Return contract** — a required status vocabulary and report shape, so the answer comes
   back structured — or as an explicit *blocked* / *needs-context* status you can act on — not
   a wall of chat.
5. **Liveness + evidence gate** — the run is watched for stalls, and the result is checked
   against what actually landed (staged + untracked + `HEAD`-unchanged) before it's trusted.

The convenience of "just ask" is the doorway; the briefed, contract-bound, tiered handoff is
the room. [What a dispatch returns](#what-a-dispatch-returns) shows a real one.

### How you actually drive it

There's no command syntax and no fixed menu of phrases to learn. You describe what you want
in natural language, in the flow of whatever you're already doing, and your harness handles
the dispatch. The asks throughout this README are **examples**, not an interface — they only
sketch the range:

- name a harness — *"ask Grok for ideas on this"*
- name a model — *"review this in GLM 5.2"*
- fan out and blend — *"spec this in Kimi and Codex, then merge the best of each"*
- or just describe the outcome and let your harness choose the tool and tier.

Underneath, every ask becomes the same briefed handoff. A single named delegation Swingle
runs end to end; naming a model or fanning out is your **driving harness** composing
dispatches on top — routing a model name to a CLI that serves it (there's no automatic
model-to-CLI discovery inside `delegate`, and you can always pin it with `via opencode`), or
running several dispatches and synthesising them. Whatever your harness picks is recorded in
the ledger, so the run reproduces. (The fan-out is exactly how this project's own logo
concepts were produced — see below.)

## What a dispatch returns

Swingle brings back checked, structured work — not a wall of chat. Here is a real one.

**A returned report** (an implementer job, trimmed):

```markdown
# Job 002 — grok pack self-smoke report

## What was implemented
End-to-end smoke of the `providers/grok` pack dispatch path...

## Files changed
| File | Action |
| --- | --- |
| `.sdd-dispatch/delegate/002-smoke-marker.txt` | created |

No files outside `.sdd-dispatch/delegate/` were modified. No git commit or push was
performed (implementer contract).

## Self-review
- Completeness: both brief requirements satisfied.
- Discipline: stayed in-repo; did not commit.

## Issues or concerns
None.
```

**The ledger** records every dispatch — role, harness, model, session id, and the returned
status — so a run reproduces and the model-to-CLI pick is never a guess:

```text
002 dispatched: provider=grok model=grok-4.5 attempt=1
002 session: attempt=1 019f8f64-8d1d-7db3-99f8-addae0933d63
002 complete: status=DONE outcome=answer-returned
model-attempt: job=002 phase=worker attempt=1 role=transcription-implementer provider=grok model=grok-4.5 class=scope outcome=ok
```

**The return-contract statuses** are a fixed vocabulary — `DONE`, `DONE_WITH_CONCERNS`,
`NEEDS_CONTEXT`, `BLOCKED` — so a job that needs more from you comes back legible, not silent.

**The evidence gate** is what stands between a returned status and a trusted commit: after a
write-lane job the controller checks the working tree (staged + untracked + `HEAD`-unchanged)
and re-runs the covering tests itself before committing.

*This README's own hero banner* was produced this way: jobs `005` (agy) and `006` (grok) each
dispatched two SVG concepts, which were then iterated and merged — a real fan-out-and-blend
run, recorded in `.sdd-dispatch/delegate/`.

## What Swingle is not

Swingle is not an LLM router or a model-endpoint aggregator. Those hand you an **endpoint or a
model** — you still have to author the harness around it: the agent loop, tools, sandbox, file
edits, session resume, the return contract. Swingle dispatches **whole harnesses you have
already installed and authenticated**, scaffolding intact.

It is also not "yet another subagent system." Your harness already has its own subagents — but
they run *its* model, inside *its* loop. Swingle's job is the case those can't cover: reaching
a *different* harness (a different vendor's CLI, a different model) without leaving the one
you're driving. Keep using in-harness subagents for same-harness work; reach for Swingle when
the best tool for a task lives in another CLI.

## Vocabulary

Used consistently throughout, because the distinction is the whole point:

- **Harness** — the unit of dispatch: a coding-agent CLI (Claude Code, Codex, Antigravity,
  Grok, Pi, opencode). *Not* a "provider" and *not* a "model".
- **Provider** — the billing entity behind a harness (Anthropic, OpenAI, Google, xAI, …).
- **Model** — the weights a harness runs (and the light/medium/heavy tier you pick per task).

On-disk pack directories keep the historical name `providers/<id>/`; each pack describes one
harness.

## Requirements & install

- The **`superpowers`** plugin (the `sdd` skill wraps `superpowers:subagent-driven-development`
  — see [Skills](#skills)). `delegate` does not need it.
- Whichever dispatch CLIs you use, on `PATH`: `claude`, `codex`, `opencode`, `agy`, `grok`,
  `pi` — each authenticated once. Auth mode, CI consequences, and seat economics:
  [docs/credentials.md](docs/credentials.md). The short version: an OAuth-only harness won't
  run in headless CI as-is; Claude and Grok also accept an API key and can.

**Harness support.** Two roles: a harness you **drive from** needs a controller adapter under
`skills/sdd/harnesses/` (five have one); a harness you **dispatch to** needs a pack under
`providers/` (six have one). Antigravity is a dispatch target today, not yet a driver. Each
pack is verified end-to-end against a specific CLI version; re-verify on a bump with
`swingle-verify <id>`.

| Harness | CLI | Verified against | Drive from? | Dispatch to? |
| --- | --- | --- | --- | --- |
| Claude Code | `claude` | 2.1.218 | ✅ | ✅ |
| Codex | `codex` | 0.144.3 | ✅ | ✅ |
| opencode | `opencode` | 1.17.18 | ✅ | ✅ |
| Grok | `grok` | 0.2.111 | ✅ | ✅ |
| Pi | `pi` | 0.81.1 | ✅ | ✅ |
| Antigravity | `agy` | 1.1.5 | — | ✅ |

Swingle's own packs, contracts, and routing doctrine ship **in this repository**, discovered
from the repo tree with no machine-specific paths baked into the packs. The external pieces it
leans on — the `superpowers` plugin (for `sdd`) and each CLI's own auth — are called out where
they apply, not bundled here.

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

opencode loads plugins as **skills trees** (it has no Claude Code plugin loader). The
recommended route generates version-pinned `skills.paths` from Claude Code's own install
registry:

```bash
scripts/opencode-skills-path --merge ~/.config/opencode/opencode.json   # global
```

opencode's install has real footguns (a plugin-cache trap that silently loads mismatched
versions, two environment-variable caveats, and a `grep` verification step). They live where
they're maintained: [skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md). Read
it before your first opencode dispatch. Note that opencode registers skills under bare
frontmatter names with name-based dedupe, so `delegate` is a global name on that harness — if
you maintain another `delegate` skill, expect a collision (tracked for a `swingle-delegate`
alias).

## Skills

| Skill | Purpose |
| --- | --- |
| `sdd` | Execute an implementation plan through the active harness and harness packs |
| `delegate` | Directly dispatch an explicitly requested one-off job or homogeneous batch — no plan required |
| `swingle-verify` | Re-run the CLI probe suite when versions bump or models release |

`sdd` **rides along with
[`superpowers:subagent-driven-development`](https://github.com/obra/superpowers)** — it wraps
that methodology and depends on the superpowers plugin being installed. Swingle is the product
(external-CLI dispatch, packs, tiering, gates); SDD is the method it applies, and it isn't
ours. `delegate` is the standalone path: it works more directly and requires no superpowers —
no superpowers skill invoked, no `.superpowers/` dependency — which is why the one-line asks
above route through `delegate`, not `sdd`.

## Direct delegation

`delegate <task>` dispatches a self-contained job (or homogeneous batch) with the full pack
doctrine — role inference, model tiering, liveness, evidence gates, controller commits, and
session resume — but none of the plan-execution ceremony. Levers (`via <harness>`, `floor it`
/ `play it safe`, `with review`, `read-only`, `supervised`) and the full lifecycle are in
[skills/delegate/SKILL.md](skills/delegate/SKILL.md). Artifacts and the ledger live in
`.sdd-dispatch/delegate/`. The boundary is semantic: multi-task implementation plans go to the
`sdd` skill regardless of how they arrived; tasks below the triviality floor stay inline unless
delegation was explicitly requested.

## Safety & trust

Swingle spawns agentic CLIs that run tools, edit files, and execute commands, on task text a
model authored. Before you install, know these four things — the full threat model is
[docs/safety.md](docs/safety.md):

- **The gates are not a sandbox.** A dispatched agent reads, writes, and runs commands the way
  you can. `read-only` is an opt-in lane, not the default.
- **Only `codex` and `grok` sandbox at the OS level.** The rest rely on the gate plus your
  review.
- **The evidence gates surface effects, not correctness.** They show what an agent did (or
  didn't) so the controller can adjudicate; they don't prove the work is right.
- **Prompt injection is a real surface.** Review dispatched changes as you would a pull request
  from a stranger.

## Model tiering & economics

Tier the model to each task — a cheap model for a review or trivial edit, the strongest for a
hard implementation — instead of paying premium rates on everything. That's why `floor it`
(cheapest model clearing each bar) is the default. Model tables, override precedence, and
`sdd-models`: [docs/model-tiering.md](docs/model-tiering.md).

What stands today is the handoff itself — the briefing, tiering, contract, and evidence gate
above — which you get whether or not a cost delta is ever measured. Tiering's *savings* are the
part awaiting a number: a measured token/cost delta on a real plan hasn't been published, it
has to be measured, and it's tracked in [#17](https://github.com/hiivmind/swingle/issues/17).

## Adding a harness pack

**Adding a pack requires zero edits to `core/`; routing is manifest-driven**, and the
validator that proves it ships with the repo. Add one directory under `providers/` satisfying
the pack contract (`pack.md`, `models.yaml`, `models.md`, `verification-log.md`) and run:

```bash
python3 scripts/validate-packs --root .
```

The manifest grammar, the `report-transport` field, and the enforcement invariants are in
[docs/pack-authoring.md](docs/pack-authoring.md).

## Reporting verification findings

The packs are living documents: CLIs flip behavior between patch releases, models come and go,
and every live dispatch is evidence. Where a finding gets recorded depends on what you can
write to — the **recording ladder**, full rules in `core/verification-protocol.md` §Recording
and the `swingle-verify` skill: writable checkout → append to the pack's `verification-log.md`
and commit; clone but no push → commit locally and open an issue or PR; installed copy only →
[open an issue](https://github.com/hiivmind/swingle/issues/new?template=verification-finding.md)
using the **Verification finding** template. Search first: an equivalent issue gets a 👍, not a
duplicate. A finding recorded only in an installed cache is a finding lost.

## Subscription seats

Swingle's economics work best driving CLIs you already run under **flat-rate subscription
seats** rather than metered API keys — but that's *orchestration*, not *arbitrage*, and
unattended use can sit near some providers' acceptable-use line. The framing, the API-key
degradation route, and what happens when a seat hits its cap:
[docs/credentials.md](docs/credentials.md).

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
