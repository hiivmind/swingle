# Adding provider notes

Each provider directory contains one living `pack.md` note identifying the provider CLI
and recording real, non-obvious operating guidance. The LLM reads the note as Markdown at
dispatch time. Repository checks enforce the provider file shape and the exact Dispatch
guidance heading; they do not certify provider behavior or execute examples.

## Required pack shape

Use this order and keep each heading exactly as written:

```markdown
# <Provider> notes

CLI: `<id>`

## Gotchas

<gotcha table, possibly empty>

## Dispatch guidance

<guidance table and optional subsections, possibly empty>

## Typical models

<optional orientation only>
```

Every provider note MUST contain exactly one `## Dispatch guidance` heading. Do not rename,
duplicate, or move that heading. Gotchas and Typical models are optional; an empty section is
better than invented evidence.

A note holds two kinds of evidence-backed row, and only these two:

**Gotchas** are reactive. A real failure was observed and the row changes recovery:

```markdown
| Failure signature | Impact | Recovery | Evidence |
| --- | --- | --- | --- |
| <observable signature> | <unreliable result> | <proven action> | <issue, commit, help command, or approved probe> |
```

Every gotcha MUST satisfy all three inclusion rules:

1. The behavior is silent, misleading, confusing, or missing from normal help.
2. The behavior occurred in real operation.
3. The row changes recovery after the LLM observes the signature.

**Dispatch guidance** is proactive. It is a real, verified, non-obvious operating fact that
changes how a dispatch is built without requiring a failure:

```markdown
| Decision point | Guidance | Rationale | Evidence |
| --- | --- | --- | --- |
| <what is being decided> | <what to do> | <why> | <help command, issue, commit, or approved probe> |
```

Every guidance row MUST satisfy all three inclusion rules:

1. The fact is not obvious from a single glance at `--help`: it is an interaction between
   documented flags, a precedence rule, a subcommand-specific behavior, or similar.
2. The fact was verified against the live CLI, not assumed or carried forward from another
   provider or an earlier version.
3. The row changes what the LLM does at dispatch time after reading it.

Every row MUST have a non-empty Evidence cell. Replace historical or deleted log-path
citations with the exact current help command, approved probe, issue, or commit. If current
behavior is unclear, inspect current help and omit the row when the evidence still does not
support it.

## Dispatch guidance contents

The Dispatch guidance section may contain its table plus optional `### Result-only command`
and `### Structured output` subsections. Include a copyable result-only command for each
provider with a supported headless route. When current evidence exposes structured output,
include one structured command and a human-readable interpretation that names its completion,
final-text, session, usage, cost, or denial fields only where observed. A command example is
LLM guidance, not a machine-executed template.

Use these canonical placeholders in command examples and mutation guidance:

- `$PROJECT`: the absolute project or workspace directory.
- `$PROMPT`: the complete authored prompt file (or its content where the CLI requires text).
- `$MODEL`: the model route selected from current provider evidence.
- `$EFFORT`: the provider's effort/reasoning setting when the provider exposes one.
- `$ARTIFACT`: an absolute path for captured provider output.

Preserve the complete authored mutation briefing in `$PROMPT`; do not shorten it, paraphrase
it, or ask a controller to rewrite it. Record narrow write modes, workspace trust, tool-class
differences, denial signatures, and exit-code traps only when current evidence supports them.
Repository verification remains separate from provider completion.

Do not add version stamps, success matrices, static model catalogs, permission inventories,
provider tutorials, or cross-provider tables. Prohibit fixed command templates, selector
programs that parse provider output for the controller, and controller paraphrasing of authored
mutation briefings. A result-only command is still allowed when it uses the canonical
placeholders and explains its human interpretation; it MUST NOT become executable controller
logic.

## Fingerprint boundary

The provider guidance fingerprint covers exactly the section beginning at the single line
`## Dispatch guidance` and ending immediately before the next line whose trimmed text starts
with `## `, or at end of file. The fingerprint normalizes CRLF and CR line endings to LF,
removes trailing newlines from that section, then hashes one final LF. Therefore:

- Changes in the Dispatch guidance table or any `###` subsection change the fingerprint.
- Changes in Gotchas or `## Typical models` do not change the fingerprint.
- A missing or duplicate Dispatch guidance heading is invalid, even when the section is empty.
- Keep all dispatch examples, interpretations, and guidance rows inside this boundary.

This boundary lets reactive gotcha maintenance and optional orientation maintenance proceed
without invalidating a cached dispatch-guidance receipt, while every proactive dispatch change
correctly requires fresh grounding.

## Model orientation exception

Discovery-method rows are welcome. A row may teach how to ask this CLI what models it has
(the listing subcommand or flag, and where prices appear when current evidence supports that
fact); it teaches fishing, not fish.

A pack MAY end with one short `## Typical models` section only when it has a line reading
`Orientation only — not definitive, not a gate`, a snapshot date, the live command that
supersedes it, at most about five entries, and no consumer that treats the list as eligibility.
When the live listing disagrees, the list loses. Remove the section when it becomes stale or
starts steering dispatch.

Git supplies history. Provider notes are living documents, not append-only verification logs.

## Check a change

Run focused repository checks after editing:

```bash
python3 -m pytest -q tests/test_repo_integrity.py tests/test_grounding.py -k "provider or fingerprint"
git diff --check
```

The checks confirm provider shape, links, anchors, and fingerprint behavior. They do not
replace a live CLI observation, execute a command example, or certify a model/account route.
