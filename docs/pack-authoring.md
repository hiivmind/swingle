# Adding provider notes

Each provider directory contains one living `pack.md` note identifying the provider CLI
and recording real, non-obvious operating guidance. Nothing parses this file back out at
dispatch time; the LLM reads it as Markdown, so its internal shape is not machine-enforced
(`swingle check` only confirms the file exists and that the provider directory holds
nothing else). Discipline here is authoring judgment, not a validator.

A note holds two kinds of row, and only these two:

**Gotchas**: reactive, a real failure was observed and the note changes recovery.

```markdown
| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| <observable signature> | <unreliable result> | <proven action> | <issue, commit, or date> |
```

Every gotcha must satisfy all three inclusion rules:

1. The behavior is silent, misleading, confusing, or missing from normal help.
2. The behavior occurred in real operation.
3. The note changes recovery after the LLM observes the signature.

**Dispatch guidance**: proactive, a real, verified, non-obvious operating fact that changes
how a dispatch is built, without any failure having occurred.

```markdown
| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| <what's being decided> | <what to do> | <why> | <help excerpt, issue, commit, or date> |
```

Every guidance row must satisfy all three inclusion rules:

1. The fact is not obvious from a single glance at `--help`: an interaction between
   documented flags, a precedence rule, a subcommand-specific behavior, or similar.
2. The fact was verified against the live CLI, not assumed or carried forward from another
   provider or an earlier version.
3. The note changes what the LLM does at dispatch time after reading it.

Every row in either table requires a non-empty Evidence cell. If CLI behavior is unclear,
inspect the current provider help before adding a row.

## Keep notes narrow

`pack.md` contains no command tutorial, version, model, success matrix, changelog digest, or
positive inventory. Do not include successful probe results, model catalogs, effort values,
permission summaries, sandbox inventories, output-format inventories, changelog summaries,
current version claims, or cross-provider comparison tables. A dispatch-guidance row states
one decision and its rationale; it does not become a second home for content the gotcha
rules already excluded.

Git supplies history. Provider notes are living documents: update or remove a row when it is
no longer true. Swingle does not ship append-only provider verification history.

## Check a change

After editing a note, run the repository authoring check:

```bash
python3 scripts/swingle check --root .
```

The check confirms the provider directory contains only `pack.md` (no stray assets) and
that links, anchors, and contract references across the repo's owned Markdown resolve. It
does not certify provider behavior, validate the note's internal table structure, or
replace a live CLI observation.
