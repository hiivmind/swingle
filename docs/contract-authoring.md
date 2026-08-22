# fAuthoring contracts

A contract is the operating brief handed to a delegated provider CLI for one role: what it
may do, how it reports, and when it must stop and ask instead of guessing. The LLM reads it
as Markdown at dispatch time; nothing parses its internal shape back out, so authoring
discipline, not a validator, keeps a new contract aligned with its siblings
(`tests/test_skills.py::test_contracts_are_transport_neutral` only confirms no provider or
transport language leaked in, and `tests/test_repo_integrity.py` only confirms
cross-references resolve).

## The role set

Contracts implement the roles of the classification matrix (see
[references/concepts.md](../references/concepts.md)): `reader`, `implementer`,
`task-reviewer`, `design-reviewer`, `independent-review`, and `fact-checker`, one
contract file per role, plus the catch-all role `general-task` for work that resists
classification or arrives composite and entangled. The matrix's axes do not grow casually:
a new contract is a new role in the matrix.

The governing principle (`contracts-and-ledger-retained`, one of the two load-bearing
controls Swingle kept from the certification era) requires a new contract to justify
itself as improving delegated quality or auditability, staying provider-independent, never
as a compatibility shim for something else that was removed.

## The shared shape

Every contract follows the same skeleton:

```markdown
# <Role> Operating Contract

You are <the task shape this role answers>. Your dispatch message names <what the
dispatch supplies, such as a brief file, prior interfaces, or the selected report mode>,
and the current working directory you operate from. This contract is how you operate.

## <Ground rules / Your job>

- **Working directory.** Operate only inside the directory your dispatch names; every
  dispatch names it explicitly. This element is mandatory — no contract may proceed on an
  inherited or assumed working directory.
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

Registration touches four places, all by hand. There is no directory-listing discovery
for contracts the way `providers/` has for provider packs:

1. Write `contracts/<role>-contract.md` following the shape above, including the
   mandatory working-directory element.
2. Add the role to `CONTRACTS` in `lib/swingle/config.py` — `config set` and `config
   validate` reject keys naming roles missing from that tuple.
3. Add the new role to `references/concepts.md`'s matrix (its cell) and the refinement
   rules if the cell holds more than one candidate.
4. Add the new contract as a selectable option in `skills/delegate/SKILL.md` step 1, the
   only place a contract is actually chosen.

`tests/test_config.py::test_contracts_tuple_matches_contracts_directory` asserts
`CONTRACTS` matches the `contracts/` listing, and `tests/test_skills.py` asserts every
role name is named in SKILL.md step 1, so a contract added to one surface but not the
others fails CI.
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
