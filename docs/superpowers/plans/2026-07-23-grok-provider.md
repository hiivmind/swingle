# Grok CLI Provider Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `providers/grok/` as a first-class dispatch pack (v1.6.0) so `via grok` works for `sdd` / `delegate` / `sdd-dispatch-verify`, with live P1–P13 evidence and surface naming updates.

**Architecture:** Standard fourth provider pack under `providers/grok/` (manifest-driven; zero `core/` logic changes). Live verification in a scratchpad settles provisional fields (`report-transport`, `sandbox`, `stall-signal`, model Status, optional `--cwd` / `--output-format` promotion). Version bump + provider-name lists on docs/skill frontmatter only.

**Tech Stack:** Markdown provider packs; `scripts/validate-packs` + `scripts/codex-smoke`; live `grok` 0.2.111 CLI; pytest structural suite.

**Spec:** `docs/superpowers/specs/2026-07-23-grok-provider-design.md` (rev 2, GLM 5.2 findings folded) — the authority for all behavior below.

## Global Constraints

- Work on branch `feature/grok-provider` (already seeded from `main` at v1.5.0 design commit); never commit to `main` without PR.
- Before EVERY commit: `python3 scripts/validate-packs --root . && ./scripts/codex-smoke` must exit 0 (chain with `&&`, never `;`).
- Purity: model ids and invocation strings live only in `providers/grok/`; skills/core may list provider **names** only.
- Model Status cells are a **single** enum ∈ `{verified, experimental, unavailable, superseded, rejected}` — never `experimental → verified`.
- Canonical dispatch template ships only **smoke-verified** flags (`-p`, `-m`, `--always-approve`). Promote `--cwd` / `--output-format plain` only after P11 Confirms.
- `resume-argv` is `["grok", "--resume", "{session_id}"]` — **no** embedded `-p` (agy convention; skill appends `-p "<prompt>"`).
- `verified-version: "0.2.111"` only after P2 + P6(file+shell) + implement-shaped on-disk evidence.
- Live probes run in `$SCRATCH` (mktemp), never the plugin working tree for destructive writes.
- Verification log is append-only; Incomplete is honest; never invent Confirmed.
- Version triad 1.6.0: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, README `**Version:**`.

## File map

| Path | Responsibility |
| --- | --- |
| `providers/grok/pack.md` | Manifest + dispatch surface + gotchas + canonical template |
| `providers/grok/models.md` | Tier/lane → `grok-4.5` candidates |
| `providers/grok/verification-log.md` | Append-only P1–P13 + resume evidence |
| `README.md` | CLI list, version, install PATH note |
| `.claude-plugin/plugin.json` | version + keyword `grok` |
| `.codex-plugin/plugin.json` | version + interface text mentioning grok |
| `skills/sdd/SKILL.md` | description provider list |
| `skills/delegate/SKILL.md` | description provider list |
| `skills/*/agents/openai.yaml` | short_description provider list |
| `CLAUDE.md` | one-line provider list |

---

### Task 1: Author `providers/grok/` (experimental; smoke-verified template)

**Files:**
- Create: `providers/grok/pack.md`
- Create: `providers/grok/models.md`
- Create: `providers/grok/verification-log.md`

**Interfaces:**
- Consumes: pack contract grammar from `scripts/validate-packs` (`REQ`, `ENUMS`, models table columns).
- Produces: a pack that validates and is PATH-detectable as `cli: grok` for Task 2 probes and Task 3 surfaces.

- [ ] **Step 1: Create `providers/grok/pack.md`**

Exact content:

````markdown
---
schema-version: 1
id: grok
cli: grok
verified-version: "0.2.111"
version-argv: ["grok", "--version"]
resume-argv: ["grok", "--resume", "{session_id}"]
fork-flag: "--fork-session"
session-source: session-list
session-list-argv: ["grok", "sessions", "list"]
stall-signal: log-age
report-transport: report-file
sandbox: none
readiness-argv: ["grok", "models"]
---

