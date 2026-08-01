# claude models (Anthropic seat)

> The table of record is [models.yaml](models.yaml) (layered overrides: see README
> "Model tables and overrides"). This file carries the documentary layer only —
> verification narrative, watch lists, and corrections.

Model keys are **aliases** (`haiku` / `sonnet` / `opus`), not pinned snapshot ids: the CLI
resolves each alias to the latest model, so the table tracks releases automatically. The
currently resolved snapshots are `haiku`→claude-haiku-4-5-20251001,
`sonnet`→claude-sonnet-5, and `opus`→claude-opus-5; see the pack's verification log for
round evidence.

Effort: `--effort low|medium|high|xhigh|max` — locally validated (bogus → warn + default, exit 0).

## Documentary

- **`opus` alias is machine-overridable.** An `ANTHROPIC_DEFAULT_OPUS_MODEL` setting (env or
  `~/.claude/settings.json`) repoints what `opus` resolves to. The alias selects "the operator's opus";
  pin a snapshot id in a project override only if a lane needs an exact model.
- **Review lane:** sonnet and opus clear P13 with the current reviewer contract. Keep
  severity adjudication in the controller; this is a prompt mitigation, not a guarantee.
  Haiku is not a review tier. See the pack's [verification log](verification-log.md) for
  benchmark evidence.
