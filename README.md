<p align="center">
  <img src="docs/images/hero-banner.svg" alt="Swingle — share the load; don't switch coding harnesses to switch models" width="100%">
</p>

# Swingle

**Share the load.**
Don't switch coding harnesses to switch models.

You already drive a coding-agent harness — Claude Code, Codex, Grok, opencode, or Pi.
Swingle lets you **stay in it** and reach any of the six supported CLIs you have installed
— Antigravity included — in a sentence:

> *"ask Grok for ideas on this."*
> *"review this in GLM 5.2."*
> *"spec this in Kimi and Codex — blend their best ideas."*

You don't leave your harness, learn another CLI, or re-auth mid-thought. You say what you
want; the harness you're driving interprets it and dispatches the right target at the
right model tier, then brings back checked, structured work — or tells you plainly when a
job is blocked. The one-line ask is the surface — the **handoff** underneath is where the
value is (next section).


## Why "Swingle"?
A *swingletree* is the pivoting crossbar in a draught harness that equalises pull between
animals of unequal strength — hitch a shire and a pony to one load and the bar rotates so
neither is over-pulled. That is what Swingle does with coding work: share the load across
the harnesses you already run.

**Version:** 2.0.0

## The delegation handoff

The magic isn't "type a sentence." It's what Swingle does with that sentence before the
other CLI ever sees it. One ask is turned into a **briefed subagent**:

1. **Role** — is this an implementer, a reviewer, an explorer? Inferred from the ask.
2. **Model tier** — cheap model for a light task, the strongest for a hard one; matched to
   the job, passed explicitly (never left to default).
3. **Operating contract + instructions** — the target CLI is handed a real brief: what to
   do, what *not* to do, the scene, the interfaces it touches.
4. **Return contract** — a required status vocabulary and report shape, so the answer comes
   back structured — or as an explicit *blocked* / *needs-context* status you can act on —
   not a wall of chat. (A job can come back needing more from you; the contract makes that
   legible instead of silent.)
5. **Liveness + evidence gate** — the run is watched for stalls, and the result is checked
   against what actually landed (staged + untracked + `HEAD`-unchanged) before it's trusted.

So *"ask Antigravity to produce a logo based on the principles in our README"* isn't a
prompt forwarded to an endpoint — it's a briefed job with a tier, a contract, and a
checked return. The convenience of "just ask" is the doorway; the briefed, contract-bound,
tiered handoff is the room.

### How you actually drive it

You talk to the harness you're already in; *it* interprets the ask and issues the
dispatches. Real asks, and what each one does:

