# Provider-Pack Architecture Implementation Plan v3 (sdd-dispatch 1.2.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the rev-4 provider-pack design (`docs/superpowers/specs/2026-07-22-provider-packs-design.md`): declarative provider packs + provider-free core + harness-neutral skill with claude-code/codex adapters + `scripts/validate-packs` with fixtures + archive-based migration.

**Architecture:** Migration-manifest-first content re-org (archive the five reference files verbatim, split content into `core/` and `providers/{codex,opencode,agy}/`), a stdlib-python validator/resolver as the release gate, and skill rewrites that make Claude Code one adapter among two.

**Tech Stack:** Markdown + YAML front-matter, python3 stdlib (validator), bash (fixtures/stubs). Repo root: `~/git/mountainash-io/mountainash/sdd-dispatch-plugin`.

## Global Constraints

- **Spec is authority**: `docs/superpowers/specs/2026-07-22-provider-packs-design.md` rev 4. On any conflict between this plan and the spec, stop and escalate — do not improvise.
- **Zero information loss**: `docs/migration-1.2.0.md` (Task 1) maps every heading of the five `references/*.md` files to exactly one destination; every later move follows it. Archive copies in `archive/v1.1/` are byte-identical to the originals.
- **Append-only history**: log entries are copied whole or split at paragraph level per the manifest — never reworded.
- **Pack manifest** is declarative data: fields `schema-version, id, cli, verified-version, version-argv, resume-argv, session-source, stall-signal, sandbox` (+ optional `fork-flag, readiness-argv, readiness-timeout-seconds`, conditional `session-list-argv`); `id`/`cli` match `[a-z0-9-]+`; argv values are arrays of strings; **argv[0] MUST equal `cli`**; no absolute paths or shell metacharacters `;|&<>$` in argv elements; only placeholder is `{session_id}`. Front-matter is the spec's restricted `key: value` grammar (scalars + one-line JSON arrays), NOT general YAML.
- **models.md**: columns Tier|Lane|Priority|Model id|Status|Pricing|Rationale. Tier ∈ cheapest|standard|most-capable; Lane ∈ implement|review|any; Status ∈ verified|experimental|unavailable|superseded|rejected (eligible: verified, experimental). Per (tier,lane): unique positive priorities, exactly one priority 1. Documentary sections (rejected/watch/history) sit below the resolvable table.
- **Core purity**: no provider model ids, CLI invocations, or harness tool names in `core/` OR `contracts/` (single allow-listed exception: the word `codex` in the routing-precedence rule).
- **Harness rule**: `${CLAUDE_PLUGIN_ROOT}` appears ONLY in `skills/sdd/harnesses/claude-code.md`.
- Validation commands are the tests — run exactly as written, expected output stated. `scripts/validate-packs` (Task 6) becomes the gate for all later tasks; Tasks 2–5 use interim greps.
- Do not bump the version until Task 10.

---

### Task 1: Migration manifest + archive

**Files:**
- Create: `docs/migration-1.2.0.md`, `archive/v1.1/` (5 copies)

**Interfaces:**
- Produces: the heading→destination map every later task follows.

- [ ] **Step 1: Archive verbatim** — `mkdir -p archive/v1.1 && cp references/dispatch-reference.md references/model-catalog.md references/sdd-external-dispatch.md references/verification-log.md references/verification-protocol.md archive/v1.1/`
- [ ] **Step 2: Verify byte-identity** — Run: `for f in references/*.md; do cmp -s "$f" "archive/v1.1/$(basename $f)" || echo "DIFF $f"; done` → no output.
- [ ] **Step 3: Write `docs/migration-1.2.0.md`** — a table `| Source (file:heading) | Destination |` covering EVERY heading listed by `grep -n '^#' references/*.md`. Required assignments (all others follow the same logic):
  - dispatch-reference: Cross-CLI table §6-29 → safety rows to `core/safety-doctrine.md`, per-CLI cells to each `providers/<id>/pack.md`; §31-136 liveness → `core/liveness.md` (abstract) with resume table rows to packs; §138-171 → `providers/codex/pack.md`; §173-209 → `providers/opencode/pack.md`; §211-249 → `providers/agy/pack.md`; §251 Change history → PRIMARY: `core/verification-log.md` (as a "pre-split change history" entry); archive copy exists as always.
  - model-catalog: §8-29 policy table → `core/roles.md` (columns reduced); §33-38 → `providers/codex/models.md`; §40-47 → `providers/agy/models.md`; §49-67 → `providers/opencode/models.md`; §69-80 watch list → split per provider into each `models.md` documentary section; §82 Release history → PRIMARY: `core/verification-log.md` "release history" entry; `(mirror)` rows in agy + opencode `models.md` History sections for the Google items.
  - sdd-external-dispatch: whole file → `core/playbook.md` with harness terms neutralized (Task 2).
  - verification-log: §8-21 → `providers/agy/verification-log.md`; §23-34 → `providers/opencode/verification-log.md`; §36-57 → `providers/codex/verification-log.md` EXCEPT the "Cross-CLI synthesis" paragraph (§51-55) → `core/verification-log.md`; §59-76 → `core/verification-log.md`; §78-128 → split: opencode-channel findings 1, 5 and the nemotron addendum context → `providers/opencode/verification-log.md`, harness/controller findings 2-4 + cost note + "what worked" → `core/verification-log.md`; §130-153 nemotron → `providers/opencode/verification-log.md`.
  - verification-protocol: whole file → `core/verification-protocol.md` (+P13 added in Task 8).
  Every manifest row names exactly ONE primary destination; extra copies are marked `(mirror)`; the archive is never listed as a destination.
- [ ] **Step 4: Completeness check** — Run: `grep -c '^| ' docs/migration-1.2.0.md` and `grep -ch '^##' references/*.md | paste -sd+ | bc` — manifest rows ≥ heading count. Every heading string appears in the manifest: `for h in $(grep -h '^## ' references/*.md | sed 's/## //;s/ .*//' | sort -u); do grep -q "$h" docs/migration-1.2.0.md || echo "MISSING $h"; done` → no output.
- [ ] **Step 5: Commit** — `git add archive docs/migration-1.2.0.md && git commit -m "chore(migration): v1.1 archive + migration manifest"`

### Task 2: core/ (provider- and harness-free)

**Files:**
- Create: `core/roles.md`, `core/liveness.md`, `core/safety-doctrine.md`, `core/playbook.md`, `core/verification-log.md`
- Move: `references/verification-protocol.md` → `core/verification-protocol.md` (git mv; original already archived)

**Interfaces:**
- Consumes: `docs/migration-1.2.0.md`.
- Produces: tier strings `cheapest|standard|most-capable`, lane strings `implement|review`, used by Tasks 3–6.

