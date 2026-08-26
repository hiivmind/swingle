# Grounding isolation

The controller keeps local deterministic commands in the decision thread. Isolate only
live provider mechanics whose output can be compacted before it reaches that thread.

## Controller-owned local work

Keep these commands and decisions in the controller:

- `dispatch context`
- `grounding record`
- `grounding invalidate`
- ledger writes
- config reads and writes
- temporary parser and artifact management
- task-specific repository verification
- consent, action handling, provider choice, and dispatch composition

These operations are deterministic project work. A grounding worker never performs
them, never writes configuration or ledger state, and never runs a provider dispatch.

## Isolated grounding work

Use one read-only grounding worker only for the requested target list. Isolate:

- live provider help
- model listing
- provider-note recovery analysis
- safe behavioral probes
- failure-repair hunts

The worker reads only the selected provider's pack note, live help, and the exact failing
command or target named in its brief. It does not inspect product implementation under
`<root>/lib` or `<root>/scripts`, choose a provider/model/effort, decide policy, or
explore outside the target list. A worker reports compact mechanics with the exact
command that produced each value. Each requested scope is `observed`, `not-exposed`, or
`unverifiable`.

Filter output at the source, for example with `jq` or a small Python filter, so the
controller receives only the fields needed for the decision. Preserve raw provider
help, probes, and parser output in the controller-owned artifact directory when needed.
If no isolation facility exists, run the target grounding inline and say so once.

## Warm dispatch boundary

A usable grounding receipt is consumed directly by a warm dispatch; warm dispatch never creates a grounding worker.
A cache miss, stale receipt, explicit fresh-grounding
request, or contradicted provider mechanic returns an action to the controller; the
controller then decides whether and how to invoke an isolated grounding worker. The
worker records no cache result. The controller validates normalized results and calls
`grounding record` or `grounding invalidate` itself.
