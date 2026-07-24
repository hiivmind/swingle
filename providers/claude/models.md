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
- **Review lane: qualified as a finder, not as a severity authority (P13, 2026-07-25).**
  sonnet and opus were run against the P13 known-defect fixture (2 runs each). Both **found**
  the defect every time (4/4, with file:line) — no false-clean — but both consistently rated
  it **Minor** rather than the required ≥ Important, reading the brief's "does not exist"
  literally instead of extending it to a directory/unreadable path. So the review rows stay
  `verified` for **dispatch**, not for review quality: use a claude reviewer to surface
  findings, but keep severity adjudication in the controller and re-grade any Minor that is
  actually a violated binding constraint. Full evidence in the 2026-07-25 entry of
  [verification-log.md](verification-log.md). haiku (cheapest) is not a review tier.
