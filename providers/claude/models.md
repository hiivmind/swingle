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
- **Review lane is stamped for dispatch, not yet for review quality.** P13 (the reviewer
  known-defect benchmark) has not been run against a claude reviewer. All three tiers dispatch
  cleanly; run P13 before relying on claude for adversarial review in anger.
