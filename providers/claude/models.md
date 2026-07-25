# claude models (Anthropic seat) — verified dispatching 2026-07-24

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

Model keys are **aliases** (`haiku` / `sonnet` / `opus`), not pinned snapshot ids: the CLI
resolves each alias to the latest model, so the table tracks releases automatically. The
resolved snapshot at verification time was `haiku`→claude-haiku-4-5, `sonnet`→claude-sonnet-5,
`opus`→claude-opus-4-8.

Effort: `--effort low|medium|high|xhigh|max` — locally validated (bogus → warn + default, exit 0).

## Documentary

- **`opus` alias is machine-overridable.** An `ANTHROPIC_DEFAULT_OPUS_MODEL` setting (env or
  `~/.claude/settings.json`) repoints what `opus` resolves to — observed on the authoring
  machine resolving `opus`→claude-opus-4-7[1m]. The alias still selects "the operator's opus";
  pin a snapshot id in a project override only if a lane needs an exact model.
- **Review lane: clears P13 with the ≥ v1.9.2 contract (P13, 2026-07-25).** sonnet and opus
  were run against the P13 known-defect fixture (2 runs each). Under the pre-1.9.2 contract
  both **found** the defect every time (4/4, no false-clean) but rated it **Minor**, reading
  the brief's "does not exist" literally. That miss motivated a severity-floor nudge in the
  shared `task-reviewer-contract.md` (an uncaught exception on plausible user input is
  Important, not Minor); re-run with the nudge, both models cited the defect under
  **Important** and flipped the assessment to Needs fixes (4/4). So the review lane now clears
  P13 with the current contract. It remains a prompt mitigation, not a guarantee — keep
  severity adjudication in the controller. Full before/after in the two 2026-07-25 entries of
  [verification-log.md](verification-log.md). haiku (cheapest) is not a review tier.
