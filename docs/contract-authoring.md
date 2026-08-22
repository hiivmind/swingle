# Authoring contracts

A contract is the operating brief handed to a delegated provider CLI for one role: what it
may do, how it reports, and when it must stop and ask instead of guessing. The LLM reads it
as Markdown at dispatch time; nothing parses its internal shape back out, so authoring
discipline, not a validator, keeps a new contract aligned with the other three
(`tests/test_skills.py::test_contracts_are_transport_neutral` only confirms no provider or
transport language leaked in, and `tests/test_repo_integrity.py` only confirms
cross-references resolve).

## The role hierarchy

Contracts sit under a fixed two-lane structure (see [references/concepts.md](../references/concepts.md)):
`implement` and `review` are the only lanes, and there is no third. `implement` holds
`reader`/`implementer`; `review` holds `task-reviewer`/`design-reviewer`/`second-opinion`,
one contract file per role. A new contract is a new role slotted under one of the two
existing lanes; the lane axis itself does not grow.

The governing principle (`contracts-and-ledger-retained`, one of the two load-bearing
controls Swingle kept from the certification era) requires a new contract to justify
itself as improving delegated quality or auditability, staying provider-independent, never
as a compatibility shim for something else that was removed.

## The shared shape

Every contract follows the same skeleton:

```markdown
# <Role> Operating Contract

You are <the task shape this role answers>. Your dispatch message names <what the
dispatch supplies, such as a brief file, prior interfaces, or the selected report mode>.
This contract is how you operate.

## <Ground rules / Your job>

- What this role may and may not do.
- Escalate rather than guess: stop and ask (status `NEEDS_CONTEXT`) when the task, a named
  source, or a requirement is unclear.

## Report

Two report modes, selected by the dispatch: file mode (write the full report to the named
path, return a short status) and captured mode (return the full report in the final
response, then the status block). The status block is at most 15 lines and uses:

STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED

## Resumed session

How this role behaves when the controller reopens the same session with follow-ups or
review findings.
```

Stay transport-neutral: a contract must read the same regardless of which provider CLI
executes it. Never mention a provider pack, report-transport mechanics, or sandboxed
providers; `test_contracts_are_transport_neutral` fails the build if any of those phrases
appear.

## Adding a new contract

Registration touches three places, all by hand. There is no directory-listing discovery
for contracts the way `providers/` has for provider packs:

1. Write `contracts/<role>-contract.md` following the shape above.
2. Add the new role as a leaf under its lane in `references/concepts.md`'s hierarchy and
   accompanying prose.
3. Add the new contract as a selectable option in `skills/delegate/SKILL.md` step 1, the
   only place a contract is actually chosen.

`tests/test_skills.py` asserts every `contracts/*.md` role name is named in that step, so a
contract added to the directory but never wired into step 1 fails CI.
`tests/test_repo_integrity.py` independently confirms any reference to a contract path or
name across `skills/`, `contracts/`, and `providers/` markdown resolves to a real file.

## Check a change

After editing or adding a contract, run the test suite:

```bash
python3 -m pytest -q
```

Neither test certifies that a contract's operating advice is good, only that references
resolve and the language stays transport-neutral. That judgment stays with whoever writes
and reviews the contract.
