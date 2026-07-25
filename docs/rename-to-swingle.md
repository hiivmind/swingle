# Backlog — rename `sdd-dispatch` → **Swingle**

**Status:** W1–W5 implemented in v2.0.0 (2026-07-25), pending release; W6 (repo rename — a release prerequisite — + external refs) and W7 (visual identity) outstanding
**Decided:** 2026-07-23
**Target version:** v2.0.0 (breaking — plugin identity changes)

> **2026-07-25 resolutions:** Q2 — rename the GitHub repo in place (301 redirect).
> Q4 — resolved by events; Grok shipped as v1.6.0 long before the rename branch. W3
> amended: instead of a pure no-op it ships the portable self-migration guide in
> `docs/migration-2.0.0.md`. Branding: the "Greedy Cup" doctrine and milkshake epigraph
> are dropped — all branding derives from the swingletree concept.


---

## The decision

The plugin is renamed **Swingle**, tagline **"share the load"**.

'Swingle' is derived from 'Swingletree' - a swingletree is the pivoting crossbar in a horse harness that equalises pull between
draft animals of unequal strength. Hitch a shire and a pony to one load and the bar
rotates until neither is over-pulled. That is the role of this plugin, for coding agent harnesses.

The rename is not cosmetic. It marks a scope change that already happened: the plugin
began as a wrapper for subagent-driven development and is now a **local harness-to-harness
dispatcher** — Claude Code, Codex, Antigravity, Grok, Pi, OpenCode — with model tiering
and token thrift as the point. `sdd-dispatch` describes the origin, not the product.

### Vocabulary that ships with the rename

| Use | Not |
|---|---|
| **harness** — the unit of dispatch (Claude Code, Codex, agy…) | "provider" (a billing entity), "model" (weights) |
| **dispatch** | "route" |
| **local dispatch, no proxy, no key custody** | "gateway", "upstream", "endpoint" |

`llm-router` / `llm-gateway` stay in package **keywords** for search discovery only, never
in prose.

The differentiator to lead the README with: **a router is a hop** (OpenRouter, LiteLLM,
Portkey proxy your traffic and hold your keys); **Swingle spawns processes locally**
against credentials the user already holds. Nothing enters the prompt path.

---

## Rule 0 — rename `sdd-dispatch`, keep `sdd`

`sdd` currently means **two different things** and only one of them is renaming:

1. **`sdd-dispatch` — the product name.** → becomes `swingle`. Rename freely.
2. **`SDD` — subagent-driven development, a methodology** (cf. the upstream
   `superpowers:subagent-driven-development` skill). A real domain term that exists
   independently of this plugin. It **stays**, everywhere, unchanged.

So `skills/sdd/SKILL.md` — "execute an implementation plan via SDD" — describes a
methodology, not the product. Prose like "applies the SDD optimizations mechanically"
survives the rename intact, and the `/sdd` skill keeps its name (Q1, resolved).

**The rename resolves an overloading rather than creating one.** Today `sdd` is doing
two jobs and the reader has to infer which. Afterwards: *Swingle* is the thing,
*SDD* is the method it applies. The relationship to superpowers' SDD becomes explicit
instead of implied by a shared prefix.

Mechanically: rename the hyphenated compound `sdd-dispatch` (and `sdd_dispatch`,
`SDD Dispatch`). Leave bare `sdd` / `SDD` alone. A naive `sed s/sdd/swingle/g`
corrupts the doctrine — every hit gets read.

---

## Workstream 1 — Identity and manifests

- [ ] `.claude-plugin/plugin.json` — `name`, `description`, `keywords`, bump to `2.0.0`
- [ ] `.claude-plugin/marketplace.json` — marketplace `name`, plugin `name`, `description`
- [ ] `.codex-plugin/plugin.json` — `name`, `description`, `repository`, `keywords`,
      and the whole `interface` block (`displayName`, `shortDescription`,
      `longDescription`, `websiteURL`)
- [ ] `.agents/plugins/marketplace.json`
- [ ] Rewrite descriptions to the new positioning — these are not find-replace targets.
      Current text sells "subagent-driven development via external CLIs"; new text sells
      "dispatch work across agent harnesses, locally."

## Workstream 2 — Skills (user-facing invocation surface)

Renaming a skill changes what the user types. Decide each deliberately (see Open
Questions).

- [ ] `skills/sdd-dispatch-verify/` → `skills/swingle-verify/` (product-named, clear
      rename) — directory, `SKILL.md` frontmatter `name`/`description`, `agents/openai.yaml`
- [x] `skills/sdd/` — **keeps its name.** It executes a plan via SDD-the-methodology,
      which is exactly what `/sdd` should mean. Update its prose where it refers to the
      *product*; leave every methodology reference alone.
- [ ] `skills/delegate/` — unaffected, but check its prose for product-name references
- [ ] `skills/sdd/harnesses/*.md` — the `harnesses/` directory name is now *load-bearing
      vocabulary*. Good. Leave it, and lean on it elsewhere.

## Workstream 3 — State directory — **no action**

`.sdd-dispatch/` is the run-state dir (dispatch logs, contracts, ledger, PID/marker
files). **It stays as-is.** No rename, no compat shim.

Rationale: sole user, plugin is a day old, and `sdd` still legitimately names the
methodology whose state this is. Renaming it would touch `core/`, `contracts/`,
`skills/*/SKILL.md`, `scripts/` and `.gitignore` for zero benefit and a non-zero chance
of orphaning a live ledger.

