<p align="center">
  <img src="docs/images/hero-banner.svg" alt="Swingle" width="100%">
</p>

# Swingle

Swingle lets the coding-agent harness you are already driving — Claude Code, Codex,
opencode, Grok, Pi, or Antigravity — dispatch work to the other agent CLIs installed on the
same machine. You ask in natural language — *"ask Grok for ideas on this"*, *"review this in
GLM 5.2"*, *"spec this in Kimi and Codex and merge the results"* — and the harness turns the
ask into a briefed dispatch to the right CLI at an appropriate model tier, then checks the
result before trusting it. No command syntax to learn, no re-authentication: every target is
a CLI you already installed and signed into.

**The symmetry is the point.** Any of the six harnesses can drive, and any of the six can be
dispatched to — all thirty-six pairings run through the same provider packs, the same
contracts, and the same gates.

**Version:** 3.1.3 · [v2.0.0 release](https://github.com/hiivmind/swingle/releases/tag/v2.0.0) · config/state paths renamed `sdd-dispatch` → `swingle`: [docs/migration-3.0.0.md](docs/migration-3.0.0.md)

## Why "Swingle"

On a horse-drawn carriage, the *swingletree* is the pivoting crossbar between the carriage
and the harness that spreads the weight of one load across a whole team of animals. Swingle
does the same for coding work: one harness holds the reins,
and the load is spread across the agent CLIs you already run. That buys two things your
harness's own subagents cannot:

- **Another provider's frontier model** — a genuinely independent second opinion or review,
  from weights your harness cannot run.
- **A different quota** — delegated work burns the target CLI's subscription tokens, not the
  budget of the session you are driving.

Swingle is not an LLM router or model-endpoint aggregator. A router hands you an endpoint,
and you still author the harness around it — agent loop, tools, sandbox, session resume.
Swingle dispatches complete harnesses you have already installed and authenticated, with
their own scaffolding intact. And it is distinct from built-in subagents, which run their
own harness's model inside its own loop: Swingle covers exactly the case those cannot — a
different vendor's CLI, a different model, without leaving the harness you are driving.

## Install

Swingle installs on **six supported harnesses**. Pick yours, run the commands, then finish with
the [post-install step](#after-installing-run-the-swingle-setup-skill) — it is the same on every
harness.

### Claude Code

```text
/plugin marketplace add hiivmind/swingle
/plugin install swingle@swingle-marketplace
```

A local checkout works too: `/plugin marketplace add /path/to/swingle`.

### Codex

```bash
codex plugin marketplace add hiivmind/swingle
codex plugin add swingle@swingle-marketplace
```

Manual alternative and details: [codex/INSTALL.md](codex/INSTALL.md).

### opencode

```bash
scripts/opencode-skills-path --merge ~/.config/opencode/opencode.json   # global
```

Generates version-pinned `skills.paths` from Claude Code's plugin registry. opencode has
known install pitfalls (a plugin-cache trap, two env-var caveats) — read
[skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md) before your first
dispatch.

### Pi

```bash
pi install https://github.com/hiivmind/swingle
```

Pi clones the repository as a package and discovers `skills/` automatically. Details:
[skills/sdd/harnesses/pi.md](skills/sdd/harnesses/pi.md).

### Grok

Grok discovers Claude-compatible plugins and skills: install via the Claude Code route
above, or point Grok at a checkout. Details:
[skills/sdd/harnesses/grok.md](skills/sdd/harnesses/grok.md).

### Antigravity

```bash
agy plugin install http://github.com/hiivmind/swingle
```

Then add a one-time `command(<cli>)` permission rule for each CLI you will dispatch to
(a missing rule silently no-ops the dispatch). Details:
[skills/sdd/harnesses/agy.md](skills/sdd/harnesses/agy.md).

### After installing: run the `swingle-setup` skill

Whichever harness you installed on, the post-install step is the same: open a session and
run the `swingle-setup` skill — `/swingle-setup`, or just ask (*"set up swingle"*, *"check
my swingle install"*). It never runs automatically, so this is the one step the install
commands above don't cover.

**What it does.** Setup starts with a read-only health check of the whole dispatch
environment: it validates the installed packs, then for each target CLI checks presence on
`PATH`, installed version against the verified version, and authentication readiness, and
it discovers your configuration layers and any pre-3.0 `sdd-dispatch` residue. It reports
everything as a status table, then offers fixes **one at a time, each requiring your
explicit consent** — it never writes anything uninvited, never commits, and never touches
project-tracked files.

**Why run it.** Dispatch works without setup — the dispatch skills are self-sufficient —
but setup is how you catch a CLI that isn't authenticated yet, version drift against the
verified pairings (handed off to `swingle-verify`), a malformed config file, or an
unmigrated pre-3.0 layout, before your first dispatch fails on one of them.

It is also how you set up customization. Setup seeds the model-registry override layers —
your own copy of a pack's tier → model table, at the user or project layer — and confirms
the seeded layer actually wins the resolution walk; edit the seeded file's rows to remap
which model serves each tier ([docs/model-tiering.md](docs/model-tiering.md)). It likewise
scaffolds the config file and walks you through its keys: disabling providers, setting a
default, per-lane routing ([docs/config.md](docs/config.md)). Re-seeding over a customized
file always requires an explicit, per-item confirmation.

**Where the files it changes live.** Every write is outside your project's tracked files:

| File | Purpose |
| --- | --- |
| `${XDG_CONFIG_HOME:-~/.config}/swingle/config.json` | user-level config (provider disable/default, lanes) |
| `${XDG_CONFIG_HOME:-~/.config}/swingle/models/<id>.yaml` | machine-wide model-registry overrides |
| `<project>/.swingle.json` | project config — scaffolded for **you** to commit |
| `<project>/.swingle/models/<id>.yaml` | project model overrides — scaffolded for **you** to commit |
| provider settings files | pack-documented baselines (e.g. persisted permissions), always outside the repo |

`XDG_CONFIG_HOME` is usually unset, so in practice the user-level paths are under
`~/.config/swingle/`. Re-running is always safe: on a healthy environment setup is purely
a status report.

### Prerequisites

- **Target CLIs on `PATH`, each authenticated once** — whichever of `claude`, `codex`,
  `opencode`, `agy`, `grok`, `pi` you want to dispatch to. Auth modes and headless-CI
  consequences: [docs/credentials.md](docs/credentials.md).
- **The [superpowers](https://github.com/obra/superpowers) plugin — only for `swingle-sdd`**
  (it wraps superpowers' subagent-driven-development). `swingle-delegate` needs nothing
  beyond this repo.

### Verified pairings

Every pack is verified end-to-end against a specific CLI version; re-verify on a version
bump with the `swingle-verify` skill.

| Harness | CLI | Verified against | Drive from? | Dispatch to? |
| --- | --- | --- | --- | --- |
| Claude Code | `claude` | 2.1.218 | ✅ | ✅ |
| Codex | `codex` | 0.144.3 | ✅ | ✅ |
| opencode | `opencode` | 1.18.9 | ✅ | ✅ |
| Grok | `grok` | 0.2.111 | ✅ | ✅ |
| Pi | `pi` | 0.81.1 | ✅ | ✅ |
| Antigravity | `agy` | 1.1.5 | ✅ | ✅ |

## The four skills

| Skill | Use it when | Example ask |
| --- | --- | --- |
| `swingle-delegate` | A one-off job or homogeneous batch, no plan | *"review this diff in GLM 5.2 via opencode"* |
| `swingle-sdd` | Executing a written multi-task implementation plan | *"run this plan with SDD"* |
| `swingle-setup` | Onboarding: paths, config, registry, CLI auth | *"run swingle-setup"* |
| `swingle-verify` | A CLI version bumped or a model released | *"swingle-verify grok"* |

Delegation levers, all optional: `via <harness>` pins the target; `floor it` (the default)
picks the cheapest model clearing each task's bar and `play it safe` goes one tier up;
`with review`, `read-only`, and `supervised` adjust the lane. Full lifecycle:
[skills/delegate/SKILL.md](skills/delegate/SKILL.md). Artifacts and the ledger land in
`.swingle/delegate/`.

## How a dispatch works

Every ask becomes a briefed subagent before the target CLI runs:

1. **Role** — implementer, reviewer, or explorer, inferred from the ask.
2. **Model tier** — matched to the task's difficulty and passed explicitly, never left to
   the CLI's default.
3. **Operating contract** — the brief: what to do, what not to do, the context, the
   interfaces it touches. Per-role contracts (implementer, task-reviewer, design-reviewer,
   reader) live in [contracts/](contracts/).
4. **Return contract** — a fixed status vocabulary (`DONE`, `DONE_WITH_CONCERNS`,
   `NEEDS_CONTEXT`, `BLOCKED`) and a required report shape, so the controller can adjudicate
   the result instead of trusting prose.
5. **Liveness + evidence gate** — the run is watched for stalls; after a write-lane job the
   controller checks the working tree and re-runs the covering tests before committing.

Every dispatch is recorded in a ledger — role, harness, model, session id, returned
status — so the run reproduces:

```text
002 dispatched: provider=grok model=grok-4.5 attempt=1
002 complete: status=DONE outcome=answer-returned
```

## Safety & trust

Swingle spawns agentic CLIs that run tools, edit files, and execute commands, on task text a
model authored. The full threat model is [docs/safety.md](docs/safety.md); the essentials:

- The gates are not a sandbox. A dispatched agent reads, writes, and runs commands the way
  you can. `read-only` is an opt-in lane, not the default.
- Only `codex` and `grok` sandbox at the OS level. The rest rely on the gate plus your
  review.
- The evidence gates surface effects, not correctness; the controller adjudicates.
- Prompt injection is a real surface. Review dispatched changes as you would a pull request
  from a stranger.

## Going deeper

- **Model tiering & economics** — tier→model tables ship in each pack; override layers and
  the `swingle-models` tool: [docs/model-tiering.md](docs/model-tiering.md).
- **Credentials & subscription seats** — Swingle works best driving flat-rate seats you
  already pay for; auth modes and caps: [docs/credentials.md](docs/credentials.md).
- **Adding a harness pack** — manifest-driven, no `core/` edits; grammar and validator:
  [docs/pack-authoring.md](docs/pack-authoring.md).
- **Reporting verification findings** — packs are living documents; where to record what
  you observe: [core/verification-protocol.md](core/verification-protocol.md), or
  [open an issue](https://github.com/hiivmind/swingle/issues/new?template=verification-finding.md).

## License

[MIT](LICENSE) © 2026 Nathaniel Ramm
