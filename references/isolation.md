# Grounding isolation

Mechanical grounding — read-only discovery and validation — should not consume the
decision thread. Wherever the harness offers subagents or background agents
(Claude Code's Task tool, an omp hub, a spawned codex or opencode agent), run these
steps isolated and consume only their compact findings:

- `config show` and ledger reads, plus any repair hunt through installed plugin files,
  scripts, or references to explain an observed error
- provider `--help` inspection and model-listing commands (including the pack's
  documented discovery command)
- reference and contract lookups needed to answer one mechanical question

The decision thread keeps everything that is not mechanical: classification and
tier/provider/model decisions, user consent, every write (`config set`, ledger init
and event appends), the dispatch itself, and all reporting to the user.

Rules:

- A grounding subagent returns compact findings: the exact values the decisions need,
  each with the command that produced it. It never writes configuration or ledger
  state, and never runs a provider dispatch.
- Stay inside the assigned target list. Anything outside it is reported as a gap
  ("not inspected: X"), never explored on initiative. Reading product source under
  `<root>/lib` or `<root>/scripts` is out of bounds — behavior comes from live help
  and pack notes, not implementation internals.
- Filter output at the source (`| jq`, `| python3 -c …`) so a large catalog arrives
  as the few fields the decision needs, never as its raw dump.
- Grounding reports mechanics only: verified command forms, supported values,
  placement rules. It does not choose among open policy options — which preferred
  model, which effort — and a grounding brief must never ask it to. Those decisions
  are made before the brief and stated in it as constraints.
- If no subagent facility exists, run grounding inline and say so in one line.
- Failure recovery is prime isolation territory: hand the subagent the failing
  command and its output, and let it search help, packs, and scripts. The decision
  thread receives the diagnosis and the matching recovery row, not the grep noise.
