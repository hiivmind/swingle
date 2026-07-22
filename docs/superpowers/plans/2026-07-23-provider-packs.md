# Provider-Pack Architecture Implementation Plan (sdd-dispatch v1.2.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the sdd-dispatch plugin's shared reference files into provider packs (`providers/<name>/`) plus a provider-free `core/`, with runtime detection and priority-based model resolution, per `docs/superpowers/specs/2026-07-22-provider-packs-design.md`.

**Architecture:** Pure content re-org plus skill-logic updates. Every fact in the five current `references/*.md` files moves to exactly one home under `core/` or `providers/{codex,opencode,agy}/`. The two SKILL.md files switch from naming three shared files to detection + pack resolution. Old paths become one-line tombstones for one release.

**Tech Stack:** Markdown + YAML front-matter, bash (detection probes, grep-based validation). No runtime code.

## Global Constraints

- **Zero information loss**: every section of the five current reference files must land in exactly one new home; the migration commit message carries the mapping table.
- **Verification logs are append-only history**: never rewrite or reword existing entries — only relocate them whole.
- **Pack contract** (spec §"The pack contract"): every `providers/<name>/` dir contains `pack.md` (with the YAML front-matter fields `name, cli, detect, version-probe, resume, session-source, stall-signal, sandbox`), `models.md` (Tier/Lane/Priority/Model id/Status/Pricing/Rationale table), `verification-log.md`.
- **Priority semantics**: exactly one priority-1 row per (tier, lane) pair; no duplicate priorities within a (tier, lane); Lane ∈ `implement|review|any` (default `any`, wildcard at resolution); `rejected` rows never resolvable; row order carries no meaning.
- **providers.local.json** is machine policy: may only `disable` detected providers or set `prefer` — never enables an undetected CLI. It is gitignored.
- All file paths below are relative to the plugin repo root `~/git/mountainash-io/mountainash/sdd-dispatch-plugin`.
- The repo is docs/skills only — "tests" are the grep/dry-run validation commands given per task; run them exactly as written.
- Do not bump the version until Task 8.

---

### Task 1: Create `core/` (provider-free knowledge)

**Files:**
- Create: `core/roles.md`, `core/liveness.md`, `core/safety-doctrine.md`, `core/playbook.md`
- Move: `references/verification-protocol.md` → `core/verification-protocol.md`
- Create: `core/verification-log.md` (cross-provider entries only)

**Interfaces:**
- Produces: `core/roles.md` tier names `cheapest` / `standard` / `most-capable` — Tasks 2–4 pack `models.md` tables and Task 6's resolution flow use these exact strings.