## Cross-CLI comparison — grok cells

| Property | grok 0.2.111 |
| --- | --- |
| Prompt argument | `-p` / `--single` (also `--prompt-file`) |
| `< /dev/null>` needed | **No** (verified smoke; harmless insurance) |
| Sandbox | Built-ins (`none`, `workspace`, `read-only`); unknown profile **fails closed** |
| Permission flags | **`--always-approve`** for implement (shell + file). `acceptEdits` alone / with always-approve: shell silent no-op |
| Exit codes | Often 0 even on model/tool failure — **not work evidence** |
| Model validation | Local error text (`unknown model id`); exit may still be 0 |
| Reasoning-effort control | `--reasoning-effort` / `--effort` (P9 for invalid/silent-ignore) |
| Output contract | stdout final message (P10 for diversion / report-file) |
| Auth | grok.com / OAuth (`grok login`); SuperGrok for higher limits |
| Changelog | product/docs for Grok Build CLI — re-read on every version bump |

## Resume — a kill is a checkpoint, not a restart

| CLI | Resume |
| --- | --- |
| grok | `grok --resume <session_id>` (+ skill-appended `-p "<prompt>"`); `-c` for most-recent in cwd; `--fork-session` to branch |

Session ids: `grok sessions list` (UUID column). Working-tree progress survives kill — `git diff` before resuming.

**Assembly rule (matches agy):** `resume-argv` does **not** embed `-p`. The skill appends
`-p "<continuation>"` (and `--always-approve` for write work). Fork form:

```bash
grok --resume <session_id> --fork-session -p "<continuation>" --always-approve
```

## grok (verified surface seed 0.2.111, 2026-07-23)

### Verified behavior (pre-design smoke + design review)

- **`--always-approve` alone** is the implement ceiling: file write and shell write both
  land on disk. `--permission-mode acceptEdits --always-approve` and `auto+always-approve`
  produce **silent shell no-ops** (exit 0, empty tree) — do not use as implement flags.
- **Exit 0 is not success**: bogus model prints an error and can still exit 0.
- **No stdin hang** under piped input (unlike codex/agy).
- **Sandbox unknown profile refuses to start** rather than running unsandboxed.
- Fallback if `--always-approve` regresses: `--permission-mode bypassPermissions`.

### Canonical dispatch template

```bash
grok -p "<PROMPT>" -m <model> --always-approve
```

Optional: `< /dev/null` at the end (not mandatory).

Provisional (do **not** treat as canonical until P11 Confirms in verification-log):
`--cwd <repo>`, `--output-format plain`.

### Gotchas

1. Exit codes are not work evidence — gate on stdout + on-disk effects.
2. `acceptEdits` is not a safe implement ceiling (shell silent no-op).
3. `-p` / `--single` = one user turn with multi-tool agency; `--prompt-file` for large briefs.
4. Stdin close optional.
5. Unknown sandbox profile fails closed.
6. Only `grok-4.5` in inventory as of 0.2.111.
7. Quota exhaustion is a **dispatch-time channel failure** (upsell message on the
   dispatch). `readiness-argv` (`grok models`) proves the CLI answers, not remaining quota.
````

- [ ] **Step 2: Create `providers/grok/models.md`**

Exact content:

````markdown
# grok models (Grok Build / xAI) — seeded 2026-07-23

## Resolvable

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; transcription/explore |
| standard | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; default implement/review |
| most-capable | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; final review until inventory grows |

Effort: document `--reasoning-effort` / `--effort` only after P9 in the verification log.

## Documentary

(none yet)

## Watch list

- Additional models appearing in `grok models` after CLI updates — evaluate with P12
  before any table slot.
````

- [ ] **Step 3: Create `providers/grok/verification-log.md`**

Exact content:

````markdown
# SDD Dispatch Verification Log — grok

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-23 — grok 0.2.111 (trigger: new provider pack; pre-design smokes)

