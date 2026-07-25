# Rename to Swingle (v2.0.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the plugin `sdd-dispatch` → `swingle` (v2.0.0) across manifests, skills, docs, and scripts, repositioned as a local harness-to-harness dispatcher — with zero behaviour change.

**Architecture:** Pure rename + repositioning per `docs/superpowers/specs/2026-07-25-rename-to-swingle-design.md`. Six sequential tasks on `feature/rename-to-swingle` (already created off `develop`), each a gate-green commit. No code paths, state directories, or config file locations change.

**Tech Stack:** Markdown, JSON manifests, YAML skill metadata. Gate: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke`. Tests: `uv run --with pytest pytest tests/ -q`.

## Global Constraints

- **Rule 0 — rename map.** `sdd-dispatch` → `swingle`; `sdd_dispatch` → `swingle`; `SDD Dispatch` → `Swingle`; `sdd-dispatch-marketplace` → `swingle-marketplace`; `sdd-dispatch-verify` (skill) → `swingle-verify`; repo URL `discreteds/sdd-dispatch-plugin` → `discreteds/swingle`. **Never** rename bare `sdd` / `SDD` (the methodology and the `/sdd` skill).
- **STAYS — never touch these strings anywhere:** `.sdd-dispatch/` (state dir, all uses incl. `.sdd-dispatch/delegate/`, `.sdd-dispatch/models/`), `.sdd-dispatch.json`, `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, `$SDD_DISPATCH_MODELS`, `.gitignore` line 4. Renaming these is a behaviour change and out of scope. Consequence: `scripts/sdd-models`, `tests/test_delegate_skill.py`, `tests/test_validate_packs.py`, `tests/fixtures/**`, and `scripts/validate-packs` lines 144/146/225 need **no edits** (only the validate-packs line-2 docstring changes, Task 3).
- **HISTORICAL — never rewrite:** `archive/**`, `docs/sol-*.md`, `docs/migration-1.2.0.md`, `docs/migration-1.8.0.md`, `docs/superpowers/specs/2026-07-2[234]-*.md`, `docs/superpowers/plans/2026-07-2[34]-*.md`, any existing verification-log **entry** (logs get one appended entry, Task 5; H1 titles are historical identity lines and stay).
- **Branding:** swingletree / draught-harness concept only. Tagline **"share the load."** The "Greedy Cup" doctrine and the milkshake epigraph are dropped (owner decision 2026-07-25) — do not add them.
- **Vocabulary in new prose:** "harness" (unit of dispatch), "dispatch" (not "route"), "local dispatch, no proxy, no key custody" (not "gateway"/"upstream"). `llm-router`/`llm-gateway` appear in manifest keywords ONLY, never prose. Physical paths (`providers/<id>/`, manifest field names) do NOT change.
- **Every commit:** `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && git commit ...` — chained with `&&`, never `;`.
- Version `2.0.0` must appear in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, AND the README `**Version:**` line in the SAME commit (the validator enforces sync — Task 1 does all three).

---

### Task 1: Manifests + version bump (W1)

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.agents/plugins/marketplace.json`
- Modify: `README.md:12` (version line ONLY — full rewrite is Task 4)

**Interfaces:**
- Produces: plugin name `swingle`, marketplace name `swingle-marketplace`, version `2.0.0`, repo URL `https://github.com/discreteds/swingle`. Tasks 2–5 use these exact strings.

- [ ] **Step 1: Replace `.claude-plugin/plugin.json` content with:**

```json
{
  "name": "swingle",
  "version": "2.0.0",
  "description": "Share the load: dispatch implementation and review work across coding-agent harnesses (codex/opencode/agy/grok/pi/claude), locally — model tiering, token thrift, liveness protocol, and a verified per-harness knowledge base",
  "author": {
    "name": "Nathaniel Ramm",
    "email": "nathaniel.ramm@discretedatascience.com"
  },
  "license": "MIT",
  "keywords": [
    "swingle",
    "harness",
    "dispatch",
    "subagents",
    "model-tiering",
    "sdd",
    "codex",
    "opencode",
    "antigravity",
    "grok",
    "llm-router",
    "llm-gateway"
  ]
}
```

- [ ] **Step 2: Replace `.claude-plugin/marketplace.json` content with:**

```json
{
  "name": "swingle-marketplace",
  "owner": {
    "name": "Nathaniel Ramm"
  },
  "plugins": [
    {
      "name": "swingle",
      "source": "./",
      "description": "Local harness-to-harness dispatch with model tiering and a verified dispatch knowledge base"
    }
  ]
}
```

