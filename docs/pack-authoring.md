# Adding provider notes

Each provider directory contains one living `pack.md` note. It identifies the provider CLI
and records only gotchas that help the LLM recover from a real, non-obvious failure.

Use this format:

```markdown
# <Provider> gotchas

CLI: `<executable>`

| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| <observable signature> | <unreliable result> | <proven action> | <issue, commit, or date> |
```

Every gotcha must satisfy all three inclusion rules:

1. The behavior is silent, misleading, confusing, or missing from normal help.
2. The behavior occurred in real operation.
3. The note changes recovery after the LLM observes the signature.

Every row requires evidence. An empty Evidence cell is invalid. If CLI behavior is unclear,
inspect the current provider help before adding guidance.

## Keep notes narrow

`pack.md` contains no command tutorial, version, model, success matrix, changelog digest, or
positive inventory. Do not include successful probe results, model catalogs, effort values,
permission summaries, sandbox inventories, output-format inventories, changelog summaries,
current version claims, or cross-provider comparison tables.

Git supplies history. Provider notes are living documents: update or remove a row when it is
no longer true. Swingle does not ship append-only provider verification history.

## Check a change

After editing a note, run the repository authoring check:

```bash
python3 scripts/swingle check --root .
```

The check validates the deterministic structure shared by all provider notes. It does not
certify provider behavior or replace a live CLI observation.