Pre-pack smokes recorded in
`docs/superpowers/specs/2026-07-23-grok-provider-design.md` §Pre-design live smoke.
Full P1–P13 suite: see next entry after Task 2 of the implementation plan.

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 (partial) | version surface | **Confirmed** | `grok --version` → `0.2.111 (94172f2aa4) [stable]` |
| P2 (partial) | trivial `-p` | **Confirmed** | `QUOTA_OK` / `PONG`-class replies, exit 0 |
| P3 (partial) | bogus model | **Confirmed** | error text `unknown model id`; exit 0 (not a failure signal) |
| P4 (partial) | stdin hang | **Refuted** (not mandatory) | piped stdin completed |
| P6 (partial) | shell under `--always-approve` | **Confirmed** | `shell.txt` = `SHELL_OK` on disk |
| P6 (partial) | shell under acceptEdits+always-approve | **Confirmed** (failure mode) | silent no-op, exit 0, empty tree |

Incomplete: full numbered suite, P7–P13, resume/fork, `--cwd` / `--output-format`, P9 invalid effort.
````

- [ ] **Step 4: Validate the pack**

Run:

```bash
python3 scripts/validate-packs --root .
./scripts/codex-smoke
```

Expected: exit 0 both. If Status cells or manifest fields fail, fix before continuing — do not commit a red gate.

- [ ] **Step 5: Commit**

```bash
git add providers/grok/
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  git commit -m "$(cat <<'EOF'
feat(providers): add grok pack skeleton (experimental models)

Fourth provider pack for Grok Build CLI 0.2.111: smoke-verified template
(--always-approve), agy-aligned resume-argv, provisional sandbox/report-transport.
EOF
)"
```

---

### Task 2: Live verification suite (P1–P13 + resume/fork)

**Files:**
- Modify: `providers/grok/verification-log.md` (append full suite entry)
- Modify: `providers/grok/pack.md` (promote verified fields only)
- Modify: `providers/grok/models.md` (Status → `verified` only if evidence warrants)

**Interfaces:**
- Consumes: pack from Task 1; `core/verification-protocol.md` probe definitions.
- Produces: evidence-backed pack facts for Task 3 surfaces.

- [ ] **Step 1: Prepare scratchpad**

```bash
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/sdd-grok-verify.XXXXXX")
echo "SCRATCH=$SCRATCH"
# record version first
grok --version | tee "$SCRATCH/version.txt"
grok models | tee "$SCRATCH/models.txt"
```

Never run destructive probes inside the plugin repo working tree.

- [ ] **Step 2: Run P2–P6 under backstops**

Use `timeout` on every probe. Record raw exit status **without** masking with pipes
(`set -o pipefail` or capture `ec=$?` before any filter).

```bash
# P2
timeout 60 grok -p "Reply with exactly the word PONG and nothing else. Do not use any tools." \
  -m grok-4.5 --always-approve >"$SCRATCH/p2.out" 2>"$SCRATCH/p2.err"; echo P2_EC:$?
# P3
timeout 60 grok -p "hi" -m not-a-real-model-xyz --always-approve \
  >"$SCRATCH/p3.out" 2>"$SCRATCH/p3.err"; echo P3_EC:$?
# P4 — never-closing stdin under 60s backstop
timeout 60 bash -c 'grok -p "Reply:P4OK" -m grok-4.5 --always-approve <&- 2>&1 || true' \
  >"$SCRATCH/p4.out"; echo P4_EC:$?
# or: (sleep 120 | grok -p "Reply:P4OK" -m grok-4.5 --always-approve) with timeout 60
# P5 flagless read
echo 'the secret word is XYZZY42' >"$SCRATCH/readtest.txt"
timeout 90 grok -p "Read the file readtest.txt and tell me the secret word." \
  --cwd "$SCRATCH" >"$SCRATCH/p5.out" 2>"$SCRATCH/p5.err"; echo P5_EC:$?
# P6 flagless write
timeout 90 grok -p "Create a file named writetest.txt containing exactly HELLO." \
  --cwd "$SCRATCH" >"$SCRATCH/p6a.out" 2>"$SCRATCH/p6a.err"; echo P6A_EC:$?
# P6 canonical flags file + shell
timeout 120 grok -p "Create file ftool.txt with FTOOL_OK using a file tool. Then using shell only: printf 'SHELL_OK\n' > shell.txt. Reply DONE." \
  -m grok-4.5 --cwd "$SCRATCH" --always-approve \
  >"$SCRATCH/p6b.out" 2>"$SCRATCH/p6b.err"; echo P6B_EC:$?
ls -la "$SCRATCH"; cat "$SCRATCH/writetest.txt" "$SCRATCH/ftool.txt" "$SCRATCH/shell.txt" 2>/dev/null
```

