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

- **The model is always passed explicitly on every dispatch.** A dispatch that omits the
  model flag does not fall back to a documented default — it inherits whatever model the
  caller's own session is running, which is typically the most expensive tier available.
  The dispatch still succeeds, the report still arrives, and the log looks normal, so the
  failure is silent: tiering is defeated and nothing surfaces it. Every pack's canonical
  dispatch template carries the model flag for this reason; never strip it, and never
  treat "the pack's default" as a thing that exists at dispatch time.
- **Turn count beats token price** — cheapest models take 2–3× the turns on multi-step work;
  standard is the floor for reviewers and prose-brief implementers.
- Scale reviewer power to the **diff's** size/risk. Final whole-branch review is
  architecture-class — always most-capable.
- Prefer the verified, contained lane for structured code/design reviews; reach for other
  provider packs for perspective diversity.
- **Calibrate the tier on the batch's first item, don't guess it for all of them.** When
  more than ~3 near-identical items are queued, run the first one at two adjacent tiers and
  compare the results behind the same controller gate that would have accepted either. The
  gate already reads both outputs, so the comparison costs one extra cheap dispatch and
  produces evidence for the remaining items instead of a guess repeated N times. Judge on
  what the gate cares about — did it clear the bar, in how many turns, with how much
  controller adjudication — not on prose polish. Record the outcome as a model-attempt line
  in the ledger; a tier that loses an A/B on one class of work is not thereby disqualified
  for others.

Tier→model mapping lives in each pack's models.yaml — the table of record, resolved through the layered override walk (env → project → user → pack default; whole-file precedence) — resolution algorithm and status eligibility in the spec §Resolution algorithm; priority 1 = default, ascending = fallback, only Status verified/experimental resolve. models.md carries the narrative.
