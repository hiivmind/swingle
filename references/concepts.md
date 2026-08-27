# Operating surface concepts

Swingle classifies the work first, then resolves the execution side in a fixed order.
Requirements classification selects the contract and advisory tier; execution then turns
that choice into one provider attempt whose result is independently checked.

```
Intent ──▶ Cell (matrix) ──▶ Contract

Tier → Provider → Project grounding → Model + Effort
  → LLM-composed command → Provider outcome → Repository verification
```

The first line is the requirements side. The second is the execution side: each
resolution narrows the next, and nothing downstream re-opens an upstream decision.

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
| **Inline** | `reader` (write-up destined for the repo) | `reader` (synthesis consumed now); `independent-review` (judge a stated position) |

Where a cell holds more than one candidate, one finer property picks among them:

- Repo × Project-bound: mutation (`implementer`) vs report-only (`reader`).
- Repo × Ephemeral: lifecycle stage — completed change (`task-reviewer`) vs merely
  proposed (`design-reviewer`).
- External × Ephemeral and Inline × Ephemeral: verdict requested vs synthesis requested.
  A verdict means compare, rank, or decide between alternatives with a confidence-qualified
  call → `fact-checker` for external claims, `independent-review` for a stated position.
  Plain synthesis stays `reader`.

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
Tier → Provider → Project grounding → Model + Effort
  → LLM-composed command → Provider outcome → Repository verification
```

**Project grounding** supplies observed provider mechanics and an advisory model
inventory for this project. The grounding cache stores those observed mechanics and
advisory inventory; it is not an availability gate. If a live invocation contradicts
the cache, live invocation wins, and the controller records or invalidates the affected
observation before continuing.

The LLM composes the provider command from the live grounding, authored task, and
provider guidance. Python provides deterministic context and ledger structure.
**Python never renders commands or parses provider output.** The provider outcome
records what the CLI did; repository verification independently checks requested
mutations, tests, and invariants.

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
capability and cost depend on both at once. `model_preferences` may therefore store the
joined pair — an entry is a model name or a `{"model", "effort"}` object — but always as
an advisory preference: the live CLI decides what it accepts at dispatch time, and an
explicit user or task statement outranks any stored value.

**How a provider's CLI actually accepts that joined choice is provider-specific and not
fixed across providers or CLI versions.** Some expose effort as a flag fully separate from
the model flag; some accept effort folded into the model identifier itself as an
alternative to a separate flag; some route it through a generic config-override mechanism
instead of a dedicated flag; some may not expose CLI-level effort control at all. Do not
assume one provider's pattern applies to another, and do not carry a pattern forward from
an earlier session or an older provider version. Inspect the target provider's current
`--help` before combining model and effort for a dispatch, the same help-first grounding
`swingle-delegate` already applies before every dispatch.

## Workspace

Every terminal job carries an automatic manifest. Inspect, verify, publish, or remove
the workspace with:

```text
workspace show --run <run-id> [--job <job-id>] [--file <path>] [--to <destination>] [--json]
workspace verify --run <run-id> [--job <job-id>] [--json]
workspace copy --run <run-id> [--job <job-id>] [--file <path>] --to <destination> [--json]
workspace delete --run <run-id> [--job <job-id>] [--json]
workspace delete --run <run-id> [--job <job-id>] --expect-selection-sha256 <digest> --apply [--json]
```

A healthy delegation asks no workspace question and no metadata question: `workspace
copy` runs only when the original request names the exact destination and selection,
and `workspace delete` applies with one preview and one confirmation using the exact
preview digest.

Boundaries:

- The manifest is automatic.
- The ledger is authoritative for lifecycle state.
- The manifest is authoritative for file inventory and hashes.
- Copy never sends files to a network service.
- Copy never runs Git.
- Deletion never removes ledger files.
- Swingle has no workspace classification or retention policy.
- The workspace modules do not import `subprocess`, network clients, or Git bindings.