On-disk content is the verdict, not agent prose.

- [ ] **Step 3: Run P7–P11**

```bash
# P7 sandbox (inside / outside / tmp) — only if claiming enforced later
timeout 120 grok -p "Write INSIDE: in.txt=IN. Write /tmp/grok-p7-out.txt=TMP. Write $HOME/grok-p7-escape.txt=OUT. Report per path." \
  -m grok-4.5 --cwd "$SCRATCH" --sandbox workspace --always-approve \
  >"$SCRATCH/p7.out" 2>"$SCRATCH/p7.err"; echo P7_EC:$?
# P8 git commit
git -C "$SCRATCH" init && git -C "$SCRATCH" config user.email t@t && git -C "$SCRATCH" config user.name t
echo seed >"$SCRATCH/seed.txt" && git -C "$SCRATCH" add seed.txt && git -C "$SCRATCH" commit -m seed
timeout 180 grok -p "Create newfile.txt with hi, git add, git commit -m 'test commit'. Report success/fail." \
  -m grok-4.5 --cwd "$SCRATCH" --always-approve \
  >"$SCRATCH/p8.out" 2>"$SCRATCH/p8.err"; echo P8_EC:$?
git -C "$SCRATCH" log --oneline | head
# P9 effort
timeout 60 grok -p "Reply:OK" -m grok-4.5 --reasoning-effort low --always-approve \
  >"$SCRATCH/p9a.out" 2>"$SCRATCH/p9a.err"; echo P9A_EC:$?
timeout 60 grok -p "Reply:OK" -m grok-4.5 --reasoning-effort not-a-real-effort --always-approve \
  >"$SCRATCH/p9b.out" 2>"$SCRATCH/p9b.err"; echo P9B_EC:$?
# P10 document + report path
timeout 180 grok -p "Write a 200-word design note about widget caches to $SCRATCH/p10-report.md using a normal file write. Also put a one-line summary as your final message." \
  -m grok-4.5 --always-approve >"$SCRATCH/p10.out" 2>"$SCRATCH/p10.err"; echo P10_EC:$?
wc -c "$SCRATCH/p10.out" "$SCRATCH/p10-report.md" 2>/dev/null
# P11 --cwd and --output-format buffering
mkdir -p "$SCRATCH/cwdtest"
timeout 90 grok -p "Write only the text CWD_OK into landed.txt in the current working directory. Reply DONE." \
  -m grok-4.5 --cwd "$SCRATCH/cwdtest" --always-approve \
  >"$SCRATCH/p11cwd.out" 2>"$SCRATCH/p11cwd.err"; echo P11CWD_EC:$?
cat "$SCRATCH/cwdtest/landed.txt" 2>/dev/null || echo CWD_MISS
# buffering: watch log mtime while long thinking prompt runs under pipe
timeout 90 grok -p "Count slowly to 5 in your head then reply: STREAM_OK" \
  -m grok-4.5 --always-approve --output-format plain \
  >"$SCRATCH/p11plain.out" 2>"$SCRATCH/p11plain.err" &
BPID=$!
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 3
  echo "t=$((i*3))s bytes=$(wc -c <"$SCRATCH/p11plain.out" 2>/dev/null || echo 0)"
done
wait $BPID; echo P11PLAIN_EC:$?
```