- [ ] **Step 1: Create `core/roles.md`** — content = `references/model-catalog.md:8-29` (the role→tier table and tiering rules) with the three provider columns REMOVED (keep columns: SDD role | Tier | Mode) and this line appended to the footnote: "Tier→model mapping lives in each provider pack's `models.md` (priority 1 = default; ascending priorities = fallback order; `rejected` rows never resolve)."
- [ ] **Step 2: Create `core/liveness.md`** — content = `references/dispatch-reference.md:31-136` (Background dispatch & liveness protocol through Operating rules) verbatim, plus the self-reaping wrapper template currently in `skills/sdd/SKILL.md` (the fenced block under "Self-reaping dispatch"). Replace the agy/codex/opencode-specific stall-threshold bullets' CLI names with references to the pack front-matter field: "consult the pack's `stall-signal:` — `log-age` CLIs use the silence thresholds; `process+print-timeout` CLIs are watched by process existence only."
- [ ] **Step 3: Create `core/safety-doctrine.md`** — extract from `references/dispatch-reference.md:6-29` the cross-CLI safety rows (hard gate, controller commits, clean-tree/diff-after on unsandboxed CLIs, never-trust-self-report) as prose; drop per-CLI cells (they go to packs in Tasks 2–4).
- [ ] **Step 4: Create `core/playbook.md`** — `git mv references/sdd-external-dispatch.md core/playbook.md`; edit its "Role → dispatch mapping" section to reference `core/roles.md` + "the active pack's models.md" instead of the model-catalog table.
- [ ] **Step 5: Move the protocol** — `git mv references/verification-protocol.md core/verification-protocol.md`; append a new probe section "### P13 — Reviewer known-defect benchmark" with: "Re-run a candidate reviewer on a diff package where a trusted model already caught a defect (same contract, brief, constraints). Candidate must cite the known defect at equal-or-higher severity; a false-clean fails the candidate outright. Evidence: smoke run 2, nemotron-3-ultra-free (2026-07-22)."
- [ ] **Step 6: Create `core/verification-log.md`** — header from `references/verification-log.md:1-6`, then move (verbatim, whole) only the cross-provider entries: `:59-76` (first live /sdd run incidents) and `:78-128` (smoke run 2 + addendum). Leave a note "Per-provider probe rounds live in providers/<name>/verification-log.md."
- [ ] **Step 7: Validate** — Run: `ls core/` → exactly `liveness.md playbook.md roles.md safety-doctrine.md verification-log.md verification-protocol.md`. Run: `grep -c 'opencode-go/\|gpt-5.6\|gemini-3' core/roles.md` → expected `0` (no provider models in core).
- [ ] **Step 8: Commit** — `git add -A && git commit -m "refactor(core): provider-free knowledge extracted to core/ (roles, liveness, safety, playbook, protocol, cross-provider log)"`

### Task 2: codex pack

**Files:**
- Create: `providers/codex/pack.md`, `providers/codex/models.md`, `providers/codex/verification-log.md`

**Interfaces:**
- Consumes: tier names from `core/roles.md` (Task 1).
- Produces: the pack-contract front-matter shape that Tasks 3–4 replicate and Task 6 parses.

- [ ] **Step 1: Create `providers/codex/pack.md`** with front-matter EXACTLY:

```yaml
---
name: codex
cli: codex
detect: command -v codex
version-probe: codex --version
resume: codex exec resume --last   # or resume <session-id>
session-source: printed in exec output; resume --last needs none
stall-signal: log-age
sandbox: enforced
---
```

Body: move verbatim `references/dispatch-reference.md:138-171` (codex Dispatch + Verified behavior), plus codex-only rows/cells from the cross-CLI table (`:6-29`), plus the codex dispatch template from `skills/sdd/SKILL.md` (the fenced implementer block) marked "canonical dispatch template".
- [ ] **Step 2: Create `providers/codex/models.md`**:

```markdown
# codex models (ChatGPT account) — verified dispatching 2026-07-22

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | gpt-5.6-luna | verified | seat | transcription/explore; ⚠ long-context recall ~41% — bump to terra on large codebases |
| standard | any | 1 | gpt-5.6-terra | verified | seat | workhorse; ~90% long-context recall; default reviewer |
| most-capable | any | 1 | gpt-5.6-sol | verified | seat | final/design review; ~90% recall |

Effort knob: `-c model_reasoning_effort=<low|medium|high>` — server-validated (bogus → HTTP 400, exit 1).
```
- [ ] **Step 3: Create `providers/codex/verification-log.md`** — protocol header line + move verbatim `references/verification-log.md:36-57` (codex 0.144.3 round).
- [ ] **Step 4: Validate** — Run: `head -12 providers/codex/pack.md | grep -c 'name:\|cli:\|detect:\|version-probe:\|resume:\|session-source:\|stall-signal:\|sandbox:'` → expected `8`.
- [ ] **Step 5: Commit** — `git add providers/codex && git commit -m "refactor(packs): codex provider pack"`

### Task 3: opencode pack

**Files:**
- Create: `providers/opencode/pack.md`, `providers/opencode/models.md`, `providers/opencode/verification-log.md`

**Interfaces:**
- Consumes: front-matter shape from Task 2; tier names from Task 1.

