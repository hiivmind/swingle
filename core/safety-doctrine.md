# Safety Doctrine

> Living doctrine. Provider behavior is recorded in provider packs and must be re-verified
> when the installed version differs from its stamp.

The hard gate is the controller, not a provider pack. A pack may offer containment, but the
controller is still responsible for choosing the dispatch lane, running the required gates,
and deciding whether work is accepted.

When the manifest declares `sandbox: none`, work only from a clean, committed tree and
inspect the diff after every dispatch, including roles requested as read-only. Agent
self-report is never evidence: verify side effects on disk and re-run the applicable test
gates yourself. The controller commits; agents never do.

Read-only is an intent unless `sandbox: enforced` supplies a review lane. In an unenforced
environment, a role can read, write, or execute freely regardless of a request to review
only, so clean-tree-before and diff-after are mandatory. Prefer a verified contained lane
for write work and structured reviews; use other packs for perspective diversity and price.

## A missing status block is unknown, never success

The four-status vocabulary (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) is a
contract the agent may simply not honor: a cheap tier can return a prose status section
instead of the block (see core/verification-log.md, "2026-07-23 — supervised-delegate
rules verified behaviorally (v1.4.0)" entry). Whatever reads that block —
controller or supervisor — **must treat an absent or non-conforming block as UNKNOWN and
escalate to the controller's own evidence**, never infer DONE from prose that sounds
finished, and never paraphrase it into a status token that was not emitted. A supervisor
reporting a status word outside the four is reporting its own inference, not the agent's
result.

This costs nothing when the gate is doing its job: the gate is on-disk evidence — HEAD,
porcelain, diff, report existence, and the controller's own test run — and that evidence
is what establishes the work is sound. The status block routes the workflow; it never
substitutes for the gate. Escalate rather than raising the tier for status fidelity alone,
unless something downstream actually parses the block by keyword.
