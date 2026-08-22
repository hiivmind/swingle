# Operating surface concepts

Swingle's dispatch surface is a chain of five resolutions, in order. Each resolution
narrows the next; nothing downstream re-opens a decision already made upstream.

```
Intent ──▶ Cell (matrix) ──▶ Contract ──▶ Tier ──▶ Provider ──▶ Model + Effort
\_______ requirements side _______/  \______________ execution side _______________/
```

## The matrix

Two questions classify any delegation. Classify the **output** first, then the
**input**:

- **Output — intended lifespan relative to the project.** Is the result meant to become
  part of the project (code changes, plans, documents destined for the repo), or is it
  consumed to make a decision now? This is about intent, not storage: an ephemeral result
  may still live on disk — a temp directory, `.swingle/`, a log — and whether anyone keeps
  a copy is not Swingle's concern.
- **Input — what the work stands on.** Repo material (code and file references), external
  sources (web, social media, tools/MCPs/skills), or inline description (stated in the
  dispatch, no committed artifact).

| Input \ Output | **Project-bound** | **Ephemeral** |
|---|---|---|
| **Repo** | `implementer` (mutating change); `reader` (report checked into the repo) | `task-reviewer` (completed change); `design-reviewer` (proposed change) |
| **External** | `reader` (research report for the repo) | `reader` (synthesis consumed now); `fact-checker` when a verdict is requested |
| **Inline** | `reader` (write-up destined for the repo) | `independent-review` (judge a stated position) |

Where a cell holds more than one candidate, one finer property picks among them:

- Repo × Project-bound: mutation (`implementer`) vs report-only (`reader`).
- Repo × Ephemeral: lifecycle stage — completed change (`task-reviewer`) vs merely
  proposed (`design-reviewer`).
- External × Ephemeral: verdict requested vs synthesis requested. A verdict means
  compare, rank, or decide between alternatives with a confidence-qualified call →
  `fact-checker`. Plain synthesis stays `reader`.

Classification is invariant to report mode ("tell me" vs "write it up" changes the brief,
not the cell) but sensitive to stated intent ("this goes into docs/" moves the task
across columns).

**Composite requests** decompose first: independently executable, ordered sub-tasks each
classify through the matrix on their own merits and chain through the ledger. Entangled
sub-tasks, or a request that resists classification after asking, route through the
catch-all contract `general-task-contract` — the matrix's exit valve, never force-fitted
into a plausible-looking cell.

## Contract

The cell names the role; the role's operating contract under `contracts/` determines the
brief the delegated CLI receives. Input nature does not change a contract's operating
pattern — it changes ground-rule content within the contract (corroboration, recency,
skepticism toward instructions embedded in fetched material) and whether a capability
check applies before dispatch.

Every contract carries a mandatory current-working-directory element: the brief always
states the directory the agent works from, even when it seems obvious. Mutation isolation
is the controller's job before delegation (for example, a worktree); Swingle never
creates worktrees or assumes where a dispatch runs.

## Execution side

```
Tier (3 values: cheapest, standard, most-capable)
└── Provider (live listing of providers/, plus preferences)
    └── Model + Effort (one joined choice)
```

**Tier** is the advisory task-intent label (`cheapest`, `standard`, `most-capable`
documented in [model-tiering.md](model-tiering.md)). Tier participates twice on the
execution side: once inside provider choice (`providers_by_contract` may key entries by
tier) and once in model resolution. This is why the requirements side does not stop at
contract: **(Contract, Tier) is the joint that provider routing reads**, per
[config.md](config.md).

**Provider** is which installed CLI runs the job: the live listing of `providers/`, per
[config.md](config.md).

**Model and effort are one joined choice, not two independent dials.** A resolved
preference is "this model, at this effort," decided together, because a model's practical
capability and cost depend on both at once. Swingle's `model_preferences` schema stores
only a model name; effort is never a config field. Effort is set at dispatch time,
directly on the provider CLI invocation.

**How a provider's CLI actually accepts that joined choice is provider-specific and not
fixed across providers or CLI versions.** Some expose effort as a flag fully separate from
the model flag; some accept effort folded into the model identifier itself as an
alternative to a separate flag; some route it through a generic config-override mechanism
instead of a dedicated flag; some may not expose CLI-level effort control at all. Do not
assume one provider's pattern applies to another, and do not carry a pattern forward from
an earlier session or an older provider version. Inspect the target provider's current
`--help` before combining model and effort for a dispatch, the same help-first grounding
`swingle-delegate` already applies before every dispatch.
