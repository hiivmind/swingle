# README Rewrite — Convenience-First Positioning + Adversarial-Review Fixes

**Status:** Design approved 2026-07-25, pending spec review
**Target:** `README.md` on `develop` (v2.0.0), plus repo description (done) and hero image wiring
**Driver:** `docs/swingle-readme-adversarial-review.md` (10 prioritised findings) + owner's convenience-first reframing

## Goal

Reposition the Swingle README around **convenience** — you never leave the coding-agent
harness you drive to use another provider — and remove the claims the adversarial review
found false or unsupported. Keep every claim that survived the review. This is a
substantial prose rewrite of most sections; sections that held up are preserved.

## Positioning spine (the order claims are made)

1. **Convenience (the lead).** Stay in the harness you like; reach every other installed
   CLI in one sentence — *"ask Antigravity to produce a logo based on the principles in our
   README."* The one-line ask is the surface; the **delegation handoff** underneath is where
   the value is, and it gets its own section (below) — the hero only teases it, it does not
   explain it here.
1a. **The delegation handoff (the magic — its own section).** The point is NOT merely
   "type a sentence." It is what Swingle does with that sentence: infer the role, select the
   model tier for the task, brief the target CLI with an **operating contract** and specific
   instructions, hand it a **return contract** (status vocabulary + report shape), run it
   under the liveness protocol, and gate the result on evidence before it comes back. A
   one-liner becomes a **first-class, fully-briefed subagent** that returns structured work —
   not a raw prompt forwarded to an endpoint. This section must *show* that pipeline; the
   convenience lead must not sell it short by stopping at "just ask."
2. **Capability / fair comparison (≈4 sentences).** A model-endpoint tool (`llm`, LLM
   routers/gateways) hands you an *endpoint or a model* — you still author the harness
   (agent loop, tools, sandbox, contracts). Swingle dispatches **whole harnesses you
   already have installed**. One line on why cross-harness beats staying inside one
   harness's own subagents.
3. **Economics (demoted, honest).** Tier the model to each task instead of running one
   premium model for everything. A **measured token/cost delta is a stated future goal**,
   not a proven claim (see Out of Scope). No "token thrift is the point" as a headline.
4. **Rigor (what held up).** Manifest-driven, zero `core/` edits (validator-backed);
   controller hard gates; the `report-transport` + recording-ladder honesty; harness /
   provider / model vocabulary discipline.

## Claims to REMOVE (review §1) and their replacements

| Remove (false/unsupported) | Replacement | Finding |
| --- | --- | --- |
| "LLM routers and gateways proxy your traffic and hold your keys" | Deleted as a differentiator. Router contrast becomes *unit of dispatch*: they give you a model/endpoint; Swingle gives you a whole installed harness. | 1.1 |
| "A router is a hop; Swingle is a hitch" (as load-bearing) | Cut from the README prose (the banner already dropped it); if any hitch/harness flavour remains, it attaches to the surviving unit-of-dispatch claim, never to key-custody. | 1.2 |
| "Nothing enters the prompt path" | "No third party in the prompt path." (Swingle itself injects doctrine/contracts — say *third party*.) | 1.3 |
| "fully local" / "local dispatch" implying local weights | "local **orchestration** — inference still runs on the remote frontier models you're authenticated to." | 1.4 |
| "Everything is self-contained. No machine-specific paths are required" | "self-contained **within this repository** — no machine-specific paths in the packs themselves," + explicit superpowers dependency up front. | 1.5 |
| "harness-neutral" (unqualified) | State per-harness support honestly; move opencode's footgun detail to a link so the body isn't 600 words of asymmetry. | 1.6 |
| Front-matter "six harnesses" vs repo "three packs" | State all **6** harnesses (Claude Code, Codex, Antigravity/agy, Grok, Pi, opencode) with **per-harness verification status**. Repo description already updated. | 1.7 |

## Section outline (final)

1. **Hero** — banner (`docs/images/hero-banner.svg`, promoted from `agy-merged-v6.svg`),
   title, tagline "Share the load across model providers.", the convenience lead, the
   worked-example sentence, swingletree story trimmed to 1–2 lines, `**Version:** 2.0.0`.
2. **The delegation handoff** (new, load-bearing) — the magic, per spine 1a. Walk the
   pipeline a single sentence triggers: role inference → model-tier selection → operating
   contract + specific instructions → **return contract** (status vocab + report shape) →
   liveness-protocol run → evidence gate → structured report back. Show it concretely
   (the logo ask is a real, lived example). This is the section that must not undersell the
   framework — the convenience of "just ask" is the doorway; the briefed, contract-bound,
   tiered handoff is the room.