- [ ] **Step 1: Create `providers/opencode/pack.md`** with front-matter (same 8 fields):

```yaml
---
name: opencode
cli: opencode
detect: command -v opencode
version-probe: opencode --version
resume: opencode run -s <session-id>   # --fork to branch; -c = last session
session-source: opencode session list
stall-signal: log-age
sandbox: none
---
```

Body: move verbatim `references/dispatch-reference.md:173-209` (opencode Dispatch + Verified behavior incl. the zero-output startup-hang entry and session-id note), plus opencode-only cells from the cross-CLI table.
- [ ] **Step 2: Create `providers/opencode/models.md`** — table from `references/model-catalog.md:49-62` recast into the Tier/Lane/Priority schema:
  cheapest/any P1 `opencode-go/deepseek-v4-flash`;
  standard/implement P1 `opencode-go/minimax-m3`, P2 `opencode-go/qwen3.7-plus`;
  standard/review P1 `opencode-go/deepseek-v4-pro`;
  most-capable/review P1 `opencode-go/glm-5.2`;
  most-capable/implement P1 `opencode-go/deepseek-v4-pro` (1M ctx), P2 `opencode-go/kimi-k2.7-code` (256K);
  plus the rejected row `opencode/nemotron-3-ultra-free` (Lane any, Status: rejected, link to pack log), the free-tier namespace/caveat block (`model-catalog.md:64-67` area), and the opencode items from the Watch list (`:69-75`).
- [ ] **Step 3: Create `providers/opencode/verification-log.md`** — move verbatim `references/verification-log.md:23-34` (opencode 1.17.18 round) and `:130-153` (nemotron evaluation).
- [ ] **Step 4: Validate** — Run: `grep -c 'priority\|Priority' providers/opencode/models.md` → ≥1; `awk '/\| cheapest \| 1 \|/' providers/opencode/models.md | wc -l` → `1`; `grep -c 'nemotron' providers/opencode/models.md` → ≥1.
- [ ] **Step 5: Commit** — `git add providers/opencode && git commit -m "refactor(packs): opencode provider pack"`

### Task 4: agy pack

**Files:**
- Create: `providers/agy/pack.md`, `providers/agy/models.md`, `providers/agy/verification-log.md`

**Interfaces:**
- Consumes: front-matter shape from Task 2; tier names from Task 1.

- [ ] **Step 1: Create `providers/agy/pack.md`** with front-matter:

```yaml
---
name: agy
cli: agy
detect: command -v agy
version-probe: agy --version
resume: agy --conversation <id>   # agy -c = most recent
session-source: printed conversation id; brain dir ~/.gemini/antigravity-cli/brain/<id>/
stall-signal: process+print-timeout
sandbox: none
---
```

Body: move verbatim `references/dispatch-reference.md:211-249` (agy Dispatch + Verified behavior: `-p` LAST, `< /dev/null`, brain-file diversion + `-mmin` sweep, OAuth silent-fail), plus agy-only cells from the cross-CLI table. Include explicitly: "log-age watching WOULD kill healthy agy runs — buffered output."
- [ ] **Step 2: Create `providers/agy/models.md`** — from `references/model-catalog.md:40-47`: cheapest/any P1 `gemini-3.6-flash-low`; standard/any P1 `gemini-3.6-flash-medium`; most-capable/any P1 `gemini-3.1-pro-high` ("agy's only Pro"); superseded `gemini-3.5-flash-*` rows Status `listed (superseded)`; the no-Flash-Lite note; effort-suffix vs `--effort` mutual-exclusion rule; agy watch-list item (Flash-Lite tier appearing).
- [ ] **Step 3: Create `providers/agy/verification-log.md`** — move verbatim `references/verification-log.md:8-21` (agy 1.1.4 round).
- [ ] **Step 4: Validate** — Run: `grep -c 'stall-signal: process+print-timeout' providers/agy/pack.md` → `1`.
- [ ] **Step 5: Commit** — `git add providers/agy && git commit -m "refactor(packs): agy provider pack"`