Revisit only if the directory name starts confusing someone — a trivial, reversible
change at any later point.

## Workstream 4 — Docs and doctrine

- [ ] `README.md` — full rewrite, not a rename. New positioning, harness vocabulary,
      local-dispatch differentiator up top, the Greedy Cup doctrine section, the
      "share the load" tagline, `"I drink your milkshake"` as a one-line epigraph.
- [ ] `CLAUDE.md` (repo) — product name, paths, skill names
- [ ] `core/roles.md`, `core/playbook.md`, `core/safety-doctrine.md`, `core/liveness.md`
- [ ] `contracts/*.md` — four contract files
- [ ] `codex/INSTALL.md`
- [ ] `providers/*/pack.md` — check for product-name references
- [ ] `docs/migration-2.0.0.md` — **new**. Follow the `docs/migration-1.2.0.md` precedent:
      what changed, what breaks, how to re-install, state-dir migration.

### Do NOT rewrite

- `archive/v1.1/**` — historical record of a shipped version
- `docs/sol-*.md` — dated review artefacts
- `core/verification-log.md`, `providers/*/verification-log.md` — **append-only by
  doctrine**. Add a new dated entry noting the rename; never edit prior entries.
- Git history

## Workstream 5 — Code, tests, CI

- [ ] `scripts/validate-packs`, `scripts/codex-smoke`
- [ ] `tests/test_delegate_skill.py`, `tests/test_validate_packs.py`
- [ ] `tests/fixtures/**` — check for hardcoded state-dir or product-name strings
- [ ] `.github/workflows/ci.yml`
- [ ] `.github/ISSUE_TEMPLATE/verification-finding.md`
- [ ] Full `pytest` green before the PR

## Workstream 6 — Repo, distribution, and the world outside this repo

- [ ] Rename GitHub repo `discreteds/sdd-dispatch-plugin` → `discreteds/swingle`.
      GitHub 301-redirects the old path, so existing git remotes keep working — but the
      marketplace cache dir (`~/.claude/plugins/cache/sdd-dispatch-marketplace`) is
      keyed on the old name and users must re-add the marketplace.
- [ ] `~/.claude/CLAUDE.md` — the **"SDD Delegation & Model Tiering"** section names the
      plugin, its skills, and the GitHub URL. Outside this repo; easy to forget.
- [ ] Memory: `agy-antigravity-dispatch.md` references the plugin by name.
- [ ] Local checkout dir `~/git/mountainash-io/mountainash/sdd-dispatch-plugin`
- [ ] Any `.claude/settings.json` referencing the marketplace

## Workstream 7 — Visual identity

- [ ] Retire `docs/images/hero-banner.jpg`; the `feature/hero-logo` branch is now stale
- [ ] **Mark**: the swingletree bar — a pivoting crossbar with traces fanning to N points.
      Monochrome-capable, favicon-safe, scales to a marketplace tile. Does not change
      when the harness roster changes.
- [ ] **Hero illustration**: cartoon multi-horse draught team + dray, harness names on
      brass nameplates/collars (not pasted provider logos). Horses drawn at **different
      sizes** — a shire beside a pony, traces taut, bar level — because that renders the
      tiering thesis with no copy. Cart loaded with casks, tying back to the drinking
      lineage the name came from. This asset is *expected* to be redrawn as harnesses
      come and go; that is why it is separate from the mark.

---

## Breaking changes (for the migration doc)

1. Plugin name changes → re-install; existing marketplace entry goes stale.
2. One skill invocation changes → `/sdd-dispatch-verify` becomes `/swingle-verify`.
   `/sdd` and `/delegate` are unaffected.
3. Repo URL changes → 301-redirected, but update remotes and any pinned marketplace source.

State directory is unchanged, so no run-state migration.

## Out of scope

- **A `swing` CLI binary.** There is no binary today and this rename does not add one.
  The command surface (`swing dispatch`, `swing lane`, `swing budget`) is an idea, not a
  commitment — capture separately if wanted.
- **The harness capability model** (portable job spec + support matrix). This is the real
  outstanding design work, but it is independent of the rename and should not be smuggled
  into it. Separate backlog item.
- Any behaviour change. This release renames and repositions; it does not alter dispatch.

---

## Open questions — decide before starting

**Q1. Does `skills/sdd/` keep its name?** — **RESOLVED: yes.** It executes a plan via
SDD-the-methodology, and keeping it disambiguates the product from the method rather than
overloading one word with both.

**Q3. State-dir migration?** — **RESOLVED: no migration.** `.sdd-dispatch/` stays.

**Q2. Rename the GitHub repo, or create a fresh one?**
Rename preserves stars, issues, history and gives a 301. A fresh repo gives a clean
narrative but abandons all of it. Rename is the obvious call unless there's a reason not to.

**Q4. Branch and sequencing.**
`feature/grok-provider` is currently checked out with a clean tree and unmerged work
(v1.6.0 Grok pack design). Does the rename land **before** Grok (so Grok ships as
Swingle) or **after** (so the rename is a clean isolated diff)? Recommendation:
after — merge Grok first, then rename as its own v2.0.0 PR with nothing else in it.

---

## Suggested sequence

1. Land the in-flight Grok work (Q4)
2. Manifests + identity (W1)
3. Skills, with tests green (W2, W5)
4. Docs rewrite + migration doc (W4)
5. Repo rename and outside-the-repo references (W6)
6. Visual identity, on its own branch (W7)

Steps 2–4 are one PR. Step 5 is a click plus follow-ups. Step 6 is independent.
W3 is a no-op.