- [ ] **Step 4: Run P12–P13 + resume/fork**

```bash
# P12 — inventory already in models.txt; one P2 per listed model
# P13 — only if claiming review lane verified
timeout 300 grok -p "Read contracts/task-reviewer-contract.md and tests/fixtures/p13/README.md and tests/fixtures/p13/defect.diff and tests/fixtures/p13/expected-findings.md. Produce a task-reviewer report. PASS only if every expected finding is cited at equal-or-higher severity." \
  -m grok-4.5 --always-approve \
  --cwd "$(pwd)" >"$SCRATCH/p13.out" 2>"$SCRATCH/p13.err"; echo P13_EC:$?

# Resume: capture session id from sessions list after a short dispatch, then continue
timeout 60 grok -p "Remember the codeword ZEBRA42. Reply READY." -m grok-4.5 --always-approve \
  >"$SCRATCH/resume1.out"; echo R1_EC:$?
SID=$(grok sessions list -n 3 2>/dev/null | awk 'NR==3{print $1}')
echo "SID=$SID"
timeout 60 grok --resume "$SID" -p "What was the codeword? Reply with only the codeword." --always-approve \
  >"$SCRATCH/resume2.out"; echo R2_EC:$?
# Fork
timeout 60 grok --resume "$SID" --fork-session -p "Reply FORKED_OK" --always-approve \
  >"$SCRATCH/fork.out"; echo FORK_EC:$?
```

If P13 fails or is too expensive, record Incomplete for review-lane claim and leave
models Status experimental for review rationale — do not mark review lane verified.

- [ ] **Step 5: Append verification-log entry and update pack facts**

Append a new `## 2026-07-23 — grok 0.2.111 (trigger: new provider; full suite)` table
with every probe's Confirmed/Refuted/Refined/New/Incomplete verdict and one-line evidence.

Then, **only where evidence supports it**:

| Field | Promote when |
| --- | --- |
| `models.md` Status → `verified` | P2 + implement-shaped on-disk work succeeded |
| `verified-version` stamp | P2 + P6 file+shell + implement-shaped report |
| `report-transport` | P10 settles report-file vs captured-output |
| `sandbox` | P7 proves real containment → `enforced`, else stay `none` |
| `stall-signal` | P11 plain buffering → keep `log-age` or document change |
| Canonical template adds `--cwd` / `--output-format plain` | P11 Confirms both |

Do not leave Status as `experimental → verified`. Single enum only.

- [ ] **Step 6: Validate + commit**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  git add providers/grok/ && \
  git commit -m "$(cat <<'EOF'
docs(providers/grok): record live verification suite for 0.2.111

