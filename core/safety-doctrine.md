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
