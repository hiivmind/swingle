# Spec — Token-profiling study (one-off)

**Status:** approved design (brainstormed 2026-07-26)
**Deliverable class:** one-off empirical study — findings doc + reduction issues. No durable
tooling is committed; the profiler lives in the study appendix for reproducibility.

## 1. Problem

When a swingle dispatch session begins, the orchestrator (controller) context reaches
**90–100k tokens before the first delegation fires**. The playbook's token-efficiency
rules (E1–E7) govern *per-task marginal* cost; nothing measures the *session-fixed*
setup cost, and nothing attributes it. Static byte-counting shows the plugin's own
doctrine (skill text + core docs + one pack + templates) is only ~24k tokens of that —
so roughly three-quarters of the observed cost is currently unattributed (harness
floor, tool-call mechanics, re-reads, hidden overhead). Reduction without attribution
risks cutting functionality while missing the real cost centers.

## 2. Goals

1. Attribute orchestrator context consumption to named causes, empirically.
2. Measure the session-fixed (Step-0) cost separately from per-task marginal cost.
3. Quantify the plugin+skills self-footprint so it can be reduced **without reducing
   functionality** — every reduction proposal must cite an attribution row.

Out of scope: external-provider-side token usage (agy/opencode consumption per job) —
captured as a backlog item, not studied here. Building a durable profiling harness —
explicitly declined in favour of the one-off study.

## 3. Evidence base

Two transcripts, one profiler:

- **Transcript A (real-world composition):** the full Claude Code session JSONL of the
  2026-07-25 SDD session (spec → external adversarial reviews → plan → 7-task dispatch
  round). Shows what a heavy session actually spends, phase by phase.
- **Transcript B (controlled Step-0 isolate):** a fresh session in this repo that
  performs exactly one trivial read-only `swingle-delegate` job and stops. Its
  tokens-before-first-dispatch IS the session-fixed cost, uncontaminated by
  spec/plan work.

## 4. Method (approach C — hybrid attribution)

The session JSONL provides two independent signals per assistant turn:

- the `usage` block — exact `input_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `output_tokens` (ground truth, but per-request totals
  only);
- the message content — every tool result, skill injection, user message, and
  assistant output, sized in bytes and attributable to a named cause (exhaustive
  attribution, but only estimable at ~4 chars/token).

**Rule:** usage deltas are ground truth for phase totals; content sizes apportion
within a phase; the two are reconciled. A residual above ~10% of a phase's delta is
flagged as its own finding (hidden overhead — system reminders, schema re-sends,
cache churn), never silently absorbed.

## 5. Phase taxonomy

Every token lands in exactly one bucket:

| Bucket | Contents |
| --- | --- |
| `harness-floor` | request-1 input: system prompt, CLAUDE.md files, tool schemas, memory |
| `skill-injection` | Skill tool results: superpowers + swingle skill text entering context |
| `step0-doctrine` | Reads of `core/`, `providers/`, `contracts/`, harness adapter |
| `workspace-mechanics` | validate-packs, git, workspace scripts, ledger I/O outputs |
| `plan-and-spec-content` | the spec/plan artifacts themselves entering context |
| `dispatch-cycles` | per-task prompts, dispatch logs, reports, review packages |
| `residual` | usage delta the content cannot explain |

## 6. Headline metrics

- tokens-before-first-dispatch, for A and B;
- cumulative context curve over the session;
- plugin-attributable vs harness-attributable split;
- per-task marginal cost across A's dispatch cycles, tested against the playbook's
  ~1–2k/task claim.

## 7. Profiler

A Python script (stdlib only) parsing transcript JSONL into a per-request ledger:
context size, delta, and per-content-block cause tags. It is written and run from the
session scratchpad — **not committed** — and its full text is embedded as an appendix
in the findings report so the method is reproducible without shipping tooling.

## 8. Outputs

1. `docs/token-profile-2026-07.md` — methodology, attribution tables, cumulative
   curve, findings, reduction backlog, appendix (profiler source).
2. One GitHub issue per concrete reduction opportunity, each citing the attribution
   row that evidences it.
3. Branch `docs/token-profiling-study` → PR to `develop`.

## 9. Constraints

- The hard gate (`validate-packs && codex-smoke`) chains every commit.
- Purity boundary applies to the report as repo prose: provider names allowed, model
  ids / invocation strings not.
- Transcript content quoted in the report is limited to structural evidence (sizes,
  causes, phases) — no verbatim reproduction of large context blocks.