### Task 5: Tombstones, README, .gitignore

**Files:**
- Modify: `references/dispatch-reference.md`, `references/model-catalog.md`, `references/sdd-external-dispatch.md`, `references/verification-log.md`, `references/verification-protocol.md` (each → tombstone)
- Modify: `README.md`, `.gitignore`

**Interfaces:**
- Consumes: final locations from Tasks 1–4.

- [ ] **Step 1: Tombstone each old file** — replace each file's entire content with (adjusting the destination line per file):

```markdown
# MOVED (v1.2.0, 2026-07-23)

This file's content now lives in the provider-pack layout:
- core/…  and/or  providers/<name>/…
Mapping: see commit message of the v1.2.0 migration commits and docs/superpowers/specs/2026-07-22-provider-packs-design.md.
This tombstone will be deleted in the release after v1.2.0.
```

Destinations per file: dispatch-reference → `core/liveness.md`, `core/safety-doctrine.md`, `providers/*/pack.md`; model-catalog → `core/roles.md`, `providers/*/models.md`; sdd-external-dispatch → `core/playbook.md`; verification-log → `core/verification-log.md`, `providers/*/verification-log.md`; verification-protocol → `core/verification-protocol.md`.
- [ ] **Step 2: Update `README.md`** — replace the Layout block with the new tree (core/, providers/ with the three packs, contracts/, skills/) and add a "Adding a provider" paragraph: one directory satisfying the pack contract (spec §pack contract), zero core edits.
- [ ] **Step 3: Update `.gitignore`** — ensure it contains `providers.local.json`.
- [ ] **Step 4: Validate** — Run: `wc -l references/*.md` → every file ≤ 10 lines. Run: `grep -rn 'references/sdd-external-dispatch\|references/model-catalog' --include='*.md' core/ providers/ | wc -l` → `0`.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "refactor: tombstone old reference paths; README layout; gitignore providers.local.json"`

### Task 6: `skills/sdd/SKILL.md` — detection + pack resolution

**Files:**
- Modify: `skills/sdd/SKILL.md`

**Interfaces:**
- Consumes: pack front-matter fields (Task 2), `core/*` filenames (Task 1).
- Produces: Step-0 detection contract that Task 8 dry-runs.

- [ ] **Step 1: Rewrite the "Plugin references" block** to list `core/playbook.md`, `core/liveness.md`, `core/safety-doctrine.md`, `core/roles.md`, and "the active packs under `${CLAUDE_PLUGIN_ROOT}/providers/<name>/`".
- [ ] **Step 2: Insert into Step 0 (after workspace setup) the detection/resolution procedure:**

```markdown
5. **Detect providers**: for each `${CLAUDE_PLUGIN_ROOT}/providers/*/pack.md`, run its
   front-matter `detect:` command → detected set. If `${CLAUDE_PLUGIN_ROOT}/providers.local.json`
   exists apply it: `disable` removes providers; `prefer` names the default lane →
   ACTIVE set. Read ONLY active packs' pack.md + models.md.
6. **Resolve models**: role → tier (core/roles.md) → row in the active pack's models.md
   matching (tier, lane) with `any` as wildcard; lowest priority number wins; skip
   Status=rejected. Lane is `review` for reviewer roles, `implement` for implementer
   roles. Session levers reroute providers as before.
7. If the plan or a lever names an INACTIVE provider: stop and ask the user (reroute or
   abort) — never silently reroute.
```
- [ ] **Step 3: Replace the per-CLI gotcha quick-list** with: "Per-CLI gotchas live in each pack's pack.md — read the active packs' gotcha sections at Step 0. Cross-provider dispatch discipline (self-reaping wrapper, pid-only kills, evidence-first liveness): core/liveness.md." Keep the dispatch templates but note each pack.md's template is canonical for that CLI.
- [ ] **Step 4: Validate** — Run: `grep -c 'references/dispatch-reference\|references/model-catalog\|references/sdd-external-dispatch' skills/sdd/SKILL.md` → `0`. Run: `grep -c 'providers.local.json' skills/sdd/SKILL.md` → ≥1.
- [ ] **Step 5: Commit** — `git add skills/sdd && git commit -m "feat(sdd): Step-0 provider detection + priority-based pack resolution"`