| You say | What happens |
| --- | --- |
| *"ask Grok for ideas on this"* | One delegation to a named **harness**; Grok is briefed and returns structured ideas. |
| *"review this in GLM 5.2"* | Name a **model**; your driving harness routes to a CLI that serves it — GLM 5.2 is offered by both opencode and Pi, so it picks one (or asks), and you can pin it with `via opencode`. Model-level selection, not just harness-level. (Routing is your driving harness interpreting the ask; there's no automatic model-to-CLI discovery inside `delegate`.) |
| *"spec this in Kimi and Codex — blend their best ideas"* | The driving harness runs the two as separate `delegate` dispatches — concurrently where the lane allows it — then synthesises the results itself. There's no single "blend" primitive; it's your driving harness composing dispatches (exactly how this project's own logo concepts were produced). |

The surface is natural language; the routing, tiering, briefing, and — for a fan-out — the
synthesis are done by the harness you're driving, on your behalf.

## What Swingle is not

Swingle is not an LLM router or a model-endpoint aggregator. Those hand you an **endpoint
or a model** — you still have to author the harness around it: the agent loop, tools,
sandbox, file edits, session resume, the return contract. Swingle dispatches **whole
harnesses you have already installed and authenticated**, scaffolding intact.

It is also not "yet another subagent system." Your harness already has its own subagents —
but they run *its* model, inside *its* loop. Swingle's job is the case those can't cover:
reaching a *different* harness (a different vendor's CLI, a different model) without leaving
the one you're driving. Keep using in-harness subagents for same-harness work; reach for
Swingle when the best tool for a task lives in another CLI.

## Vocabulary

Used consistently throughout, because the distinction is the whole point:

- **Harness** — the unit of dispatch: a coding-agent CLI (Claude Code, Codex, Antigravity,
  Grok, Pi, opencode). *Not* a "provider" and *not* a "model".
- **Provider** — the billing entity behind a harness (Anthropic, OpenAI, Google, xAI, …).
- **Model** — the weights a harness runs (and the light/medium/heavy tier you pick per task).

On-disk pack directories keep the historical name `providers/<id>/`; each pack describes one
harness.

## Requirements & install

**Dependencies, stated plainly:**

- The **`superpowers`** plugin (the `sdd` skill wraps `superpowers:subagent-driven-development`
  — see [Skills](#skills)). `delegate` does not need it.
- Whichever dispatch CLIs you use, on `PATH`: `claude`, `codex`, `opencode`, `agy`, `grok`,
  `pi` — **each authenticated once.** Most use interactive OAuth; some also accept an API
  key (Claude via `ANTHROPIC_API_KEY`, Grok via `XAI_API_KEY`).
- **Consequence for CI — depends on the harness.** An OAuth-only harness needs a
  human-seeded credential store, so it doesn't run in headless CI or ephemeral runners
  as-is; an API-key-capable harness (Claude, Grok) can, with the key as a CI secret. Check
  which mode the harnesses you depend on use before wiring them into a pipeline.

**Harness support.** Two roles: a harness you **drive from** needs a controller adapter
under `skills/sdd/harnesses/` (five have one); a harness you **dispatch to** needs a pack
under `providers/` (six have one). Antigravity is a dispatch target today, not yet a
driver. Each pack is verified end-to-end against a specific CLI version; re-verify on a bump
with `swingle-verify <id>`.

| Harness | CLI | Verified against | Drive from? | Dispatch to? |
| --- | --- | --- | --- | --- |
| Claude Code | `claude` | 2.1.218 | ✅ | ✅ |
| Codex | `codex` | 0.144.3 | ✅ | ✅ |
| opencode | `opencode` | 1.17.18 | ✅ | ✅ |
| Grok | `grok` | 0.2.111 | ✅ | ✅ |
| Pi | `pi` | 0.81.1 | ✅ | ✅ |
| Antigravity | `agy` | 1.1.5 | — | ✅ |

Swingle's own packs, contracts, and routing doctrine ship **in this repository** — the
`sdd` / `delegate` / `swingle-verify` skills and harness packs are discovered from the repo
tree, with no machine-specific paths baked into the packs. The external pieces it leans on
— the `superpowers` plugin (for `sdd`) and each CLI's own auth — are called out where they
apply, not bundled here.

### Claude Code

```text
/plugin marketplace add discreteds/swingle
/plugin install swingle@swingle-marketplace
```

(A local checkout works too: `/plugin marketplace add /path/to/swingle`.)

### Codex

This repository is also a Codex plugin (`.codex-plugin/plugin.json`) with a self-hosted
marketplace:

```bash
codex plugin marketplace add discreteds/swingle
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
versions, two environment-variable caveats, and a `grep` verification step). Rather than
reproduce 600 words here, they live where they're maintained:
[skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md). Read it before your
first opencode dispatch.

## Skills

| Skill | Purpose |
| --- | --- |
| `sdd` | Execute an implementation plan through the active harness and harness packs |
| `delegate` | Directly dispatch an explicitly requested one-off job or homogeneous batch — no plan required |
| `swingle-verify` | Re-run the CLI probe suite when versions bump or models release |

**Credit where it's due.** `sdd` **rides along with
[`superpowers:subagent-driven-development`](https://github.com/obra/superpowers)** — it wraps
that methodology and depends on the superpowers plugin being installed. Swingle is the
product (external-CLI dispatch, packs, tiering, gates); SDD is the method it applies, and it
isn't ours.

`delegate` is the standalone path: it works **more directly and requires no superpowers** —
no superpowers skill invoked, no `.superpowers/` dependency. That's why the one-line asks
above route through `delegate`, not `sdd`.

## Direct delegation

`delegate <task>` dispatches a self-contained job (or homogeneous batch) with the full pack
doctrine — role inference from `core/roles.md`, model tiering, liveness, evidence gates
(staged + untracked + `HEAD`-unchanged), controller commits, and session resume — but none
of the plan-execution ceremony. Levers: `via <harness>`, `floor it` / `play it safe` /
explicit model, `with review`, `read-only`, `supervised` / `unsupervised`. Jobs whose
planned worker + reviewer dispatches total ≥3 (counted after batching) run supervised
automatically (announced). Artifacts and the lifecycle
ledger live in `.sdd-dispatch/delegate/`, ignored via `.git/info/exclude`
(`.sdd-dispatch/models/` is committable project config). The boundary is semantic: multi-task
implementation plans go to the `sdd` skill regardless of how they arrived; tasks below the
triviality floor stay inline unless delegation was explicitly requested.

## Safety & trust

Swingle spawns agentic CLIs that run tools, edit files, and execute commands, on **task text
a model authored**. Be clear-eyed about what that means.

- **What the evidence gates do.** After a *write-lane* dispatch the controller inspects the
  working tree (staged + untracked + `HEAD`-unchanged) and re-runs the covering tests itself
  before trusting a result and committing; *read-lane* work is judged on the report it
  returns. The gates **surface evidence** — an agent that did nothing, left a bad diff, or
  touched state it shouldn't — so the controller can adjudicate and commit. They do not
  *prove* the work is semantically correct (incomplete tests can't). Agents are contracted
  not to commit, and a stray agent commit is surfaced as a violation, not absorbed.
- **What they do not do.** They are not a sandbox. A dispatched agent can, within its run,
  read and write files and run commands the way you can. `read-only` is an *opt-in* lane, not
  the default. Two harnesses (`codex`, `grok`) provide an OS-enforced sandbox; the rest rely
  on the gate + your review.
- **Prompt injection is a real surface.** A dispatched agent reads repository content you
  point it at; hostile content there can try to steer it. The gates catch *effects* (bad
  diffs, failed tests), not *intent* — review dispatched changes as you would a pull request
  from a stranger.
- **Manifest injection is closed** — every manifest value is validator-enforced, `*-argv`
  arrays are data (`argv[0]` must equal `cli`, shell metacharacters rejected), so a pack
  cannot smuggle in a command to execute. That's a narrow, deliberately-closed surface; it is
  not the whole threat model, which is the bullet points above.

## Model tiering & economics

Tier the model to each task: a cheap model for a review or a trivial edit, the strongest for
a hard implementation — instead of paying premium rates on everything. That's the economic
idea, and it's why "floor it" (cheapest model clearing each bar) is the default.

**Honesty note:** we have not yet published a *measured* token/cost delta on a real plan.
That number can't be asserted — it has to be measured — and it's tracked in
[#17](https://github.com/discreteds/swingle/issues/17). Until it lands, treat tiering as a
sound design principle, not a proven savings figure. The convenience — never leaving your
harness — is the benefit that stands today.

### Model tables and overrides

Each pack ships its model priority table in `providers/<id>/models.yaml` (restricted YAML:
flat header + `tier/lane/priority/model/status[/pricing/rationale]` rows). At dispatch time
the table is resolved per harness, first file found wins whole-file (no merging):

1. `$SDD_DISPATCH_MODELS/<id>.yaml` (env override — a directory)
2. `<project>/.sdd-dispatch/models/<id>.yaml` (committable, team-shared)
3. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` (this machine)
4. the pack default

Seed an override with `scripts/sdd-models init <id> --project <repo>|--user`; inspect with
`scripts/sdd-models which`. Override statuses are your own assertion — the `verified` stamps
in pack defaults come from live dispatch evidence only. A malformed override is a hard error,
never a silent fall-through; an override that omits a (tier, lane) slot resolves that slot to
"no eligible model — ask", the supported way to keep a harness from auto-routing in one
project.

## Adding a harness pack

The strong, testable claim first: **adding a pack requires zero edits to `core/`; routing is
manifest-driven**, and the validator that proves it ships with the repo. Add one directory
under `providers/` satisfying the pack contract — `pack.md`, `models.yaml` (the model table
of record), `models.md` (documentary narrative), and `verification-log.md` — then run:

```bash
python3 scripts/validate-packs --root .
```

The manifest is the YAML front matter of `pack.md`. Required: `schema-version`, `id`, `cli`,
`verified-version`, `version-argv`, `resume-argv`, `session-source`, `stall-signal`,
`sandbox`. Optional: `fork-flag`, `session-list-argv`, `readiness-argv`,
`readiness-timeout-seconds`, and:

| Field | Values | Meaning |
| --- | --- | --- |
| `report-transport` | `report-file` (default) · `captured-output` | How an agent's report gets back to the controller |
| `list-models-argv` | argv array | How to enumerate an open-catalog harness's live model list (e.g. pi). Surfaced by `sdd-models init`, never auto-executed |

Declare `captured-output` when the CLI cannot reliably write an agent-authored file to a
workspace path. The skills then ask for **no file** and take the full report as the captured
final message, saving it themselves. Getting this wrong is not cosmetic: on such a harness a
report-file request fails *intermittently* while the exit code stays 0, so the report is
silently missing and any reviewer downstream loses an input. `agy` is `captured-output`;
`claude`, `codex`, `opencode`, `grok`, and `pi` are `report-file`.

Every value is validator-enforced, and `*-argv` arrays are data — `argv[0]` must equal `cli`,
and shell metacharacters are rejected.

## Reporting verification findings

The packs are living documents: CLIs flip behavior between patch releases, models come and go,
and every live dispatch is evidence. Where a finding gets recorded depends on what you can
write to (the **recording ladder** — full rules in `core/verification-protocol.md` §Recording
and the `swingle-verify` skill, step 0):

1. **Writable source checkout** — append to the pack's `verification-log.md`, update the pack
   facts, and commit. Never record into an installed plugin cache (Claude Code
   `~/.claude/plugins/cache/...`, Codex `~/.codex/plugins/cache/...`) — caches are clobbered on
   the next upgrade.
2. **Clone but no push rights** — commit locally and open an issue or PR carrying the log entry.
3. **No source tree** (installed copy only) — [open an issue](https://github.com/discreteds/swingle/issues/new?template=verification-finding.md)
   using the **Verification finding** template (`verification` label), one issue per independent
   finding: CLI + plugin version, trigger, the pack assertion under test, verdict, verbatim
   evidence, impact. **Search first**: if an equivalent issue exists, a 👍 reaction adds weight
   to its prioritisation; comment only when you bring a new angle not already covered.

A finding recorded only in an installed cache is a finding lost.

## A note on subscription seats

Swingle's economics work best when it drives CLIs you already run under **flat-rate
subscription seats** rather than metered API keys. Two honest caveats:

- **Framing.** This is *orchestration* — driving tools you already run interactively — not
  *arbitrage*. Unattended, programmatic use of consumer subscription seats can sit near the
  line in some providers' acceptable-use terms; check yours.
- **Degradation.** If a provider closes seat-based CLI use, the harnesses whose CLI also
  accepts an API key keep working — authenticate that way instead (Claude via
  `ANTHROPIC_API_KEY`, Grok via `XAI_API_KEY`, or any other API-key mode a CLI offers). The
  credential lives in the CLI's own auth, not the pack; `models.yaml` only picks *which*
  model. Harnesses with no API-key mode lose that route — so the fallback is real where an
  API path exists, not universal.

## Layout

```
skills/sdd/                       # plan-execution skill and harness adapters
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
skills/swingle-verify/            # CLI re-verification skill
core/                             # shared doctrine, playbook, roles, and logs
providers/<id>/                   # self-contained harness packs
contracts/                        # implementer, task-reviewer, design-reviewer, reader contracts
codex/INSTALL.md                  # Codex installation instructions
scripts/validate-packs            # pack validator and resolver
scripts/codex-smoke               # Codex layout and validator smoke test
scripts/opencode-skills-path      # opencode skills.paths from installed Claude Code plugins
```
