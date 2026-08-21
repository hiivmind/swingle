---
name: swingle-sdd
description: >-
  Execute a written implementation plan through subagent-driven-development with
  swingle-delegate at each external dispatch point. Use for plan execution; keep the
  installed workflow as the authority for planning, task order, reviews, and completion.
  Triggers: "run this plan with SDD", "/swingle-sdd", "/sdd", "execute the plan via
  subagents", and the Standard Delivery Flow reaching its execute step.
---

# SDD Through Swingle Delegate

Run the installed `subagent-driven-development` workflow. That workflow is the sole authority for planning, task order, reviews, fixes, and completion.

At each external dispatch point, use `swingle-delegate`. Pass the current task brief, role, working directory, inputs, report requirement, and exact SDD run-ledger path.

The delegate initializes and appends provider, model or provider-default, session when available, attempt, status, and outcome to that exact path.

Do not add a second setup, worktree, review, liveness, model, or provider-validation process.