- [ ] **Step 3: Replace `.codex-plugin/plugin.json` content with:**

```json
{
  "name": "swingle",
  "version": "2.0.0",
  "description": "Share the load: dispatch implementation and review work across coding-agent harnesses (codex/opencode/agy/grok/pi/claude), locally, through validated packs — no proxy, no key custody.",
  "author": {
    "name": "Nathaniel Ramm"
  },
  "repository": "https://github.com/discreteds/swingle",
  "keywords": [
    "swingle",
    "harness",
    "dispatch",
    "subagent",
    "orchestration",
    "sdd",
    "llm-router",
    "llm-gateway"
  ],
  "skills": "./skills/",
  "interface": {
    "displayName": "Swingle",
    "shortDescription": "Dispatch work across coding-agent harnesses through validated packs, locally",
    "longDescription": "Swingle is a local harness-to-harness dispatcher: it executes implementation plans and one-off jobs through external-CLI subagents (codex, opencode, agy, grok, pi, claude) with manifest-driven routing, model tiering, liveness protocol, controller hard gates, and an append-only verification knowledge base. It spawns processes locally against credentials you already hold — no proxy, no key custody.",
    "developerName": "Nathaniel Ramm",
    "category": "Developer Tools",
    "capabilities": [
      "Read",
      "Write"
    ],
    "websiteURL": "https://github.com/discreteds/swingle"
  }
}
```

- [ ] **Step 4: Replace `.agents/plugins/marketplace.json` content with:**

```json
{
  "name": "swingle-marketplace",
  "interface": {
    "displayName": "Swingle Marketplace"
  },
  "plugins": [
    {
      "name": "swingle",
      "source": {
        "source": "local",
        "path": "./"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Developer Tools"
    }
  ]
}
```

- [ ] **Step 5: In `README.md` change line 12** `**Version:** 1.9.2` → `**Version:** 2.0.0`. Touch nothing else in the README.

- [ ] **Step 6: Gate + tests + commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
uv run --with pytest pytest tests/ -q && \
git add .claude-plugin .codex-plugin .agents README.md && \
git commit -m "feat(identity)!: rename plugin to swingle, v2.0.0 manifests"
```

Expected: gate PASS lines, pytest all green. If the validator complains about a name/version sync rule beyond these five files, read its message and fix within this task — do not defer.

---

### Task 2: Skill rename `sdd-dispatch-verify` → `swingle-verify` (W2)

**Files:**
- Rename: `skills/sdd-dispatch-verify/` → `skills/swingle-verify/` (via `git mv`)
- Modify: `skills/swingle-verify/SKILL.md`, `skills/swingle-verify/agents/openai.yaml`
- Modify: `skills/sdd/SKILL.md:69`, `skills/delegate/SKILL.md:89`
- Modify: `skills/sdd/harnesses/grok.md:5`, `skills/sdd/harnesses/opencode.md:5`, `skills/sdd/harnesses/pi.md:12,20`

**Interfaces:**
- Consumes: names from Task 1 (`swingle`, `swingle-marketplace`, `discreteds/swingle`).
- Produces: skill invocation `swingle-verify` — Tasks 3–5 reference it.

- [ ] **Step 1:** `git mv skills/sdd-dispatch-verify skills/swingle-verify`

- [ ] **Step 2: Edit `skills/swingle-verify/SKILL.md`:**
  - Frontmatter `name: sdd-dispatch-verify` → `name: swingle-verify`.
  - Frontmatter description: `Re-verify one SDD dispatch provider pack, or all active packs,` → `Re-verify one Swingle provider pack, or all active packs,` (rest of the sentence unchanged).
  - Title `# SDD Dispatch Verification` → `# Swingle Verification`.
  - Line 35: `the repo for \`https://github.com/discreteds/sdd-dispatch-plugin\`` → `the repo for \`https://github.com/discreteds/swingle\``.
  - Lines 39–40: `codex plugin marketplace upgrade sdd-dispatch-marketplace` → `codex plugin marketplace upgrade swingle-marketplace`; `codex plugin add sdd-dispatch@sdd-dispatch-marketplace` → `codex plugin add swingle@swingle-marketplace`.
  - Lines 47, 59, 62: `--repo discreteds/sdd-dispatch-plugin` → `--repo discreteds/swingle`; `gh api repos/discreteds/sdd-dispatch-plugin/...` → `gh api repos/discreteds/swingle/...`.
  - Read the whole file to the end; apply the same three substitution families to any hit below line 70.

