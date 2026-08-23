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
- If no subagent facility exists, run grounding inline and say so in one line.
- Failure recovery is prime isolation territory: hand the subagent the failing
  command and its output, and let it search help, packs, and scripts. The decision
  thread receives the diagnosis and the matching recovery row, not the grep noise.
