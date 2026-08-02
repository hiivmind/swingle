# Safety & trust

Swingle spawns agentic CLIs that run tools, edit files, and execute commands — on task text
a model authored. This page is the full threat model. The README carries the four
load-bearing lines; everything else lives here.

## What the evidence gates do

After a **write-lane** dispatch the controller inspects the working tree
(staged + untracked + `HEAD`-unchanged) and re-runs the covering tests itself before
trusting a result and committing. **Read-lane** work is judged on the report it returns.

The gates **surface evidence** — an agent that did nothing, left a bad diff, or touched
state it shouldn't — so the controller can adjudicate and commit. They do **not** prove the
work is semantically correct; incomplete tests can't. Agents are contracted not to commit,
and a stray agent commit is surfaced as a violation, not absorbed.

## What they do not do

- **They are not a sandbox.** A dispatched agent can, within its run, read and write files
  and run commands the way you can. `read-only` is an **opt-in** lane, not the default.
- **Only two provider CLIs sandbox at the OS level** — `codex` and `grok`. The rest rely on the
  gate plus your review.
- **Prompt injection is a real surface.** A dispatched agent reads repository content you
  point it at; hostile content there can try to steer it. The gates catch *effects* (bad
  diffs, failed tests), not *intent* — review dispatched changes as you would a pull request
  from a stranger.

## Manifest injection is closed

Every manifest value is validator-enforced: `*-argv` arrays are data (`argv[0]` must equal
`cli`, shell metacharacters rejected), so a pack cannot smuggle in a command to execute.
That is a narrow, deliberately-closed surface — **not** the whole threat model, which is the
sections above. Enforcement lives in `scripts/validate-packs`; the doctrine in
`core/safety-doctrine.md`.

## When a seat hits its cap

A subscription seat hitting a usage/rate limit — or a metered key hitting a quota — surfaces
as a **channel failure** (provider-wide). The controller does **not** silently fall back to
another tier or another provider: it stops and adjudicates, surfacing the failure to you, with
the ledger left consistent (no partial commit is trusted past the gate). Automatic
quota-aware fallback is a deliberate non-feature today — smarter handling is roadmap, tracked
alongside the economics work in [#17](https://github.com/hiivmind/swingle/issues/17). See
[credentials.md](credentials.md) for the API-key fallback route where a CLI offers one.