- [ ] **Step 3: Replace `skills/swingle-verify/agents/openai.yaml` content with:**

```yaml
interface:
  display_name: "Swingle Verify"
  short_description: "Re-verify one Swingle provider pack (or all active packs) against live CLI behavior after a version bump, model release, or anomaly."
  default_prompt: "Re-verify the named provider pack with swingle-verify."

policy:
  allow_implicit_invocation: false
```

- [ ] **Step 4: Update referring skills (methodology prose stays):**
  - `skills/sdd/SKILL.md:69`: `` warn and suggest `sdd-dispatch-verify <id>` `` → `` warn and suggest `swingle-verify <id>` ``. (Lines 62/78/79 are config paths — do not touch.)
  - `skills/delegate/SKILL.md:89`: `` warn and suggest `sdd-dispatch-verify <id>` `` → `` warn and suggest `swingle-verify <id>` ``. (All other hits in this file are `.sdd-dispatch/` paths — do not touch.)
  - `skills/sdd/harnesses/grok.md:5`: `(plugin: sdd-dispatch)` → `(plugin: swingle)`; `` `delegate` / `sdd-dispatch-verify` `` → `` `delegate` / `swingle-verify` ``.
  - `skills/sdd/harnesses/opencode.md:5`: `skill(sdd-dispatch-verify)` → `skill(swingle-verify)`.
  - `skills/sdd/harnesses/pi.md:12`: `` same for `delegate` / `sdd-dispatch-verify` `` → `` same for `delegate` / `swingle-verify` ``.
  - `skills/sdd/harnesses/pi.md:20`: `pi install https://github.com/discreteds/sdd-dispatch-plugin` → `pi install https://github.com/discreteds/swingle`. (Line 14's `.sdd-dispatch/delegate/ledger.md` — do not touch.)

- [ ] **Step 5: Verify nothing else references the old skill path:**

```bash
grep -rn 'sdd-dispatch-verify' skills/ scripts/ tests/ contracts/ core/ providers/*/pack.md providers/*/models.md .github/ || echo CLEAN
```

Expected: `CLEAN` (verification-log historical entries are excluded from this scope on purpose; README/CLAUDE.md/codex/INSTALL.md hits are Tasks 3–4).

- [ ] **Step 6: Gate + tests + commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
uv run --with pytest pytest tests/ -q && \
git add -A skills/ && \
git commit -m "feat(skills)!: rename sdd-dispatch-verify skill to swingle-verify"
```

pytest must be fully green — `tests/test_delegate_skill.py` structural assertions (exactly one negative-disclaimer mention each of the superpowers strings) must not be disturbed by the delegate edit.

---

### Task 3: Doctrine, CLAUDE.md, codex/INSTALL.md, script docstring (W4 part 1 + W5)

**Files:**
- Modify: `CLAUDE.md:1,51,70`
- Modify: `core/verification-protocol.md:1,114,120`
- Modify: `codex/INSTALL.md` (lines 15–16, 20, 26–27, 41–44, 49)
- Modify: `scripts/validate-packs:2`

**Interfaces:**
- Consumes: `swingle`, `swingle-marketplace`, `swingle-verify`, `discreteds/swingle` from Tasks 1–2.

- [ ] **Step 1: `CLAUDE.md`:** line 1 `# CLAUDE.md — sdd-dispatch plugin` → `# CLAUDE.md — swingle plugin`; line 51 `` re-verify with `sdd-dispatch-verify <id>` `` → `` re-verify with `swingle-verify <id>` ``; skills-table row `` | `sdd-dispatch-verify` | `` → `` | `swingle-verify` | ``. Line 69's `.sdd-dispatch/delegate/` stays.

- [ ] **Step 2: `core/verification-protocol.md`:** line 1 `# SDD Dispatch Verification Protocol` → `# Swingle Verification Protocol`; line 114 `(sdd-dispatch-verify Procedure step 0)` → `(swingle-verify Procedure step 0)`; line 120 `--repo discreteds/sdd-dispatch-plugin` → `--repo discreteds/swingle`. Purity boundary check: no model ids or invocation strings may be introduced — these three edits add none.

- [ ] **Step 3: `codex/INSTALL.md`** — apply throughout:
  - `codex plugin marketplace add discreteds/sdd-dispatch-plugin` → `codex plugin marketplace add discreteds/swingle`
  - `codex plugin add sdd-dispatch@sdd-dispatch-marketplace` → `codex plugin add swingle@swingle-marketplace`
  - `codex plugin marketplace upgrade sdd-dispatch-marketplace` → `codex plugin marketplace upgrade swingle-marketplace`
  - cache path example `.../sdd-dispatch/<version>/` → `.../swingle/<version>/`
  - clone block: `git clone https://github.com/discreteds/sdd-dispatch-plugin "$HOME/src/swingle"`, symlinks `"$HOME/src/swingle/skills/sdd"` and `ln -s "$HOME/src/swingle/skills/swingle-verify" "$HOME/.agents/skills/swingle-verify"`, update command `git -C "$HOME/src/swingle" pull`. Use the NEW repo URL `https://github.com/discreteds/swingle` in the clone (301 covers the interim).
  - Keep the 2026-07-23 "Verified end-to-end" parenthetical's date and version facts — only the path inside it changes.

- [ ] **Step 4: `scripts/validate-packs` line 2:** `"""sdd-dispatch pack validator/resolver + Step-0 simulator (stdlib only)."""` → `"""swingle pack validator/resolver + Step-0 simulator (stdlib only)."""`. Lines 144/146/225 (`.sdd-dispatch`/`sdd-dispatch` config paths) stay byte-identical.

- [ ] **Step 5: Confirm the zero-hit files really are zero-hit (no edits expected):**

```bash
grep -rn 'sdd-dispatch\|sdd_dispatch\|SDD Dispatch' \
  core/roles.md core/playbook.md core/safety-doctrine.md core/liveness.md \
  contracts/ providers/*/pack.md providers/*/models.md providers/*/models.yaml \
  .github/workflows/ci.yml .github/ISSUE_TEMPLATE/verification-finding.md \
  skills/sdd/harnesses/codex.md skills/sdd/harnesses/claude-code.md || echo CLEAN
```

Expected: `CLEAN`. If any hit appears, apply Rule 0 to it in this task.

- [ ] **Step 6: Gate + commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add CLAUDE.md core/verification-protocol.md codex/INSTALL.md scripts/validate-packs && \
git commit -m "docs+chore: swingle naming in CLAUDE.md, verification protocol, codex install, validator docstring"
```

---

### Task 4: README full rewrite (W4 part 2)

**Files:**
- Modify: `README.md` (full replacement)

**Interfaces:**
- Consumes: all names from Tasks 1–2. The technical sections below were verified against the v1.9.2 README — preserve their facts exactly as written here.

- [ ] **Step 1: Replace `README.md` content in full with:**

````markdown
# Swingle

**Share the load.**

A *swingletree* is the pivoting crossbar in a draught harness that equalises pull
between animals of unequal strength. Hitch a shire and a pony to one load and the bar
rotates until neither is over-pulled. That is what this plugin does for coding-agent
harnesses.

Swingle is a **local harness-to-harness dispatcher**: from whichever harness you are
driving (Claude Code, Codex, opencode, Antigravity's agy, Grok, Pi), it dispatches
implementation and review work to the others as external-CLI subagents, tiering the
model to each task's judgment bar. Token thrift is the point — heavy pulls go to the
strongest harness that clears the bar, light pulls to the cheapest.

**A router is a hop; Swingle is a hitch.** LLM routers and gateways proxy your traffic
and hold your keys. Swingle spawns processes locally against credentials you already
hold — local dispatch, no proxy, no key custody. Nothing enters the prompt path.

Vocabulary, used consistently below: a **harness** is the unit of dispatch (Claude
Code, Codex, agy, …) — not a "provider" (a billing entity) or a "model" (weights). The
on-disk pack directories keep the historical name `providers/<id>/`; each pack
describes one harness.

Everything is self-contained. The `sdd` skill and harness packs are discovered from
this repository; no machine-specific paths are required.

**Version:** 2.0.0

## Install with Claude Code

Requires the `superpowers` plugin and whichever dispatch CLIs you use on PATH
(`codex`, `opencode`, `agy`, `grok`, `pi`, `claude`), each authenticated once interactively.

```text
/plugin marketplace add discreteds/swingle
/plugin install swingle@swingle-marketplace
```

(A local checkout also works: `/plugin marketplace add /path/to/swingle`.)

## Install with Codex

This repository is also a Codex plugin (`.codex-plugin/plugin.json`) with a self-hosted
marketplace:

```bash
codex plugin marketplace add discreteds/swingle
codex plugin add swingle@swingle-marketplace
```

Manual alternative
(clone + symlink into `$HOME/.agents/skills/`) and full details:
[codex/INSTALL.md](codex/INSTALL.md). The Codex entry point is `skills/sdd/SKILL.md`.

## Install with opencode

opencode has no Claude Code plugin loader — its `plugin` config key takes npm packages
and local `.ts` modules only. Plugins reach opencode as **skills trees** instead, which
costs this repository nothing: it ships skills exclusively (no commands, agents, or
hooks). Skills register under their bare frontmatter names (`sdd`, `delegate`,
`swingle-verify`); opencode has no plugin namespace and dedupes by name, so install
by exactly one of the routes below.

### Route A — expose every installed Claude Code plugin (recommended)

If you already run this plugin under Claude Code, the whole plugin set can be handed to
opencode at once. Generate version-pinned `skills.paths` entries from Claude Code's own
install registry:

```bash
scripts/opencode-skills-path --merge ~/.config/opencode/opencode.json   # global
scripts/opencode-skills-path --merge ./opencode.json                    # per-project
```

Run it again after installing, updating, or removing a Claude Code plugin.

**Do not shortcut this by pointing `skills.paths` at `~/.claude/plugins/cache` directly.**
That directory retains every version ever installed (`cache/<marketplace>/<plugin>/<version>/`),
and because opencode dedupes by skill name it will silently register an arbitrary version
per skill — including mismatched versions within a single plugin. Observed on a real
machine: the bare cache path loaded `sdd` 1.0.0 next to `delegate` 1.5.0, and superpowers
6.0.3 while 6.1.1 was the installed version. The script reads `installed_plugins.json` and
emits only the pinned `installPath` of each installed plugin, which resolves all three
correctly.

### Route B — this plugin alone, from a checkout

For a source checkout (or if you do not use Claude Code at all), point `skills.paths` at
the repository's `skills/` directory in `~/.config/opencode/opencode.json` (global) or
`./opencode.json` (per-project). Entries are scanned recursively for `**/SKILL.md`; `~/`
is expanded and relative paths resolve against the working directory.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": ["~/src/swingle/skills"]
  }
}
```

A symlink into `~/.claude/skills/` works too — opencode scans Claude Code's skill
directories by default — but it has two drawbacks Route B avoids: the compat scan is
switched off by `OPENCODE_DISABLE_EXTERNAL_SKILLS` / `OPENCODE_DISABLE_CLAUDE_CODE`, and
skill locations are reported *through* the symlink, so the asset-root derivation in
[skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md) must resolve the
physical path before it can find `core/` and `providers/`.

### After either route

Restart opencode and confirm the skills are registered before first use:

```bash
opencode debug skill | grep -E '"name": "(sdd|delegate|swingle-verify)"'
```

`sdd` wraps `superpowers:subagent-driven-development`, so superpowers must be reachable by
the same route (Route A covers it automatically). Dispatch CLIs (`codex`, `opencode`,
`agy`, `grok`, `pi`, `claude`) must be on PATH and authenticated once interactively, as with the other
harnesses. Harness-specific behaviour — the missing shell background mode, the
`subagent_depth` cap, and session-id attribution when opencode dispatches its own pack —
is documented in [skills/sdd/harnesses/opencode.md](skills/sdd/harnesses/opencode.md).

## Layout

```
skills/sdd/                       # plan-execution skill and harness adapters
skills/delegate/                  # direct one-off dispatch skill (no plan machinery)
skills/swingle-verify/            # CLI re-verification skill
core/                             # shared doctrine, playbook, roles, and logs
providers/<id>/                    # self-contained harness packs
contracts/                         # implementer, task-reviewer, design-reviewer, and reader contracts
codex/INSTALL.md                   # Codex installation instructions
archive/v1.1/                      # verbatim legacy references
references/                        # v1.1 tombstones with migration links
scripts/validate-packs             # pack validator and resolver
scripts/codex-smoke                # Codex layout and validator smoke test
scripts/opencode-skills-path       # opencode skills.paths from installed Claude Code plugins
```

## Skills

| Skill | Purpose |
| --- | --- |
| `sdd` | Execute an implementation plan through the active harness and harness packs |
| `delegate` | Directly dispatch an explicitly requested one-off job or homogeneous batch through the packs — no plan required |
| `swingle-verify` | Re-run the CLI probe suite when versions bump or models release |

`sdd` keeps its name deliberately: it executes plans via **SDD — subagent-driven
development** — a methodology that exists independently of this plugin (see the upstream
`superpowers:subagent-driven-development` skill). Swingle is the product; SDD is a
method it applies.

## Direct delegation

`delegate <task>` dispatches a self-contained job (or homogeneous batch) to an external
CLI with the full pack doctrine — role inference from `core/roles.md`, model tiering,
liveness, hardened evidence gates (staged + untracked + HEAD-unchanged), controller
commits, and session resume — but none of the SDD plan-execution ceremony. Levers:
`via <harness>`, `floor it` / `play it safe` / explicit model, `with review`,
`read-only`, `supervised` / `unsupervised`. Jobs implying ≥3 planned dispatch cycles
run supervised automatically (announced). Artifacts and the lifecycle ledger live in
`.sdd-dispatch/delegate/`, ignored via `.git/info/exclude` (`.sdd-dispatch/models/` is committable project config). The boundary is semantic:
multi-task implementation plans go to the `sdd` skill regardless of how they arrived;
tasks below the triviality floor stay inline unless delegation was explicitly
requested.

## Adding a harness pack

Add one directory under `providers/` satisfying the pack contract:
`pack.md`, `models.yaml` (the model table of record), `models.md` (documentary narrative), and `verification-log.md` with the required manifest fields. Run:

```bash
python3 scripts/validate-packs --root .
```

Adding a pack requires zero edits to `core/`; routing is manifest-driven.

The manifest is the YAML front matter of `pack.md`. Required: `schema-version`, `id`,
`cli`, `verified-version`, `version-argv`, `resume-argv`, `session-source`,
`stall-signal`, `sandbox`. Optional: `fork-flag`, `session-list-argv`,
`readiness-argv`, `readiness-timeout-seconds`, and:

| Field | Values | Meaning |
| --- | --- | --- |
| `report-transport` | `report-file` (default) · `captured-output` | How an agent's report gets back to the controller |
| `list-models-argv` | argv array | How to enumerate an open catalog harness's live model list (e.g. pi). Surfaced by `sdd-models init`, never auto-executed |

Declare `captured-output` when the CLI cannot reliably write an agent-authored file to a
workspace path. The skills then ask for **no file** and take the full report as the
captured final message, saving it themselves. Getting this wrong is not cosmetic: on such
a harness a report-file request fails *intermittently* while the exit code stays 0, so
the report is silently missing and any reviewer downstream loses an input. `agy` is
`captured-output`; `codex`, `opencode`, and `grok` are `report-file`.

Every value is validator-enforced, and `*-argv` arrays are data — `argv[0]` must equal
`cli`, and shell metacharacters are rejected, so a manifest can never smuggle in a
command to execute.

## Model tables and overrides

Each pack ships its model priority table in `providers/<id>/models.yaml` (restricted
YAML: flat header + a list of `tier/lane/priority/model/status[/pricing/rationale]`
rows). At dispatch time the table is resolved per harness, first file found wins
whole-file (no merging):

1. `$SDD_DISPATCH_MODELS/<id>.yaml` (env override — a directory)
2. `<project>/.sdd-dispatch/models/<id>.yaml` (committable, team-shared)
3. `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/models/<id>.yaml` (this machine)
4. the pack default

Seed an override with `scripts/sdd-models init <id> --project <repo>|--user`; inspect
with `scripts/sdd-models which`. Override statuses are your own assertion — the
`verified` stamps in pack defaults come from live dispatch evidence only. A malformed
override is a hard error, never a silent fall-through; an override that omits a
(tier, lane) slot resolves that slot to "no eligible model — ask", which is the
supported way to keep a harness from auto-routing in one project.

## Reporting verification findings

The packs are living documents: CLIs flip behavior between patch releases, models come
and go, and every live dispatch is evidence. Where a finding gets recorded depends on
what you can write to (the **recording ladder** — full rules in
`core/verification-protocol.md` §Recording and the `swingle-verify` skill, step 0):

1. **Writable source checkout** — append to the pack's `verification-log.md`, update the
   pack facts, and commit. Never record into an installed plugin cache (Claude Code
   `~/.claude/plugins/cache/...`, Codex `~/.codex/plugins/cache/...`) — caches are
   clobbered on the next upgrade.
2. **Clone but no push rights** — commit locally and open an issue or PR carrying the
   log entry.
3. **No source tree** (installed copy only) — [open an issue](https://github.com/discreteds/swingle/issues/new?template=verification-finding.md)
   using the **Verification finding** template (`verification` label), one issue per
   independent finding: CLI + plugin version, trigger, the pack assertion under test,
   verdict, verbatim evidence, impact. **Search first**: if an equivalent issue exists,
   a 👍 reaction adds weight to its prioritisation; comment only when you bring a new
   angle or wrinkle not already covered.

A finding recorded only in an installed cache is a finding lost.
````

Notes for the implementer: the hero-banner image line is intentionally gone (the old
banner is retired; the swingletree mark arrives with W7 on its own branch — do not
delete `docs/images/hero-banner.jpg` in this PR). The `**Version:** 2.0.0` line must
survive exactly as written — the validator syncs it against `plugin.json`.

- [ ] **Step 2: Gate + commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add README.md && \
git commit -m "docs(readme)!: rewrite for Swingle — local harness-to-harness dispatch positioning"
```

---

### Task 5: Migration guide, verification-log entries, backlog status flip (W3 + W4 part 3)

**Files:**
- Create: `docs/migration-2.0.0.md`
- Modify (append only): `core/verification-log.md`, `providers/agy/verification-log.md`, `providers/claude/verification-log.md`, `providers/codex/verification-log.md`, `providers/grok/verification-log.md`, `providers/opencode/verification-log.md`, `providers/pi/verification-log.md`
- Modify: `docs/rename-to-swingle.md` (status block only)

**Interfaces:**
- Consumes: all new names. Produces: the portable self-migration guide (the W3 deliverable).

- [ ] **Step 1: Create `docs/migration-2.0.0.md` with:**

````markdown
# Migration: 1.x → 2.0.0 (sdd-dispatch → Swingle)

The plugin `sdd-dispatch` is renamed **Swingle** at v2.0.0. This release renames and
repositions; it does **not** alter dispatch behaviour, state layout, or config paths.

## What changed

- Plugin name: `sdd-dispatch` → `swingle`; marketplace: `sdd-dispatch-marketplace` →
  `swingle-marketplace`.
- One skill invocation: `/sdd-dispatch-verify` → `/swingle-verify`. `/sdd` and
  `/delegate` are unchanged.
- Repository: `discreteds/sdd-dispatch-plugin` → `discreteds/swingle` (GitHub
  301-redirects the old URL).

## What did NOT change

- `.sdd-dispatch/` workspace state (delegate artifacts, ledgers, `models/` overrides) —
  valid as-is, no migration.
- Config paths: `<project>/.sdd-dispatch.json`,
  `${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/`, `$SDD_DISPATCH_MODELS`.
- Pack manifests, contracts, model tables, and all dispatch behaviour.

## Self-migration guide for a v1 workspace

Bring this checklist to any repo or machine that installed the plugin as
`sdd-dispatch`; an agent (or human) there can execute it directly.

1. **Re-point the plugin source.** The install cache is keyed on the old marketplace
   name, so upgrade-in-place does not work — remove and re-add:
   - Claude Code: `/plugin uninstall sdd-dispatch@sdd-dispatch-marketplace`, remove the
     old marketplace, then `/plugin marketplace add discreteds/swingle` and
     `/plugin install swingle@swingle-marketplace`.
   - Codex: `codex plugin marketplace add discreteds/swingle` then
     `codex plugin add swingle@swingle-marketplace`; the stale
     `sdd-dispatch-marketplace` entry can be removed at leisure.
   - opencode Route A: rerun `scripts/opencode-skills-path --merge <config>` after the
     Claude Code reinstall. Route B / pi / symlink installs: update the checkout
     (`git pull` — the remote 301-redirects) and re-point any symlink named
     `sdd-dispatch-verify` at `skills/swingle-verify`.
2. **Update local invocation references.** In the workspace's CLAUDE.md / AGENTS.md /
   settings, replace `/sdd-dispatch-verify` with `/swingle-verify`. Leave `/sdd`,
   `/delegate`, and every `.sdd-dispatch/` path exactly as they are.
3. **Update pinned URLs.** Git remotes keep working via the 301, but move pins to
   `https://github.com/discreteds/swingle`
   (`git remote set-url origin https://github.com/discreteds/swingle`).
4. **Verify.** Confirm `.sdd-dispatch/` contents are untouched, then run one live
   dispatch round (or `swingle-verify <id>` for a pack you use) to confirm the new
   install resolves packs.
````

- [ ] **Step 2: Append to each of the seven verification logs** (adjust nothing above the append point; same text in all seven):

```markdown

## 2026-07-25 — plugin renamed to Swingle (v2.0.0)

The plugin `sdd-dispatch` is renamed `swingle` at v2.0.0 (`sdd-dispatch-marketplace` →
`swingle-marketplace`, skill `sdd-dispatch-verify` → `swingle-verify`, repository →
`discreteds/swingle`). Entries above predate the rename and keep the old names as
historical record. No pack facts or probe results changed in this release.
```

- [ ] **Step 3: `docs/rename-to-swingle.md`** — change the status block (lines 3–5) to:

```markdown
**Status:** W1–W5 shipped in v2.0.0 (2026-07-25); W6 (repo rename + external refs) and W7 (visual identity) outstanding
**Decided:** 2026-07-23
**Target version:** v2.0.0 (breaking — plugin identity changes)
```

Then append directly under the status block:

```markdown
> **2026-07-25 resolutions:** Q2 — rename the GitHub repo in place (301 redirect).
> Q4 — resolved by events; Grok shipped as v1.6.0 long before the rename branch. W3
> amended: instead of a pure no-op it ships the portable self-migration guide in
> `docs/migration-2.0.0.md`. Branding: the "Greedy Cup" doctrine and milkshake epigraph
> are dropped — all branding derives from the swingletree concept.
```

- [ ] **Step 4: Gate + commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add docs/migration-2.0.0.md docs/rename-to-swingle.md core/verification-log.md providers/*/verification-log.md && \
git commit -m "docs: v2.0.0 self-migration guide, rename log entries, backlog status"
```

---

### Task 6: Final sweep and full verification

**Files:** none expected — this task verifies and only edits if the sweep finds a straggler.

- [ ] **Step 1: Residual-name sweep**

```bash
grep -rIn --exclude-dir=.git --exclude-dir=archive 'sdd-dispatch\|sdd_dispatch\|SDD Dispatch' . \
  | grep -v '^\./docs/sol-' \
  | grep -v '^\./docs/migration-' \
  | grep -v '^\./docs/rename-to-swingle.md' \
  | grep -v '^\./docs/superpowers/' \
  | grep -v 'verification-log.md' \
  | grep -v '\.sdd-dispatch' \
  | grep -v 'config}/sdd-dispatch\|xdg" / "sdd-dispatch\|"sdd-dispatch" / "models\|Path(xdg) / "sdd-dispatch' \
  || echo SWEEP-CLEAN
```

Expected: `SWEEP-CLEAN`. Any surviving line is a missed rename — fix it per Rule 0 and re-run. (The `verification-log.md` exclusion is safe: Task 5 appended the only new content those files get; their remaining hits are historical entries and H1 identity lines, both allowed.)

- [ ] **Step 2: Confirm the state-dir strings survived UNCHANGED** (renaming them would be a behaviour break):

```bash
grep -c 'sdd-dispatch' scripts/validate-packs scripts/sdd-models tests/test_validate_packs.py tests/test_delegate_skill.py .gitignore
```

Expected: every count ≥ 1 (these are the deliberately-kept config/state paths — except `scripts/validate-packs` whose docstring changed but whose path lines remain).

- [ ] **Step 3: Full gate + suite**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
uv run --with pytest pytest tests/ -q
```

Expected: gate PASS, pytest fully green.

- [ ] **Step 4: Commit any sweep fixes** (skip if tree clean):

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
git add -A && git commit -m "chore: rename sweep stragglers"
```

- [ ] **Step 5: Push and open the PR to `develop`** (do not merge — owner instruction required):

```bash
git push -u origin feature/rename-to-swingle && \
gh pr create --base develop --title "feat!: rename plugin to Swingle (v2.0.0)" --body "$(cat <<'EOF'
Renames sdd-dispatch → Swingle per docs/superpowers/specs/2026-07-25-rename-to-swingle-design.md.

- W1: manifests → swingle / swingle-marketplace, v2.0.0, new positioning
- W2: skills/sdd-dispatch-verify → skills/swingle-verify (/sdd and /delegate unchanged)
- W3: portable self-migration guide for v1 workspaces (docs/migration-2.0.0.md) — .sdd-dispatch/ state and config paths deliberately unchanged
- W4: README rewritten for local harness-to-harness dispatch positioning; doctrine + install docs renamed; verification logs get appended rename entries only
- W5: validator docstring; tests untouched and green

Out of scope: W6 (GitHub repo rename + external refs), W7 (visual identity), any behaviour change.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