- [ ] **Step 1: `core/roles.md`** — from `archive/v1.1/model-catalog.md:8-29`: table with columns `SDD role | Tier | Lane | Mode` (Lane: implementer roles → implement; reviewer/final-review roles → review; explore/research → review). Keep tiering rules. Footnote: "Tier→model mapping lives in each pack's models.md — resolution algorithm and status eligibility in the spec §Resolution algorithm; priority 1 = default, ascending = fallback, only Status verified/experimental resolve."
- [ ] **Step 2: `core/liveness.md`** — from `archive/v1.1/dispatch-reference.md:31-136` minus the per-CLI resume table rows (§66-70 → packs) and minus CLI-specific threshold naming: thresholds keyed to manifest `stall-signal` (`log-age` → 300s low/med effort, 600–900s high/xhigh; `process+print-timeout` → process existence + the CLI's print-timeout, log age is NOT a signal). Include the self-reaping wrapper template from `skills/sdd/SKILL.md` with the dispatch line abstracted to `<pack dispatch template> > "$LOG" 2>&1 &`.
- [ ] **Step 3: `core/safety-doctrine.md`** — safety invariants from `archive/v1.1/dispatch-reference.md:6-29` prose-ified: hard gate; controller commits; clean-tree-before/diff-after when manifest `sandbox: none`; agent self-report never evidence; read-only is intent unless `sandbox: enforced` provides a lane.
- [ ] **Step 4: `core/playbook.md`** — `git rm references/sdd-external-dispatch.md` content basis = archive copy; rewrite harness-specific wording: "Agent tool"→"the harness's native subagent mechanism (see harness adapter)", "all Claude"→"`native-subagents` lever", `${CLAUDE_PLUGIN_ROOT}` references → "the plugin tree root (see harness adapter)". Role→dispatch mapping section now cites `core/roles.md` + active pack models.md.
- [ ] **Step 5: Protocol move** — `git mv references/verification-protocol.md core/verification-protocol.md` (P13 comes in Task 8).
- [ ] **Step 6: `core/verification-log.md`** — header + the manifest-assigned cross-provider entries copied whole/at-paragraph from the archive, each tagged `(from archive/v1.1)`. Top note: "Per-provider rounds: providers/<id>/verification-log.md. Pre-split history: archive/v1.1/verification-log.md."
- [ ] **Step 7: Validate (interim)** — Run: `grep -rn 'gpt-5.6\|gemini-3\|opencode-go/\|deepseek\|minimax\|qwen\|glm-5\|Agent tool\|TodoWrite\|CLAUDE_PLUGIN_ROOT' core/ | grep -v 'codex.*routing\|precedence' | wc -l` → `0`. Run: `ls core/ | sort | paste -sd' '` → `liveness.md playbook.md roles.md safety-doctrine.md verification-log.md verification-protocol.md`.
- [ ] **Step 8: Commit** — `git add -A && git commit -m "refactor(core): provider- and harness-free core per migration manifest"`

### Task 3: codex pack

**Files:**
- Create: `providers/codex/pack.md`, `providers/codex/models.md`, `providers/codex/verification-log.md`

**Interfaces:**
- Consumes: manifest map (Task 1), tier/lane strings (Task 2).
- Produces: the manifest shape Tasks 4–5 replicate; parsed by Task 6 validator.

- [ ] **Step 1: `providers/codex/pack.md`** front-matter EXACTLY:

```yaml
---
schema-version: 1
id: codex
cli: codex
verified-version: "0.144.3"
version-argv: ["codex", "--version"]
resume-argv: ["codex", "exec", "resume", "{session_id}"]
session-source: exec-output
stall-signal: log-age
sandbox: enforced
---
```

Body per manifest: `archive/v1.1/dispatch-reference.md:138-171`, codex cells of the cross-CLI table, the codex dispatch template from current `skills/sdd/SKILL.md` labeled "canonical dispatch template", resume prose noting `resume --last` shortcut, `< /dev/null` rule.
- [ ] **Step 2: `providers/codex/models.md`**:

```markdown
# codex models (ChatGPT seat) — verified dispatching 2026-07-22

## Resolvable

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | gpt-5.6-luna | verified | seat | transcription/explore; ⚠ recall ~41% — escalate to terra on large codebases |
| standard | any | 1 | gpt-5.6-terra | verified | seat | workhorse; ~90% recall; default reviewer |
| most-capable | any | 1 | gpt-5.6-sol | verified | seat | final/design review; ~90% recall |

Effort: `-c model_reasoning_effort=<low|medium|high>` — server-validated (bogus → HTTP 400, exit 1).

## Documentary

(none yet)
```
- [ ] **Step 3: `providers/codex/verification-log.md`** — header + `archive/v1.1/verification-log.md:36-57` minus the Cross-CLI synthesis paragraph (stays core), tagged `(from archive/v1.1)`.
- [ ] **Step 4: Validate (interim)** — Run: `sed -n '2,11p' providers/codex/pack.md | grep -c '^[a-z-]*:'` → `9`. Run: `grep -c '| cheapest | any | 1 |' providers/codex/models.md` → `1`.
- [ ] **Step 5: Commit** — `git add providers/codex && git commit -m "refactor(packs): codex pack (declarative manifest)"`

### Task 4: opencode pack

**Files:** Create: `providers/opencode/{pack.md,models.md,verification-log.md}`

**Interfaces:** Consumes Task 3's shape.

- [ ] **Step 1: `providers/opencode/pack.md`** front-matter EXACTLY:

```yaml
---
schema-version: 1
id: opencode
cli: opencode
verified-version: "1.17.18"
version-argv: ["opencode", "--version"]
resume-argv: ["opencode", "run", "-s", "{session_id}"]
fork-flag: "--fork"
session-source: session-list
session-list-argv: ["opencode", "session", "list"]
stall-signal: log-age
sandbox: none
readiness-argv: ["opencode", "session", "list"]
---
```

Body per manifest: `archive/v1.1/dispatch-reference.md:173-209` (positional prompt / `-p`=password, no-sandbox, silent `--variant`, zero-output startup hang + handling, session-id source), opencode cells of the cross-CLI table, canonical dispatch template (opencode form of the skill template: `opencode run --auto -m <model> --dir <repo> "<prompt>"`).
- [ ] **Step 2: `providers/opencode/models.md`** — Resolvable table:

```markdown
| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | opencode-go/deepseek-v4-flash | verified | $0.14/$0.28 | cheapest paid coder; transcription/explore |
| standard | implement | 1 | opencode-go/minimax-m3 | verified | $0.30/$1.20 | adaptation (eager — watch over-build) |
| standard | implement | 2 | opencode-go/qwen3.7-plus | verified | $0.40/$1.60 | adaptation alternate |
| standard | review | 1 | opencode-go/deepseek-v4-pro | verified | $1.74/$3.48 | per-task reviewer (caught planted defect) |
| most-capable | implement | 1 | opencode-go/deepseek-v4-pro | verified | $1.74/$3.48 | 1M ctx heavy implement |
| most-capable | implement | 2 | opencode-go/kimi-k2.7-code | experimental | — | coding-strong, 256K ctx |
| most-capable | review | 1 | opencode-go/glm-5.2 | verified | $1.40/$4.40 | final review; #1 open-weights AA 51 |
```

(Enum note: the old catalog's "listed" status maps to `experimental` everywhere.) Documentary sections below: rejected `opencode/nemotron-3-ultra-free` (evidence link to pack log), free-tier namespace + trial-data caveat, watch list (`kimi-k3`, `grok-4.5`, `qwen3.7-max`, the three new `-free` tiers), Zen pricing note, history items from the manifest.
- [ ] **Step 3: `providers/opencode/verification-log.md`** — header + manifest-assigned entries: `archive/v1.1/verification-log.md:23-34`, the opencode-channel parts of §78-128, §130-153 (nemotron), each tagged `(from archive/v1.1)`.
- [ ] **Step 4: Validate (interim)** — Run: `grep -c '| standard | implement | 1 |' providers/opencode/models.md` → `1`; `grep -c '| standard | review | 1 |' providers/opencode/models.md` → `1`; `grep -A3 '^## Documentary' providers/opencode/models.md | grep -c nemotron` → ≥1.
- [ ] **Step 5: Commit** — `git add providers/opencode && git commit -m "refactor(packs): opencode pack"`

### Task 5: agy pack

**Files:** Create: `providers/agy/{pack.md,models.md,verification-log.md}`

**Interfaces:** Consumes Task 3's shape.

- [ ] **Step 1: `providers/agy/pack.md`** front-matter EXACTLY:

```yaml
---
schema-version: 1
id: agy
cli: agy
verified-version: "1.1.4"
version-argv: ["agy", "--version"]
resume-argv: ["agy", "--conversation", "{session_id}"]
session-source: conversation-id
stall-signal: process+print-timeout
sandbox: none
---
```

Body per manifest: `archive/v1.1/dispatch-reference.md:211-249` (`-p "<PROMPT>"` LAST, `< /dev/null`, buffered output — "a log-age watch WOULD kill healthy agy runs", brain-file diversion + `-mmin` sweep, OAuth silent-fail, effort-suffix XOR `--effort`), agy cells of the cross-CLI table, canonical dispatch template (`agy --model <m> --effort <e> --add-dir <repo> --print-timeout <t> -p "<PROMPT>" < /dev/null`).
- [ ] **Step 2: `providers/agy/models.md`** — Resolvable: cheapest/any P1 `gemini-3.6-flash-low` (verified); standard/any P1 `gemini-3.6-flash-medium` (experimental — dispatch-verified at low only); most-capable/any P1 `gemini-3.1-pro-high` (experimental; "agy's only Pro — long-context + hardest architecture only"). Documentary: superseded `gemini-3.5-flash-*` rows; no-Flash-Lite note; in-CLI extras (claude/gpt-oss) as unused; watch: agy Flash-Lite tier; history: 2026-07-21 Google release note.
- [ ] **Step 3: `providers/agy/verification-log.md`** — header + `archive/v1.1/verification-log.md:8-21` tagged `(from archive/v1.1)`.
- [ ] **Step 4: Validate (interim)** — Run: `grep -c 'stall-signal: process+print-timeout' providers/agy/pack.md` → `1`; `grep -c 'log-age watch WOULD kill' providers/agy/pack.md` → `1`.
- [ ] **Step 5: Commit** — `git add providers/agy && git commit -m "refactor(packs): agy pack"`

### Task 6: validate-packs + fixtures (TDD)

**Files:**
- Create: `scripts/validate-packs` (python3, executable), `tests/test_validate_packs.py`, `tests/fixtures/` (fixture packs, stub bins, configs)

**Interfaces:**
- Consumes: pack contract (Tasks 3–5), spec §Resolution algorithm, §Routing precedence, §Configuration.
- Produces: `validate-packs [--root DIR] [--resolve ROLE PROVIDER] [--check-config FILE]`, exit 0 clean / 1 findings; one `file: message` line per finding. Task 7's Step 0 text and Task 10's gate call this.

- [ ] **Step 1: Write failing tests** — `tests/test_validate_packs.py` (pytest, invokes the script via subprocess against fixture roots):

```python
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-packs"
FIX = Path(__file__).parent / "fixtures"

def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)

def test_real_tree_valid():
    r = run("--root", str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr

def test_missing_p1_fails():
    r = run("--root", str(FIX / "bad-missing-p1"))
    assert r.returncode == 1 and "priority 1" in r.stdout

def test_duplicate_priority_fails():
    r = run("--root", str(FIX / "bad-dup-priority"))
    assert r.returncode == 1 and "duplicate priority" in r.stdout

def test_shell_string_manifest_fails():
    r = run("--root", str(FIX / "bad-shell-detect"))
    assert r.returncode == 1 and "argv" in r.stdout

def test_id_dirname_mismatch_fails():
    r = run("--root", str(FIX / "bad-id-mismatch"))
    assert r.returncode == 1 and "id" in r.stdout

def test_resolve_exact_lane_beats_any():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "per-task reviewer", "alpha")
    assert r.returncode == 0 and "review-model-exact" in r.stdout

def test_resolve_any_fallback():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "transcription implementer", "alpha")
    assert r.returncode == 0 and "cheap-any-model" in r.stdout

def test_resolve_rejected_never():
    r = run("--root", str(FIX / "bad-rejected-only"), "--resolve", "per-task reviewer", "alpha")
    assert r.returncode == 1 and "no eligible" in r.stdout

def test_config_malformed_fails_closed():
    r = run("--check-config", str(FIX / "config-malformed.json"))
    assert r.returncode == 1

def test_config_disabled_default_fails():
    r = run("--check-config", str(FIX / "config-disabled-default.json"))
    assert r.returncode == 1 and "default_provider" in r.stdout

def test_argv0_mismatch_fails():
    r = run("--root", str(FIX / "bad-argv0"))
    assert r.returncode == 1 and "argv[0]" in r.stdout

def test_shell_metachar_argv_fails():
    r = run("--root", str(FIX / "bad-metachar"))
    assert r.returncode == 1 and "metacharacter" in r.stdout

def test_exclusion_advances_fallback():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "per-task reviewer", "alpha",
            "--exclude", "alpha:review-model-exact")
    assert r.returncode == 0 and "review-model-any" in r.stdout

def test_step0_detection_and_routing():
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-alpha"))
    assert r.returncode == 0 and "active: alpha" in r.stdout

def test_step0_no_providers_installed():
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-empty"))
    assert r.returncode == 1 and "no active providers" in r.stdout

def test_step0_native_subagents_bypasses():
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-alpha"), "--lever", "native-subagents")
    assert r.returncode == 0 and "native-subagents: bypass" in r.stdout

def test_config_disabled_lane_target_fails():
    r = run("--check-config", str(FIX / "config-disabled-lane.json"))
    assert r.returncode == 1 and "providers_by_lane" in r.stdout

def test_interpreter_cli_denied():
    r = run("--root", str(FIX / "bad-interpreter-cli"))
    assert r.returncode == 1 and "interpreter" in r.stdout

def test_empty_argv_fails():
    r = run("--root", str(FIX / "bad-empty-argv"))
    assert r.returncode == 1 and "empty" in r.stdout

def test_strict_grammar_rejects_bad_lines():
    r = run("--root", str(FIX / "bad-grammar"))
    assert r.returncode == 1 and "grammar" in r.stdout

def test_fallback_order_exact_then_any():
    r = run("--root", str(FIX / "good-lanes"), "--resolve", "per-task reviewer", "alpha")
    assert "fallback order: review-model-exact, review-model-any" in r.stdout

def test_step0_multi_active_no_policy_asks():
    r = run("--step0", "--root", str(FIX / "good-two-providers"),
            "--path-dir", str(FIX / "bins-two"), "--role", "per-task reviewer")
    assert r.returncode == 1 and "ask user" in r.stdout

def test_step0_lane_routing_and_resolution():
    r = run("--step0", "--root", str(FIX / "good-two-providers"),
            "--path-dir", str(FIX / "bins-two"),
            "--config", str(FIX / "config-lane-beta.json"), "--role", "per-task reviewer")
    assert r.returncode == 0 and "provider: beta" in r.stdout and "model:" in r.stdout

def test_step0_version_mismatch_blocks_when_required():
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-alpha-oldver"),
            "--config", str(FIX / "config-require-version.json"), "--role", "per-task reviewer")
    assert r.returncode == 1 and "incompatible" in r.stdout

def test_step0_readiness_failure_reported():
    r = run("--step0", "--root", str(FIX / "good-lanes"),
            "--path-dir", str(FIX / "bins-alpha-notready"), "--role", "per-task reviewer")
    assert r.returncode == 1 and "not ready" in r.stdout
```

- [ ] **Step 2: Build fixtures** — under `tests/fixtures/`: each `bad-*`/`good-*` dir mirrors the tree shape (`core/roles.md` minimal + `providers/alpha/{pack.md,models.md,verification-log.md}`). `good-lanes` models.md: cheapest/any P1 `cheap-any-model` (verified); standard/review P1 `review-model-exact` (verified); standard/any P1 `review-model-any` (verified). `bad-missing-p1`: standard/review has only P2. `bad-dup-priority`: two standard/review P1 rows. `bad-shell-detect`: manifest has `detect: command -v alpha` string field. `bad-id-mismatch`: dir `alpha`, manifest `id: beta`. `bad-rejected-only`: standard/review row Status rejected. `bad-argv0`: version-argv `["sh","-c","true"]`. `bad-metachar`: resume-argv containing `"x;y"`. `bad-interpreter-cli`: manifest `cli: sh`. `bad-empty-argv`: `version-argv: []`. `bad-grammar`: front-matter containing an out-of-grammar line (`nested:\n  key: v`) and a single-quoted array. `good-two-providers`: packs alpha + beta, both with standard/review P1 (`alpha-review`, `beta-review`); `good-lanes` manifests carry `verified-version: "1.0.0"`. Stub bins (all executable shell stubs): `bins-alpha/alpha` prints `alpha 1.0.0`; `bins-two/{alpha,beta}` print `<name> 1.0.0`; `bins-alpha-oldver/alpha` prints `alpha 0.9.0`; `bins-alpha-notready/alpha` prints version on `--version` but exits 1 on the readiness argv. Configs: `config-malformed.json` (truncated JSON), `config-disabled-default.json` = `{"disable":["alpha"],"default_provider":"alpha"}`, `config-disabled-lane.json` = `{"disable":["alpha"],"providers_by_lane":{"review":"alpha"}}`, `config-lane-beta.json` = `{"providers_by_lane":{"review":"beta"}}`, `config-require-version.json` = `{"require-verified-version":true}`. Minimal `core/roles.md` in fixtures maps: "transcription implementer"→(cheapest,implement); "per-task reviewer"→(standard,review).
- [ ] **Step 3: Run tests, verify all fail** — Run: `uv run --with pytest pytest tests/test_validate_packs.py -q` → all FAIL (script missing).
- [ ] **Step 4: Implement `scripts/validate-packs`** — python3 stdlib only:

```python
#!/usr/bin/env python3
"""sdd-dispatch pack validator/resolver + Step-0 simulator (stdlib only)."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

MANIFEST_REQ = ["schema-version", "id", "cli", "verified-version", "version-argv",
                "resume-argv", "session-source", "stall-signal", "sandbox"]
OPTIONAL = {"fork-flag", "session-list-argv", "readiness-argv", "readiness-timeout-seconds"}
ENUMS = {"session-source": {"session-list", "exec-output", "conversation-id"},
         "stall-signal": {"log-age", "process+print-timeout"},
         "sandbox": {"enforced", "none"}}
INTERPRETERS = {"sh","bash","dash","zsh","ksh","env","python","python3","perl","ruby",
                "node","deno","bun","npx","uv","uvx","xargs","nice","timeout","sudo","doas"}
TIERS = {"cheapest", "standard", "most-capable"}
LANES = {"implement", "review", "any"}
STATUSES = {"verified", "experimental", "unavailable", "superseded", "rejected"}
ELIGIBLE = {"verified", "experimental"}
NAME_RE = re.compile(r"^[a-z0-9-]+$")
META_RE = re.compile(r"[;|&<>$]")
VER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)+")
LINE_RE = re.compile(r'^([a-z-]+):\s*(".*"|\[.*\]|[^"\[\s][^"]*)?\s*(#.*)?$')
CONFIG_KEYS = {"disable": list, "default_provider": str, "providers_by_lane": dict,
               "require-verified-version": bool, "note": str}
findings = []
def find(m): findings.append(m)

def parse_front_matter(path):
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "---":
        find(f"{path}: no front-matter"); return {}
    fm, closed = {}, False
    for i, line in enumerate(lines[1:], start=2):
        if line == "---": closed = True; break
        m = LINE_RE.match(line)
        if not m or m.group(2) is None:
            find(f"{path}:{i}: grammar violation: {line!r}"); continue
        k, raw = m.group(1), m.group(2).strip()
        if k in fm: find(f"{path}:{i}: duplicate key {k}")
        if raw.startswith("["):
            if "'" in raw: find(f"{path}:{i}: grammar violation: single quotes in array")
            try: v = json.loads(raw)
            except json.JSONDecodeError: find(f"{path}:{i}: invalid JSON array for {k}"); v = None
            if isinstance(v, list) and not v: find(f"{path}: {k} is an empty argv array")
            fm[k] = v if isinstance(v, list) else []
        else:
            fm[k] = raw.strip('"')
    if not closed: find(f"{path}: unterminated front-matter")
    return fm

def check_manifest(pack_dir):
    fm = parse_front_matter(pack_dir / "pack.md")
    for k in MANIFEST_REQ:
        if k not in fm: find(f"{pack_dir}/pack.md: missing field {k}")
    for k in fm:
        if k not in MANIFEST_REQ and k not in OPTIONAL and k != "detect":
            find(f"{pack_dir}/pack.md: unknown field {k}")
    if str(fm.get("schema-version", "")) != "1":
        find(f"{pack_dir}/pack.md: unknown schema-version {fm.get('schema-version')}")
    if "detect" in fm: find(f"{pack_dir}/pack.md: shell 'detect' forbidden")
    for k, allowed in ENUMS.items():
        if k in fm and fm[k] not in allowed: find(f"{pack_dir}/pack.md: bad enum {k}={fm[k]}")
    for k in ("id", "cli"):
        if k in fm and not NAME_RE.match(str(fm[k])): find(f"{pack_dir}/pack.md: {k} fails [a-z0-9-]+")
    if fm.get("cli") in INTERPRETERS: find(f"{pack_dir}/pack.md: cli is an interpreter/launcher: {fm['cli']}")
    if fm.get("id") and fm["id"] != pack_dir.name: find(f"{pack_dir}/pack.md: id != dirname")
    for k in [k for k in fm if k.endswith("-argv")]:
        v = fm[k]
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            find(f"{pack_dir}/pack.md: {k} must be a JSON array of strings"); continue
        if not v: find(f"{pack_dir}/pack.md: {k} is an empty argv array"); continue
        if fm.get("cli") and v[0] != fm["cli"]:
            find(f"{pack_dir}/pack.md: {k} argv[0] must equal cli ({v[0]} != {fm['cli']})")
        for tok in v[1:]:
            if META_RE.search(tok): find(f"{pack_dir}/pack.md: {k} shell metacharacter: {tok}")
            if tok.startswith("/"): find(f"{pack_dir}/pack.md: {k} absolute path: {tok}")
            for ph in re.findall(r"\{([a-z_]+)\}", tok):
                if ph != "session_id": find(f"{pack_dir}/pack.md: unknown placeholder {{{ph}}}")
    if fm.get("session-source") == "session-list" and "session-list-argv" not in fm:
        find(f"{pack_dir}/pack.md: session-list-argv required for session-source: session-list")
    return fm

def parse_models(pack_dir):
    rows, in_doc = [], False
    for n, line in enumerate((pack_dir / "models.md").read_text().splitlines(), 1):
        if line.lower().startswith("## documentary"): in_doc = True
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0] in TIERS:
            if in_doc:
                if cells[4] in ELIGIBLE: find(f"{pack_dir}/models.md:{n}: eligible status in Documentary section")
                continue
            tier, lane, prio, model, status = cells[:5]
            if lane not in LANES: find(f"{pack_dir}/models.md:{n}: bad lane {lane}")
            if status not in STATUSES: find(f"{pack_dir}/models.md:{n}: bad status {status}")
            if not prio.isdigit() or int(prio) < 1: find(f"{pack_dir}/models.md:{n}: bad priority {prio}")
            else: rows.append({"tier": tier, "lane": lane, "prio": int(prio),
                              "model": model, "status": status})
    seen = set()
    for r in rows:
        key = (r["tier"], r["lane"], r["prio"])
        if key in seen: find(f"{pack_dir}/models.md: duplicate priority {key}")
        seen.add(key)
    for tl in {(r["tier"], r["lane"]) for r in rows}:
        if not any(r["prio"] == 1 for r in rows if (r["tier"], r["lane"]) == tl):
            find(f"{pack_dir}/models.md: {tl} has no priority 1 row")
    return rows

def parse_roles(root):
    roles = {}
    p = root / "core" / "roles.md"
    if not p.exists(): find(f"{p}: missing"); return roles
    for line in p.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[1] in TIERS and cells[2] in (LANES - {"any"}):
            roles[cells[0].lower()] = (cells[1], cells[2])
    return roles

def candidate_order(rows, tier, lane, excl):
    elig = [r for r in rows if r["status"] in ELIGIBLE and r["model"] not in excl]
    exact = sorted((r for r in elig if (r["tier"], r["lane"]) == (tier, lane)), key=lambda r: r["prio"])
    anyl = sorted((r for r in elig if (r["tier"], r["lane"]) == (tier, "any")), key=lambda r: r["prio"])
    return exact + anyl

def load_config(path):
    if path is None: return {}
    try: cfg = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e: find(f"{path}: unreadable/malformed ({e})"); return None
    if not isinstance(cfg, dict): find(f"{path}: config root must be an object"); return None
    for k, v in list(cfg.items()):
        if k not in CONFIG_KEYS: print(f"warn: unknown key {k}", file=sys.stderr); cfg.pop(k); continue
        if not isinstance(v, CONFIG_KEYS[k]): find(f"{path}: {k} has wrong type"); return None
    for x in cfg.get("disable", []):
        if not isinstance(x, str): find(f"{path}: disable entries must be strings"); return None
    for lane, pid in cfg.get("providers_by_lane", {}).items():
        if lane not in ("implement", "review"): find(f"{path}: providers_by_lane bad lane {lane}")
        if not isinstance(pid, str): find(f"{path}: providers_by_lane values must be strings")
    disabled = set(cfg.get("disable", []))
    if cfg.get("default_provider") in disabled: find(f"{path}: default_provider is disabled")
    for lane, pid in cfg.get("providers_by_lane", {}).items():
        if pid in disabled: find(f"{path}: providers_by_lane[{lane}] names disabled provider {pid}")
    return cfg

def run_argv(argv, path_dirs, timeout):
    env = dict(os.environ, PATH=os.pathsep.join(path_dirs))
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout + r.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)

def check_repo_docs(root):
    ver_plugin = ver_readme = None
    pj = root / ".claude-plugin" / "plugin.json"
    if pj.exists(): ver_plugin = json.loads(pj.read_text()).get("version")
    rd = root / "README.md"
    if rd.exists():
        m = re.search(r"\*\*Version:\*\*\s*([0-9.]+)", rd.read_text())
        ver_readme = m.group(1) if m else None
    if ver_plugin and ver_readme and ver_plugin != ver_readme:
        find(f"version mismatch: plugin.json {ver_plugin} != README {ver_readme}")
    banned = re.compile(r"gpt-5\.6|gemini-3|opencode-go/|deepseek|minimax|qwen|glm-5|Agent tool|TodoWrite|CLAUDE_PLUGIN_ROOT|spawn_agent")
    for d in ("core", "contracts"):
        for f in sorted((root / d).glob("*.md")) if (root / d).exists() else []:
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if banned.search(line) and "routing" not in line and "precedence" not in line:
                    find(f"{f}:{n}: purity violation: {line.strip()[:70]}")
    link_re = re.compile(r"\]\(([^)#http][^)#]*)")
    for f in sorted(root.rglob("*.md")):
        if "archive/" in str(f.relative_to(root)) or ".git" in f.parts: continue
        for n, line in enumerate(f.read_text().splitlines(), 1):
            for target in link_re.findall(line):
                if not (f.parent / target).exists():
                    find(f"{f}:{n}: broken link {target}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--resolve", nargs=2, metavar=("ROLE", "PROVIDER"))
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--check-config")
    ap.add_argument("--step0", action="store_true")
    ap.add_argument("--config"); ap.add_argument("--path-dir", action="append", default=[])
    ap.add_argument("--lever"); ap.add_argument("--task-provider"); ap.add_argument("--role")
    a = ap.parse_args()
    root = Path(a.root)
    excl = {}
    for e in a.exclude:
        prov, _, model = e.partition(":"); excl.setdefault(prov, set()).add(model)
    if a.check_config:
        load_config(a.check_config)
    else:
        packs = sorted((root / "providers").glob("*/")) if (root / "providers").exists() else []
        for p_ in packs:
            if not (p_ / "pack.md").exists(): find(f"{p_}: missing pack.md")
        packs = [p_ for p_ in packs if (p_ / "pack.md").exists()]
        if not packs: find(f"{root}: no packs found")
        fms, rows_by_id = {}, {}
        for p_ in packs:
            fms[p_.name] = check_manifest(p_)
            for f in ("models.md", "verification-log.md"):
                if not (p_ / f).exists(): find(f"{p_}: missing {f}")
            if (p_ / "models.md").exists(): rows_by_id[p_.name] = parse_models(p_)
        if not a.step0 and not a.resolve:
            check_repo_docs(root)
        if a.step0:
            if a.lever == "native-subagents":
                print("native-subagents: bypass external dispatch (no provider selected)")
            else:
                installed = [pid for pid, fm in fms.items() if any(
                    (Path(d) / fm.get("cli", "")).exists() and os.access(Path(d) / fm.get("cli",""), os.X_OK)
                    for d in a.path_dir)]
                print(f"installed: {' '.join(installed) or '(none)'}")
                cfg = load_config(a.config)
                if cfg is None: cfg = {}
                else:
                    active = [x for x in installed if x not in set(cfg.get("disable", []))]
                    tmo = 10
                    if cfg.get("require-verified-version"):
                        compat = []
                        for pid in active:
                            rc, out = run_argv(fms[pid]["version-argv"], a.path_dir, tmo)
                            m = VER_RE.search(out or "")
                            if rc == 0 and m and m.group(0) == fms[pid].get("verified-version"):
                                compat.append(pid)
                            else: print(f"incompatible: {pid} ({m.group(0) if m else 'unparseable'} != {fms[pid].get('verified-version')})")
                        dropped = set(active) - set(compat)
                        if dropped: find(f"incompatible providers removed: {' '.join(sorted(dropped))}")
                        active = compat
                    if not active: find("no active providers")
                    else:
                        print(f"active: {' '.join(active)}")
                        role_tl = None
                        if a.role:
                            roles = parse_roles(root)
                            role_tl = next((v for k, v in roles.items() if a.role.lower() in k), None)
                            if not role_tl: find(f"unknown role: {a.role}")
                        lane = role_tl[1] if role_tl else None
                        chosen = (a.task_provider or a.lever or
                                  (cfg.get("providers_by_lane", {}).get(lane) if lane else None) or
                                  cfg.get("default_provider") or
                                  ("codex" if "codex" in active else (active[0] if len(active) == 1 else None)))
                        if chosen and chosen not in active: find(f"routed provider inactive: {chosen}")
                        elif not chosen: find("route-selection: ask user (multiple active, no policy)")
                        else:
                            print(f"provider: {chosen}")
                            if role_tl:
                                order = candidate_order(rows_by_id.get(chosen, []), role_tl[0], role_tl[1],
                                                        excl.get(chosen, set()))
                                if not order: find(f"no eligible model for {role_tl} in {chosen}")
                                else: print(f"model: {order[0]['model']} (P{order[0]['prio']}); "
                                            f"fallback: {', '.join(r['model'] for r in order)}")
                            ready_argv = fms[chosen].get("readiness-argv") or fms[chosen]["version-argv"]
                            rc, _ = run_argv(ready_argv, a.path_dir,
                                             int(fms[chosen].get("readiness-timeout-seconds", 30)))
                            if rc != 0: find(f"provider not ready: {chosen} (exit {rc})")
                            else: print(f"ready: {chosen}")
        elif a.resolve:
            role, provider = a.resolve[0].lower(), a.resolve[1]
            roles = parse_roles(root)
            tl = next((v for k, v in roles.items() if role in k), None)
            if not tl: find(f"unknown role: {role}")
            elif provider not in rows_by_id: find(f"unknown provider: {provider}")
            else:
                order = candidate_order(rows_by_id[provider], tl[0], tl[1], excl.get(provider, set()))
                if order: print(f"{role} -> {tl} -> {order[0]['model']} (P{order[0]['prio']}, {order[0]['status']}); "
                                f"fallback order: {', '.join(r['model'] for r in order)}")
                else: find(f"no eligible model for {tl} in {provider}")
    for f in findings: print(f)
    sys.exit(1 if findings else 0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to green** — Run: `uv run --with pytest pytest tests/test_validate_packs.py -q` → all PASS. If `test_real_tree_valid` fails, the finding lines name real pack defects: fix the pack files (Tasks 3–5 outputs), not the validator, unless the validator misreads the spec.
- [ ] **Step 6: chmod + smoke** — Run: `chmod +x scripts/validate-packs && ./scripts/validate-packs --root . && echo CLEAN` → `CLEAN`. Run: `./scripts/validate-packs --root . --resolve "per-task reviewer" opencode` → line containing `opencode-go/deepseek-v4-pro (P1, verified)`.
- [ ] **Step 7: Commit** — `git add scripts tests && git commit -m "feat: validate-packs validator/resolver + fixture suite (TDD)"`

### Task 7: Harness-neutral sdd skill + adapters

**Files:**
- Modify: `skills/sdd/SKILL.md`
- Create: `skills/sdd/harnesses/claude-code.md`, `skills/sdd/harnesses/codex.md`

**Interfaces:**
- Consumes: manifest fields (Tasks 3–5), `core/*` names (Task 2), validator `--resolve` (Task 6).
- Produces: Step-0 procedure Task 10 dry-runs.

- [ ] **Step 1: Rewrite `skills/sdd/SKILL.md` harness-neutral** — keep frontmatter name/description; open with: "**Harness**: identify your controlling harness and read `harnesses/<harness>.md` (claude-code, codex) before Step 0 — it maps skill-loading, native subagent dispatch, task tracking, background jobs, and asset-root resolution. All paths below are relative to the plugin tree root `<root>` (the directory containing `skills/`, `core/`, `providers/`)." Replace all `${CLAUDE_PLUGIN_ROOT}` with `<root>`; replace "Agent tool"/"Claude subagent" wording in the Flavour section with "native subagent (see adapter)"; rename the "all Claude" lever to `native-subagents` ("alias 'all Claude' under Claude Code"). Step 0 gains:

```markdown
4b. **Trust gate**: run `python3 <root>/scripts/validate-packs --root <root>` — refuse
   to proceed past a non-zero exit. THEN check `git -C <root> status --porcelain
   providers/` — any untracked or modified provider directory requires explicit user
   approval before its manifest or prose is used (git-tracked state is the trust anchor).
5. **Detect providers**: read each <root>/providers/*/pack.md manifest; a provider is
   INSTALLED iff `command -v -- "<cli>"` succeeds for its validated cli name (data-only
   manifests — never execute manifest strings as shell; argv[0]==cli is
   validator-enforced). Apply layered config (first found): $SDD_DISPATCH_CONFIG →
   <project>/.sdd-dispatch.json → ${XDG_CONFIG_HOME:-~/.config}/sdd-dispatch/config.json
   — disable/steer only; malformed/wrong-typed config, disabled default_provider or
   providers_by_lane target, or set-but-unreadable $SDD_DISPATCH_CONFIG = STOP with the
   error. ACTIVE = installed − disabled (− incompatible iff require-verified-version).
6. **Compatibility**: compare `version-argv` output to `verified-version`; mismatch →
   warn and suggest `sdd-dispatch-verify <id>` (block iff config require-verified-version).
7. **Provider routing (before any model resolution)**: FIRST, if the `native-subagents`
   lever (or per-task native directive) is in effect → bypass external dispatch entirely
   (harness-native subagents per adapter; no provider is selected). Otherwise: per-task
   provider directive → session lever → config providers_by_lane[lane-of-role] /
   default_provider → codex-if-active else sole-active-iff-exactly-one → ask. Inactive
   provider named anywhere → ask, never silently reroute.
8. **Resolve model within the routed provider**: role → (tier, lane) via core/roles.md →
   ordered candidates in the pack's models.md (eligible statuses verified/experimental;
   exact-lane rows by priority, THEN (tier, any) rows by priority — this order is the
   complete fallback sequence); take the first; none → ask the user.
   (`scripts/validate-packs --resolve "<role>" <provider>` prints the walk and order.)
9. **Readiness**: before the FIRST dispatch to a chosen provider, run its bounded
   preflight (version + session-list/auth probe per manifest); failures are
   channel-class → fallback rules.
10. **Failure classes**: channel failures (auth, model-not-found, startup stall) may
    advance to the NEXT candidate in the resolution order (same provider; max 3 total
    attempts per (task, role)); cross-provider moves are ALWAYS a user question. Ledger
    line per attempt:
    `model-attempt: task=<N> role=<role> provider=<id> model=<id> class=<channel|quality> outcome=<failed|ok>`
    — channel-failed (provider, model) pairs are excluded session-wide and rebuilt from
    the ledger after compaction; quality failures (BLOCKED, repeated review rejection)
    create no exclusion and NEVER auto-fall-back — escalate tier or adjudicate.
```

Dispatch-override sections now say "use the active pack's canonical dispatch template (pack.md) inside the self-reaping wrapper (core/liveness.md)" — delete the inlined codex/opencode templates and the per-CLI gotcha quick-list (pointer to packs instead).
- [ ] **Step 2: Write `skills/sdd/harnesses/claude-code.md`** — table mapping the five concerns: skill-load = Skill tool `superpowers:subagent-driven-development`; native subagents = Agent tool (haiku/sonnet for supervised flavour); task tracking = TodoWrite; background jobs = Bash `run_in_background` + task notifications (self-reaping wrapper inside one background call; notification == finished-or-reaped); asset root = `${CLAUDE_PLUGIN_ROOT}`. Note: lever alias "all Claude" == `native-subagents`.
- [ ] **Step 3: Write `skills/sdd/harnesses/codex.md`** — skill-load = superpowers codex adaptation (its `references/codex-tools.md`); native subagents = `spawn_agent`; task tracking = `update_plan`; background jobs = shell background + poll loop (same self-reaping wrapper, checked between turns); asset root = resolve from the physical path of this SKILL.md (`<root> = dirname(dirname(dirname(SKILL.md)))`); note (per spec): codex-as-provider under a codex controller is allowed; nested `codex exec` may be blocked by sandbox policy, so run a one-shot nested-exec probe at the first codex-lane dispatch and treat failure as a channel-class failure (user question). No prohibition.
- [ ] **Step 4: Validate** — Run: `grep -c 'CLAUDE_PLUGIN_ROOT' skills/sdd/SKILL.md skills/sdd/harnesses/codex.md` → `0` for both; `grep -c 'CLAUDE_PLUGIN_ROOT' skills/sdd/harnesses/claude-code.md` → ≥1; `grep -c 'native-subagents' skills/sdd/SKILL.md` → ≥1; `grep -rc 'references/dispatch-reference\|references/model-catalog' skills/ | grep -v ':0'` → empty.
- [ ] **Step 5: Commit** — `git add skills/sdd && git commit -m "feat(sdd): harness-neutral skill + claude-code/codex adapters, manifest-driven Step 0"`

### Task 8: verify skill + P13 fixture

**Files:**
- Modify: `skills/sdd-dispatch-verify/SKILL.md`, `core/verification-protocol.md`
- Create: `tests/fixtures/p13/{defect.diff,expected-findings.md,README.md}`

**Interfaces:** Consumes pack layout, validator.

- [ ] **Step 1: P13 fixture** — copy the smoke-2 known-defect review package `~/.claude/jobs/5dfe2f9a/tmp/smoke2-wordstats/.superpowers/sdd/review-d88cdcb..2cc2902.diff` to `tests/fixtures/p13/defect.diff`. If that path no longer exists, reconstruct: `defect.diff` = a diff adding a CLI whose file-handling is `path = Path(args.file)` / `if not path.exists(): print error, return 2` / `text = path.read_text()` — the defect being that directories and unreadable files bypass the guard and traceback. Write `expected-findings.md`: "Reviewer MUST flag (≥Important): non-file/unreadable paths (directory, permission-denied) reach read_text() and raise a traceback instead of the spec'd stderr error + exit 2 (path.exists() is an insufficient guard)." `README.md`: provenance (smoke run 2, 2026-07-22; deepseek-v4-pro caught it; nemotron-3-ultra-free false-cleaned it).
- [ ] **Step 2: Append P13 to `core/verification-protocol.md`**: "### P13 — Reviewer known-defect benchmark. Dispatch the candidate reviewer with the standard task-reviewer contract against tests/fixtures/p13/defect.diff (+ its brief context in README). PASS iff every finding in expected-findings.md is cited at equal-or-higher severity. A false-clean disqualifies the candidate for review lanes."
- [ ] **Step 2b: Contracts purity** — in `contracts/implementer-contract.md`, replace the codex-specific commit-restriction wording with sandbox-generic wording: "You must NOT run git commit/push — the controller commits after gating. (On sandboxed providers this is enforced; elsewhere it is your contract.)" Run: `grep -c 'codex' contracts/*.md` → `0`.
- [ ] **Step 3: Rewrite `skills/sdd-dispatch-verify/SKILL.md`** — pack-scoped: arg names one provider id or `--all-active`; a run edits only that pack + appends its log; cross-provider synthesis → core log. Procedure prepends: `scripts/validate-packs --root <root>` must pass before probes; new review-lane models require P13; new implement-lane models require a small-implementer probe; live P1–P12 probes are environment smoke tests (run where the CLI exists), the validator+fixtures are the portable gate. Version bump per verification commit (patch).
- [ ] **Step 4: Validate** — Run: `ls tests/fixtures/p13/` → `README.md defect.diff expected-findings.md`; `grep -c 'P13' core/verification-protocol.md skills/sdd-dispatch-verify/SKILL.md` → ≥1 each; `grep -c 'validate-packs' skills/sdd-dispatch-verify/SKILL.md` → ≥1.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat(verify): pack-scoped verify skill, P13 known-defect fixture"`

### Task 9: Tombstones, README, packaging, links

**Files:**
- Modify: 4 remaining `references/*.md` → tombstones (verification-protocol already moved), `README.md`, `.claude-plugin/plugin.json` (no version change yet)
- Create: `codex/INSTALL.md`, `references/verification-protocol.md` tombstone

**Interfaces:** Consumes final layout.

- [ ] **Step 1: Tombstones** — each of the five `references/` paths becomes exactly:

```markdown
# MOVED (v1.2.0, 2026-07-23) — removed at v1.3.0

- Archived verbatim: [archive/v1.1/<this-file>](../archive/v1.1/<this-file>)
- New homes: <exact relative links per docs/migration-1.2.0.md for THIS file>
```
- [ ] **Step 2: `codex/INSTALL.md`** — Codex installation: clone/checkout the whole repository (the skill requires `core/`, `providers/`, `contracts/` siblings — copying SKILL.md alone is unsupported); point codex skill discovery at `skills/sdd/SKILL.md`; first-run: read `skills/sdd/harnesses/codex.md`; verify with `python3 scripts/validate-packs --root .`.
- [ ] **Step 3: `README.md`** — new layout tree; install sections for BOTH harnesses (Claude marketplace commands; Codex → codex/INSTALL.md); "Adding a provider" (one directory satisfying the pack contract; run validate-packs; zero core edits); version line `**Version:** 1.2.0` placeholder as `1.1.4` for now (Task 10 syncs).
- [ ] **Step 3b: `scripts/codex-smoke`** — bash: from the repo root verify (a) `skills/sdd/SKILL.md` exists at that exact relative path; (b) `skills/sdd/harnesses/codex.md` exists; (c) root derivation `ROOT=$(cd "$(dirname skills/sdd/SKILL.md)/../.." && pwd)` yields a dir containing `core/` and `providers/`; (d) `python3 scripts/validate-packs --root "$ROOT"` exits 0. Print PASS/FAIL per check; exit non-zero on any FAIL. chmod +x. Run: `./scripts/codex-smoke` → 4 PASS lines.
- [ ] **Step 4: Link rewrite sweep** — Run: `grep -rn '](.*references/' --include='*.md' core/ providers/ skills/ contracts/ docs/migration-1.2.0.md codex/ README.md | wc -l` → `0`; `grep -rn 'sdd-external-dispatch\|model-catalog\|dispatch-reference' --include='*.md' core/ providers/ skills/ README.md | wc -l` → `0` (tombstones point to archive/ + new homes; archive/ itself exempt).
- [ ] **Step 5: Commit** — `git add -A && git commit -m "refactor: tombstones with exact destinations, dual-harness README, codex INSTALL"`

### Task 10: Release 1.2.0

**Files:** Modify: `.claude-plugin/plugin.json`, `README.md` (version sync), `core/verification-log.md`

- [ ] **Step 1: Full gate** — Run: `./scripts/validate-packs --root . && echo CLEAN` → `CLEAN`. Run: `uv run --with pytest pytest tests/ -q` → all pass (incl. --step0 and exclusion-fallback cases). Run: `./scripts/codex-smoke` → 4 PASS.
- [ ] **Step 2: Resolution walks (document in commit message)** — Run: `./scripts/validate-packs --root . --resolve "per-task reviewer" opencode` → `opencode-go/deepseek-v4-pro (P1, verified)`; `--resolve "transcription implementer" codex` → `gpt-5.6-luna (P1, verified)`; `--resolve "adaptation implementer" agy` → `gemini-3.6-flash-medium (P1, experimental)`.
- [ ] **Step 3: Detection dry-run (environment smoke, NON-BLOCKING)** — Run: `for p in providers/*/; do cli=$(sed -n 's/^cli: //p' "$p/pack.md" | head -1); command -v -- "$cli" >/dev/null && echo "$(basename $p): installed" || echo "$(basename $p): absent"; done` → report the lines as-is; absent CLIs are recorded in the release log entry, never a release blocker.
- [ ] **Step 3b: Fresh-clone codex smoke** — Run: `T=$(mktemp -d) && git clone -q . "$T/clone" && (cd "$T/clone" && ./scripts/codex-smoke) && rm -rf "$T"` → 4 PASS lines from the clone.
- [ ] **Step 3c: Claude install/load smoke (this machine)** — reinstall the plugin (`/plugin marketplace add <repo path>` + `/plugin install sdd-dispatch@sdd-dispatch-marketplace` + `/reload-plugins`, or the harness-appropriate reinstall), then confirm the `sdd` skill loads and its Step 0 reaches the trust gate. Record the result in the release log entry; if the harness session cannot perform the reinstall mid-plan, record it as a post-release user step in the ledger and DO NOT silently skip the record.
- [ ] **Step 4: Config tests** — Run: `./scripts/validate-packs --check-config tests/fixtures/config-malformed.json; echo "exit=$?"` → `exit=1`; same for `config-disabled-default.json` → `exit=1`.
- [ ] **Step 5: Migration log entry** — append to `core/verification-log.md`: date, "v1.2.0 provider-pack migration", pointer to `docs/migration-1.2.0.md`, gate results (validator CLEAN, N pytest passed, detection results), and the three resolution walks.
- [ ] **Step 6: Version sync** — `sed -i 's/"version": "1.1.4"/"version": "1.2.0"/' .claude-plugin/plugin.json` and set README version line to `1.2.0`.
- [ ] **Step 7: Final commit** — `git add -A && git commit -m "release: v1.2.0 provider-pack architecture (validate-packs CLEAN; resolution walks: reviewer→deepseek-v4-pro, transcription→luna, adaptation→3.6-flash-medium)"`
