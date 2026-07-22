# SDD Roles and Tiers

> Living policy. The role-to-tier table below is the authority the SDD workflow reads at
> setup; each provider pack supplies its own eligible model mapping.

## Role → tier → lane → mode

| SDD role | Tier | Lane | Mode |
| --- | --- | --- | --- |
| Transcription implementer (complete code in brief) | cheapest | implement | bg, write |
| Adaptation implementer (prose/design/debug) | standard | implement | bg, write |
| Large-codebase / long-context implement | most-capable | implement | bg, write |
| Read-only codebase explore ("where is X") | cheapest | review | bg, read-only* |
| External research / synthesis (long-context) | standard | review | bg, read-only* |
| Per-task reviewer (spec + quality, scale to diff) | standard | review | bg, read-only* |
| Final whole-branch / design review | most-capable | review | bg, read-only* |

\* "read-only" is an intent unless an enforced sandbox provides the review lane. Otherwise:
clean tree before, diff after (see safety doctrine).

**Tiering rules:**

- **Turn count beats token price** — cheapest models take 2–3× the turns on multi-step work;
  standard is the floor for reviewers and prose-brief implementers.
- Scale reviewer power to the **diff's** size/risk. Final whole-branch review is
  architecture-class — always most-capable.
- Prefer the verified, contained lane for structured code/design reviews; reach for other
  provider packs for perspective diversity.

Tier→model mapping lives in each pack's models.md — resolution algorithm and status eligibility in the spec §Resolution algorithm; priority 1 = default, ascending = fallback, only Status verified/experimental resolve.
