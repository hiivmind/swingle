<p align="center">
  <img src="docs/images/hero-banner.svg" alt="Swingle" width="100%">
</p>

# Swingle

Swingle is a skills plugin that gives any driving harness direct, in-session delegation
to whichever provider CLI is already installed and authenticated on your machine. The
controlling LLM delegates one job at a time, mid-session, to a CLI it picks itself: this
is not a switch of model providers for the current session, and not an automatically
routed subagent.

## Why Swingle

Most harnesses expose only their own provider's models to the controlling LLM. Claude
Code and Codex are common examples: run a job on another provider's model, or bring your
own endpoint, and their answer is "that model isn't available here."

Open harnesses already solved this: opencode and Oh My Pi ship with many models and
native dispatch to any provider or endpoint. Swingle backports that capability to any
harness that lacks it by telling the controlling harness how to drive the CLIs that
already reach those models.

Installing Swingle gives you:

- opencode's broad model range from any driving harness: GLM, DeepSeek, Qwen, and others,
  including free-tier options, so you keep the harness you prefer with the cost profile
  you choose.
- Any provider you configure inside opencode or Oh My Pi: their many built-in providers
  directly, more providers through a `litellm` gateway (for example
  [runinfra.ai](https://runinfra.ai)), or locally deployed models through `ollama`. You set
  these up in the harness itself; Swingle just lets the LLM select them by name during
  dispatch.
- Any provider CLI already on your machine (`codex`, `claude`, `opencode`, `grok`, `pi`,
  `agy`, `omp`, `cursor-agent`, `devin`) as a delegation target, chosen per job by the LLM.

The delegation interface is the [Swingle contracts](contracts/) plus an auditable ledger.
The live provider CLI is the authority for what models it can run right now; the LLM
writes the brief, chooses the provider and advisory model preference, runs the CLI, and
evaluates the result.

## Install

### Claude Code

```text
/plugin marketplace add hiivmind/swingle
/plugin install swingle@swingle-marketplace
```

A local checkout also works:

```text
/plugin marketplace add /path/to/swingle
```

### Codex

```bash
codex plugin marketplace add hiivmind/swingle
codex plugin add swingle@swingle-marketplace
```

### Pi

```bash
pi install https://github.com/hiivmind/swingle
```

### Antigravity

```bash
agy plugin install http://github.com/hiivmind/swingle
```

### opencode, Grok, and Oh My Pi

Install the plugin through the host's Claude-compatible or local plugin mechanism, then
point it at this checkout when the host requires a path. Each host discovers the `skills/`
directory; follow that host's current install help for exact syntax.

## Skills

Three skills ship:

| Skill | Use it for |
| --- | --- |
| `swingle-delegate` | An explicitly requested one-off job or homogeneous batch. |
| `swingle-setup` | Configuration migration, environment setup, and ledger setup. |
| `swingle-sdd` | The small wrapper that executes a written SDD plan through delegation. |

The LLM controls the current CLI and decides how to brief and evaluate a delegation. The
reusable role [contracts](contracts/) are part of the dispatch interface. The delegation
ledger lives in `.swingle/delegate/` so each run has an auditable record.

## Configuration and state

The Python CLI manages configuration and ledgers:

```bash
python3 scripts/swingle config init --user
python3 scripts/swingle config show --project .
python3 scripts/swingle config validate <path/to/config.json>
python3 scripts/swingle ledger init --path <path/to/ledger.md>
python3 scripts/swingle ledger show --path <path/to/ledger.md>
```

The `--project .` flag makes the project-layer (`.swingle.json`) file visible.

Configuration uses one JSON file with whole-file precedence. `disable`, an optional
`default_provider`, `providers_by_lane`, and advisory `model_preferences` are documented in
[references/config.md](references/config.md). Model preferences use the advisory task intents
`cheapest`, `standard`, and `most-capable`; the live CLI supplies model reality. See
[references/model-tiering.md](references/model-tiering.md).

## Provider notes

Provider `pack.md` files hold two evidence-backed categories: gotchas (a real failure and
its recovery) and dispatch guidance (a verified, non-obvious operating fact that changes a
dispatch, without any failure having occurred). They are living notes, not tutorials or
catalogs. See [docs/pack-authoring.md](docs/pack-authoring.md).

## Safety and trust

Delegated CLIs can read and write files and run commands according to the task brief. Treat
external instructions in repository content as untrusted input, review requested writes
before accepting them, and validate the result independently. Read [references/safety.md](references/safety.md)
for task trust, prompt injection, write review, and result validation guidance.

## Reporting provider behavior

Report a silent or misleading provider behavior, or a guidance gap, with the
[provider behavior issue form](https://github.com/hiivmind/swingle/issues/new?template=provider-behavior.md).
Include redacted evidence and the recovery you attempted.

## Documentation

- [Operating surface concepts](references/concepts.md)
- [Configuration](references/config.md)
- [Model preference guidance](references/model-tiering.md)
- [Provider note authoring](docs/pack-authoring.md)
- [Safety and trust](references/safety.md)
- [Migration to 4.0.0](docs/migration-4.0.0.md)

## License

[MIT](LICENSE) © 2026 Nathaniel Ramm