3. **What Swingle isn't** (~4 sentences) — the `llm`/router fair comparison (endpoint vs
   whole harness) + why cross-harness beats one harness's own subagents. Disambiguation,
   not a headline war (review §4).
4. **Vocabulary** — promote harness / provider / model discipline (review §6).
5. **Requirements & install** — dependencies loud up front (superpowers plugin; the CLIs
   you use on PATH, each **authenticated once interactively** → therefore **no headless /
   CI / ephemeral-runner** use without a seeded credential store, review #10); all 6
   harnesses with verification status; "self-contained within this repo"; Claude Code /
   Codex / opencode install kept, but opencode's footgun detail (Route A/B cache warning,
   env-var caveats, grep verification) trimmed to a short pointer to the existing
   `skills/sdd/harnesses/opencode.md`, which already documents that behaviour — so the
   README body stops reading as 600 words of asymmetry.
6. **Skills** — sdd / delegate / swingle-verify. **Credit superpowers explicitly**: the
   `sdd` skill **rides along with `superpowers:subagent-driven-development`** — it wraps that
   methodology and depends on the superpowers plugin being installed; say so plainly and give
   credit (this also satisfies review 1.5's "own the dependency loudly"). By contrast,
   `delegate` works **more directly and does NOT require superpowers** — no superpowers skill
   invoked, no `.superpowers/` dependency — which is exactly why the delegation-handoff
   section (§2) and the worked example route through `delegate`, not `sdd`. Make the split
   unmistakable: sdd = plan execution on top of superpowers; delegate = standalone one-shot
   dispatch with no superpowers dependency.
7. **Safety & trust** (new) — honest threat model: what the evidence gates
   (staged + untracked + HEAD-unchanged) defend against and what they **do not**;
   dispatched agents run real tools and edits; read-only is opt-in; prompt-injection via
   repository content an agent reads is a real surface; supervision trigger stated plainly.
   Demote "a manifest can never smuggle in a command" from headline to a footnote (it
   closes a narrow surface, review §3).
8. **Model tiering & economics** — demoted, honest (see spine 3); keep model-tables /
   overrides (held up).
9. **Adding a harness pack** — promoted: lead the technical section with "zero `core/`
   edits, manifest-driven" (falsifiable, validator-backed, review §6).
10. **Model tables and overrides** — keep (held up).
11. **Reporting verification findings / recording ladder** — keep (held up).
12. **Seat economics & degradation** (new, short) — the flat-rate-seat moat + ToS reality;
    one-line degradation story (packs fall back to API-keyed dispatch); frame as
    *orchestration*, not *arbitrage* (review §5).

## Preserve verbatim (survived the review, §6)

- "Adding a pack requires zero edits to `core/`; routing is manifest-driven."
- The `report-transport` paragraph ("a report-file request fails *intermittently* while
  the exit code stays 0").
- The recording ladder ("A finding recorded only in an installed cache is a finding lost").
- The harness / provider / model vocabulary definitions.
- "A malformed override is a hard error, never a silent fall-through."

## Out-of-file changes in the same PR

- **Repo description** — already updated to the convenience-first framing (2026-07-25).
- **Hero image** — promote `.sdd-dispatch/delegate/concepts/agy-merged-v6.svg` →
  `docs/images/hero-banner.svg` (tracked) and reference it in §1. (The old
  `docs/images/hero-banner.jpg`, if present, is retired — do not delete unless confirmed.)

## Constraints

- **Honesty over polish.** Every claim must survive a hostile reader. No absolutes
  ("never", "nothing", "fully") next to a surface the architecture contradicts.
- **Vocabulary lock** — harness = unit of dispatch; provider = billing entity; model =
  weights. (Note: the banner byline "across model providers" is an owner-chosen marketing
  line and stays as-is on the image; README prose keeps the disciplined nouns.)
- **The gate still applies** — `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`
  must pass; `**Version:** 2.0.0` must survive (validator syncs it against `plugin.json`).
- Keep all deliberately-kept `.sdd-dispatch/` state/config paths intact.

## Out of scope (captured, not dropped)

- **The measured token/cost benchmark (review #1).** A real plan executed all-Opus vs
  tiered-across-harnesses with ledger + cost delta. This is the highest-value follow-up and
  its own project; the README states it as a future goal and links a tracking issue.
- **W7 visual identity** beyond wiring the current banner (full brand mark, favicon set).

## Success criteria

- A re-run of the adversarial review finds findings 1.1, 1.3, 1.4, 1.5, 1.6, 1.7, #10
  closed; §3 (threat model) and §5 (ToS/degradation) addressed; #1 (benchmark) honestly
  marked as future, not asserted.
- The gate passes and the full test suite is green.
- A hostile 30-second reader lands on **convenience**, not a falsifiable cost claim.