Append P1–P13 and resume/fork evidence; promote pack facts only where
on-disk probes Confirmed them.
EOF
)"
```

- [ ] **Step 7: Clean scratchpad**

```bash
rm -rf "$SCRATCH"
# also remove any accidental $HOME/grok-p7-escape.txt or /tmp/grok-p7-out.txt from P7
rm -f "$HOME/grok-p7-escape.txt" /tmp/grok-p7-out.txt
```

---

### Task 3: Surface updates + version 1.6.0

**Files:**
- Modify: `README.md`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `skills/sdd/SKILL.md` (description frontmatter only)
- Modify: `skills/delegate/SKILL.md` (description frontmatter only)
- Modify: `skills/sdd/agents/openai.yaml`
- Modify: `skills/delegate/agents/openai.yaml`
- Modify: `CLAUDE.md` (opening one-liner only)

**Interfaces:**
- Consumes: verified pack from Tasks 1–2.
- Produces: installable 1.6.0 surfaces that name grok alongside existing providers.

- [ ] **Step 1: Bump version triad to 1.6.0**

In `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`: set `"version": "1.6.0"`.

In `.claude-plugin/plugin.json`:
- description: change `(codex/opencode/agy)` → `(codex/opencode/agy/grok)`
- keywords: add `"grok"`

In `.codex-plugin/plugin.json`:
- description / longDescription: include grok in the provider list
- keywords: add `"grok"` if useful

In `README.md`:
- Line with `CLIs (codex / opencode / agy)` → include `grok`
- `**Version:** 1.5.0` → `**Version:** 1.6.0`
- Install PATH note: mention `grok` beside `codex`, `opencode`, `agy`

- [ ] **Step 2: Skill frontmatter provider lists**

Replace `codex/opencode/agy` with `codex/opencode/agy/grok` in:

- `skills/sdd/SKILL.md` description
- `skills/delegate/SKILL.md` description
- `skills/sdd/agents/openai.yaml` short_description
- `skills/delegate/agents/openai.yaml` short_description

Do **not** add model ids or dispatch invocation strings to skill bodies.

- [ ] **Step 3: `CLAUDE.md` one-liner**

Opening line provider list: `(codex / opencode / agy)` → `(codex / opencode / agy / grok)`.

- [ ] **Step 4: Full gate**

```bash
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  uv run --with pytest pytest tests/ -q
```

Expected: validate-packs exit 0, codex-smoke exit 0, pytest all pass.

- [ ] **Step 5: Commit**

```bash
git add README.md .claude-plugin/plugin.json .codex-plugin/plugin.json \
  skills/sdd/SKILL.md skills/delegate/SKILL.md \
  skills/sdd/agents/openai.yaml skills/delegate/agents/openai.yaml \
  CLAUDE.md
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  uv run --with pytest pytest tests/ -q && \
  git commit -m "$(cat <<'EOF'
chore: v1.6.0 surface updates for grok provider

Bump version triad, name grok in skill/README/plugin surfaces.
EOF
)"
```

---

### Task 4: Final verification + PR readiness

**Files:** none new (read-only checks)

- [ ] **Step 1: Detection smoke**

```bash
command -v grok
python3 scripts/validate-packs --root . --step0 2>/dev/null || python3 scripts/validate-packs --root .
# confirm pack id present
ls providers/grok/
grep -E '^id:|^cli:|^verified-version:' providers/grok/pack.md
```

Expected: `grok` on PATH; pack validates; id/cli match.

- [ ] **Step 2: One end-to-end implement-shaped dispatch (if not already in Task 2)**

In a fresh scratch git repo, dispatch a tiny implement brief that writes a report path
using the canonical template; confirm on-disk report + tree mutation; confirm HEAD
unchanged if agent tries to commit (controller-commits).

- [ ] **Step 3: Status / purity final check**

```bash
# no transition strings in Status column
grep -n '→' providers/grok/models.md && exit 1 || true
# no model ids in skills body (frontmatter provider names OK)
rg -n 'grok-4\.5' skills/ && exit 1 || true
python3 scripts/validate-packs --root . && ./scripts/codex-smoke && \
  uv run --with pytest pytest tests/ -q
```

- [ ] **Step 4: Summarize for PR**

Draft PR body covering: fourth pack, key gotchas (exit 0, acceptEdits silent no-op,
resume-argv), verification summary table, version 1.6.0. Open PR to `main` only when
the user asks.

---

## Spec coverage checklist

| Spec section | Task |
| --- | --- |
| Layout `providers/grok/*` | Task 1 |
| Manifest fields + resume-argv without `-p` | Task 1 |
| Smoke-verified canonical template | Task 1 |
| models.md single-enum Status | Task 1 → promote Task 2 |
| P1–P13 + resume/fork | Task 2 |
| Provisional field promotion rules | Task 2 |
| Surface updates + 1.6.0 | Task 3 |
| Success criteria / purity | Task 4 |
| Out of scope (core, harness, default_provider) | — not in plan |

## Placeholder scan

None intentional. Live probe commands are concrete; verdicts depend on on-disk results
and must be written honestly.