### Task 7: `skills/sdd-dispatch-verify/SKILL.md` — pack-scoped verification

**Files:**
- Modify: `skills/sdd-dispatch-verify/SKILL.md`

**Interfaces:**
- Consumes: pack layout (Tasks 2–4), `core/verification-protocol.md` incl. P13 (Task 1).

- [ ] **Step 1: Rewrite scope section**: invocation names one provider (`/sdd-dispatch-verify opencode`) or sweeps the active set; a run edits ONLY that provider's pack files + appends to its `verification-log.md`; cross-provider synthesis appends to `core/verification-log.md`.
- [ ] **Step 2: Add pack-validity checks to the procedure** (run before probes): front-matter has all 8 fields; `detect`/`version-probe` exit 0; every (tier, lane) pair has exactly one priority-1 row; no duplicate priorities within a (tier, lane); rejected rows never resolve.
- [ ] **Step 3: Reference P13** (reviewer known-defect benchmark) as mandatory for any new model proposed for a review lane; small-implementer probe mandatory for implement lanes.
- [ ] **Step 4: Validate** — Run: `grep -c 'P13\|known-defect' skills/sdd-dispatch-verify/SKILL.md` → ≥1; `grep -c 'references/' skills/sdd-dispatch-verify/SKILL.md` → `0`.
- [ ] **Step 5: Commit** — `git add skills/sdd-dispatch-verify && git commit -m "feat(verify): pack-scoped verification + pack-validity checks + P13 benchmark"`

### Task 8: End-to-end validation + release 1.2.0

**Files:**
- Modify: `.claude-plugin/plugin.json` (version), `core/verification-log.md` (migration entry)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Detection dry-run (this machine)** — Run for each pack: `bash -c "$(awk -F': ' '/^detect:/{print $2}' providers/codex/pack.md | sed 's/ *#.*//')" && echo codex-OK` (repeat for opencode, agy). Expected: all three print `<name>-OK`.
- [ ] **Step 2: Override test** — create temp `providers.local.json` `{"disable":["codex"],"prefer":"opencode"}`; confirm the Step-0 procedure text yields active = {opencode, agy} when walked by hand; delete the temp file. Expected: file deleted, `git status` clean of it (gitignored).
- [ ] **Step 3: Resolution walk** — for role "per-task reviewer": core/roles.md → tier standard, lane review; providers/opencode/models.md (standard, review) P1 → `opencode-go/deepseek-v4-pro`, Status not rejected. Also walk "transcription implementer" → (cheapest, implement) → `opencode-go/deepseek-v4-flash` via Lane `any`. Document both walks in the commit message.
- [ ] **Step 4: Repo-wide greps** — `grep -rn 'references/' --include='*.md' skills/ core/ providers/ README.md | grep -v tombstone | wc -l` → `0`; `wc -l references/*.md` → all ≤10; per-pack front-matter field count = 8 (Task 2 Step 4 command against all three packs).
- [ ] **Step 5: Migration log entry** — append to `core/verification-log.md`: date, "v1.2.0 provider-pack migration", the file mapping table (old section → new home), and the three dry-run results.
- [ ] **Step 6: Bump version** — `sed -i 's/"version": "1.1.4"/"version": "1.2.0"/' .claude-plugin/plugin.json`.
- [ ] **Step 7: Commit** — `git add -A && git commit -m "release: v1.2.0 provider-pack architecture (detection dry-run: codex/opencode/agy all active on this machine)"`
