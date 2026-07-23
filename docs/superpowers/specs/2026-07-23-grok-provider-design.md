# Grok CLI Provider Pack — sdd-dispatch v1.6.0

Date: 2026-07-23  
Status: **approved** (rev 3 — official Grok CLI user-guide folded in)  
Target version: **1.6.0**  
Branch: `feature/grok-provider` (seeded from `main` / v1.5.0)  
Design review: `.sdd-dispatch/delegate/001-review.md` (opencode / `opencode-go/glm-5.2`,
2026-07-23) — Verdict: *Sound with required changes*; Important + Minor findings
addressed in rev 2.  
**Rev 3:** pack facts re-anchored on the **shipped Grok CLI user guide**
(`~/.grok/docs/user-guide/`, especially `14-headless-mode.md`,
`17-sessions.md`, `18-sandbox.md`, `22-permissions-and-safety.md`) and
`~/.grok/README.md` — not on first-principles reverse-engineering. Live
verification still stamps behavior that can flip per version (exit codes, model
inventory, silent permission footguns); it does **not** re-litigate documented
first-class flags.

## Purpose

Add **Grok Build CLI** (`grok`, xAI) as a first-class dispatch provider pack so
`sdd` / `delegate` / `sdd-dispatch-verify` can route work with `via grok` the same
way they route `via codex` / `via opencode` / `via agy`.

This is **Grok as a dispatch target**, not Grok as a controller harness. A
`skills/sdd/harnesses/grok.md` adapter is out of scope for this round.

## Constraints (from architecture)

- Provider packs are self-contained under `providers/<id>/`.
- **Zero required edits to `core/`** for a new provider; routing is manifest-driven.
- Provider *names* may appear in skill frontmatter / README / keywords; **model ids
  and invocation strings live only in the pack**.
- New capability differences that skills must branch on become **manifest fields**,
  not provider-name special-cases in skills.
- `verified-version` is stamped only after live end-to-end dispatch evidence in the
  pack's verification log.
- **Versioning:** new provider (feature) ⇒ plugin **minor** bump (1.5.0 → **1.6.0**);
  subsequent in-pack fact edits ⇒ **patch** per `CLAUDE.md`. Keep
  `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and README
  `**Version:**` in sync.
- Hard gate before every commit:
  `python3 scripts/validate-packs --root . && ./scripts/codex-smoke && …`

## Approach chosen

**Approach A — standard fourth pack.**

Rejected:

- **B — Grok as controller harness**: separate product surface.
- **C — docs-only stub**: undercuts the hard-gate / evidence story; user requested
  full pack + live verify.

## Pre-design live smoke (this machine, 2026-07-23)

CLI: `grok 0.2.111 (94172f2aa4) [stable]`. Auth: grok.com session present.
Models inventory: only `grok-4.5` (default). Free-tier quota was exhausted mid-design
and recovered after SuperGrok subscription.

| Probe-shaped check | Result |
| --- | --- |
| Version | `grok --version` / `grok version` → `0.2.111` |
| Trivial `-p` | `Reply with exactly: QUOTA_OK` → `QUOTA_OK`, exit 0 |
| File write | `--permission-mode acceptEdits --always-approve` wrote `probe.txt` |
| Shell write | **`--always-approve` alone** and **`--permission-mode bypassPermissions`** wrote `shell.txt` with `SHELL_OK` |
| Shell under `acceptEdits` + `always-approve` | **Silent no-op**: exit 0, empty tree, empty/near-empty stdout |
| Shell under `auto` + `always-approve` | Same silent no-op |
| Stdin hang | Piped stdin completed; `< /dev/null` **not mandatory** |
| Bogus model | Error text (`unknown model id`); **exit 0** — exit code is not a failure signal |
| Sessions | `grok sessions list` prints UUID column; resume via `-r` / `--resume` |
| Sandbox | Built-ins include at least `none`, `workspace`, `read-only`; unknown profile **refuses to start** rather than run unsandboxed |
| `--prompt-file` | Works for single-turn headless (documented) |
| `--reasoning-effort` | Documented levels; P9 still checks invalid/silent-ignore on this version |
| `--cwd` / `--output-format` | **Documented first-class headless flags** (14-headless-mode) — not provisional |

### Authority: official headless surface (user-guide 14 / 17 / 18 / 22)

| Fact | Source |
| --- | --- |
| Headless trigger | `-p` / `--single`, `--prompt-file`, `--prompt-json` |
| Always-approve | `--always-approve` ≡ `--yolo` ≡ `--permission-mode bypassPermissions` |
| Working directory | `--cwd <PATH>` (project root discovery walks up from cwd for `.git`) |
| Output formats | `plain` (default), `json` (includes `sessionId`), `streaming-json` (NDJSON; streams) |
| Session resume | `grok -p "…" --resume <id>` or `-c`; capture id via `--output-format json \| jq -r .sessionId` |
| New named session UUID | `-s` / `--session-id` creates only (must be UUID; does **not** resume) |
| Fork | `--fork-session` with `-r`/`-c` (optional `-s` names child UUID) |
| Stdin | Headless **does not** read piped stdin into the prompt (no hang class) |
| Sandbox profiles | `off` (default), `workspace`, `read-only`, `strict`, `devbox` — OS-enforced (Landlock/Seatbelt) |
| Review isolation | `--sandbox read-only` for exploration/code review (writes only `~/.grok/` + temp) |
| Implement isolation | `--sandbox workspace` (write CWD + temp + `~/.grok/`) when containment wanted |
| Exit codes (documented) | `0` success, `1` error, `130` SIGINT, `143` SIGTERM |
| Effort levels | `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` (+ per-model menu ids) |
| `--permission-mode` caveat | Flag only fully enables **`bypassPermissions`** and **`default`**; `acceptEdits` / `dontAsk` / `plan` via the flag are accepted but **do not enable that policy** — set via `defaultMode` in settings. Explains smoke: `acceptEdits` + shell looked like silent no-op |

**Permission ceiling (docs + smoke):**

Canonical unattended implement flags: **`--always-approve`** (or `--yolo`). That is
the documented always-approve path for headless automation. Do **not** use
`--permission-mode acceptEdits` for implement dispatches — the CLI flag does not
actually enable acceptEdits policy (user-guide 22), and smoke showed shell no-ops.
Optional containment: add `--sandbox workspace` for implement, `--sandbox read-only`
for review. Never treat exit 0 alone as proof of work when smoke shows counterexamples
(bogus model); controller diff-after / report-exists remains the gate.

## Pack contract

### Layout

```
providers/grok/
  pack.md               # YAML front matter + dispatch surface + gotchas
  models.md             # tier/lane → model table
  verification-log.md   # append-only P1–P13 results
```

### Manifest (front matter of `pack.md`)

```yaml
---
schema-version: 1
id: grok
cli: grok
verified-version: "0.2.111"   # only after P2 + P6(file+shell) + implement-shaped on-disk evidence
version-argv: ["grok", "--version"]
resume-argv: ["grok", "--resume", "{session_id}"]
fork-flag: "--fork-session"
session-source: exec-output
session-list-argv: ["grok", "sessions", "list"]
stall-signal: log-age
report-transport: report-file
sandbox: enforced
readiness-argv: ["grok", "models"]
---
```

Notes:

- **`session-source: exec-output`** — preferred capture is `--output-format json` →
  `.sessionId` (user-guide 14/17). `session-list-argv` remains available as a fallback
  (`grok sessions list`) when plain output was used. (If the validator requires
  `session-list-argv` only for `session-source: session-list`, keep the field optional
  and document list as recovery.)
- **`resume-argv` excludes the prompt flag** — matches agy. Skills append
  `-p "<continuation>"` (and implement flags). Documented form:
  `grok -p "…" --resume <id>` (flag order flexible).
- **`fork-flag`:** with resume, insert `--fork-session` before skill-appended `-p`:
  `grok --resume <id> --fork-session -p "<continuation>" --always-approve`.
- **`sandbox: enforced`** — Grok has real OS-level profiles (`workspace`, `read-only`,
  `strict`, …). Pack prose documents which profile the template uses per lane; P7
  confirms on this machine/kernel rather than discovering whether a sandbox exists.
- **`stall-signal: log-age`** — for implement logs prefer progressive output. When
  capturing session ids use `--output-format json` (single object at end — do not use
  log-age against a silent json buffer; the self-reaping wrapper watches the CLI
  process). For long plain/streaming runs, `streaming-json` advances log mtime.
- **`report-transport: report-file`** default; P10 only flips if agent-authored
  workspace report paths fail (unlikely given normal file tools).
- No new manifest fields required for v1.6.0.

### Canonical dispatch template

**Implement (documented headless automation pattern):**

```bash
grok -p "<PROMPT>" \
  -m <model> \
  --cwd <repo> \
  --always-approve \
  --sandbox workspace \
  --output-format plain
```

Aliases: `--yolo` ≡ `--always-approve`. For session-id capture on the same run, use
`--output-format json` and parse `.sessionId` / `.text`.

**Review (read-only intent + enforced sandbox):**

```bash
grok -p "<PROMPT>" \
  -m <model> \
  --cwd <repo> \
  --always-approve \
  --sandbox read-only \
  --output-format plain
```

(`read-only` still allows writes to `~/.grok/` + temp for session persistence; project
tree writes are blocked at the kernel.)

Optional: `< /dev/null` is unnecessary (stdin not consumed) but harmless.

Resume (after kill / fix loop) — skill assembles from `resume-argv` + prompt flag:

```bash
grok --resume <session_id> -p "<continuation prompt>" --always-approve --cwd <repo>
# fork:
grok --resume <session_id> --fork-session -p "<continuation>" --always-approve --cwd <repo>
```

Sandbox on resume is **session-fixed** (user-guide 18): omit `--sandbox` on resume or
pass the same profile; a different profile is refused.

Session id sources (prefer in order):

1. `--output-format json` → `.sessionId`
2. `grok sessions list` (cwd-scoped UUID column)

### Gotchas to document in pack.md (seed list; verify may refine)

1. **Do not use `--permission-mode acceptEdits` for headless implement** — the flag
   does not enable acceptEdits policy (only `bypassPermissions` / `default` via that
   flag); use `--always-approve` / `--yolo`.
2. **Exit 0 is documented success, but smoke saw exit 0 on bogus model** — still gate
   on stdout content + on-disk effects, not exit alone.
3. **`-p` / `--single`** = one user turn with multi-tool agency; `--prompt-file` for
   large briefs. Headless does not ingest piped stdin as prompt.
4. **`-s` is create-only** (UUID) — never use it to resume; use `-r` / `-c`.
5. **Sandbox unknown / unapplyable custom profile fails closed**; built-in profiles
   are real. Resume cannot change sandbox profile.
6. **Model inventory is thin** — only `grok-4.5` listed on this machine as of 0.2.111;
   all tiers map to it until `grok models` grows.
7. **Quota exhaustion** is a **dispatch-time channel failure** (upsell on the
   dispatch). `grok models` readiness does not prove remaining quota.
8. **Primary docs path for re-verify:** `~/.grok/docs/user-guide/` (versioned with the
   install) — read headless/permissions/sandbox/sessions on every CLI bump before
   probing.

### models.md

Status cells must be a **single** enum value from
`{verified, experimental, unavailable, superseded, rejected}` — never a transition
string like `experimental → verified` (validator rejects it and the hard gate fails).

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; transcription/explore |
| standard | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; default implement/review |
| most-capable | any | 1 | grok-4.5 | experimental | seat / SuperGrok | sole inventory row; final review until inventory grows |

Status rules:

- Author the pack with `experimental` while only pre-design smokes exist.
- In the same PR, after P2/P12 and an implement-shaped dispatch leave on-disk evidence,
  rewrite the Status cells to `verified` (single enum) and stamp `verified-version`.
- If a required probe blocks, leave Status as `experimental`, keep an honest
  Incomplete verification-log entry, and do **not** invent Confirmed rows.
- Documentary / watch list: empty unless `grok models` grows during verify.

Effort control: document `--reasoning-effort` / `--effort` only after P9 records
valid / invalid / silent-ignore behavior.

## Verification plan (this PR)

Run the full suite from `core/verification-protocol.md` in a scratchpad (never the
plugin repo working tree for destructive probes). Prefer the verify skill
(`sdd-dispatch-verify grok`) once the pack directory exists and validates.

Minimum to stamp `verified-version: "0.2.111"`:

- P1 version + surface
- P2 trivial success with captured stdout
- P6 **file tool and shell command** under canonical flags (both on disk)
- At least one implement-shaped dispatch that writes a report path (or, if P10 forces
  `captured-output`, a controller-saved full report)

Full suite still required for the PR to claim a complete pack:

| Probe | Focus for grok |
| --- | --- |
| P3 | Bogus model error text vs documented exit-1; record if exit 0 still happens |
| P4 | Confirm stdin not consumed (docs) |
| P5 | Flagless read |
| P6 | Flagless write + shell; then canonical `--always-approve` (+ optional workspace sandbox) |
| P7 | Confirm documented profiles: `workspace` write bound; `read-only` blocks project writes; outside-cwd behavior |
| P8 | `git commit` under workspace sandbox — controller-commits rationale |
| P9 | Effort: valid level + invalid (silent-ignore vs error) |
| P10 | Document-shaped task + report-file path; `report-transport` |
| P11 | Footguns: `-s` vs `-r`; `--permission-mode acceptEdits` non-effect; json `.sessionId` capture |
| P12 | Inventory from `grok models` |
| P13 | Reviewer known-defect fixture if review lane is claimed |

Also probe resume assembly (docs-backed; still run once live):

- `grok -p "…" --output-format json` → capture `.sessionId`
- Resume: `grok --resume <id> -p "<continuation>" --always-approve`
- Fork: insert `--fork-session`; new id
- Resume with **mismatched** `--sandbox` → expect refuse (user-guide 18)

Append results to `providers/grok/verification-log.md`. If any probe is blocked,
record **Incomplete** honestly (agy pattern) rather than inventing Confirmed.

## Surface updates (same PR)

| Surface | Change |
| --- | --- |
| `README.md` | CLI list includes grok; version **1.6.0**; PATH install note |
| `.claude-plugin/plugin.json` | version 1.6.0; keyword `grok` |
| `.codex-plugin/plugin.json` | version 1.6.0; keyword if present |
| `skills/sdd/SKILL.md` description | `codex/opencode/agy/grok` |
| `skills/delegate/SKILL.md` description | same |
| `skills/*/agents/openai.yaml` | short_description provider list |
| `CLAUDE.md` | one-line provider list |

**Not in scope:**

- Edits to `core/roles.md`, `core/playbook.md`, or other doctrine (unless a probe
  reveals a *shared* invariant that is currently false for all packs — unlikely).
- Hardcoding `grok` in skill routing logic.
- Setting grok as `default_provider` in any shipped config.
- Grok controller harness adapter.
- Mechanical `--deny` rules for `git commit` until P8/P11 prove rule grammar.
- Expanding skill resume-assembly docs beyond a one-line pack note (unless
  implementation discovers a real cross-pack bug — then fix in a follow-up).

## Implementation outline (for writing-plans)

1. Branch already: `feature/grok-provider` off `main`.
2. Author `providers/grok/` three files from this design + **user-guide-backed**
   template (Status=`experimental` until live P2/P6/implement evidence).
3. `python3 scripts/validate-packs --root .` green.
4. Run live P1–P13 + resume/fork; append verification-log; promote Status /
   `verified-version` / any field that live evidence revises (not re-litigate
   documented flag existence).
5. Surface version + naming updates.
6. `./scripts/codex-smoke` + `uv run --with pytest pytest tests/ -q`.
7. Commit; open PR to `main`.

## Success criteria

- `validate-packs` accepts `providers/grok/`.
- `via grok` is a valid provider directive when `grok` is on PATH (detection by `cli`).
- Canonical template matches **user-guide headless automation** (`-p`, `-m`, `--cwd`,
  `--always-approve`, lane sandbox, output format) and is copy-pasteable from pack.md.
- Verification log has a 2026-07-23/24 entry with real probe evidence.
- Version triad is 1.6.0 and in sync.
- No purity violations (no model ids / invocation strings in `core/` or skills body
  beyond existing provider-name lists in descriptions).
- Model Status cells are single valid enums (never transition strings).
- Pack prose cites `~/.grok/docs/user-guide/` for re-verify on CLI bumps.

## Design-review disposition (GLM 5.2, 2026-07-23) + rev 3 docs correction

| Finding | Disposition |
| --- | --- |
| Important: Status `experimental → verified` invalid enum | **Fixed** — cells are single `experimental`; promote to `verified` only after evidence |
| Important: `--cwd` / `--output-format` unverified in template | **Rev 3 supersedes** — both are documented first-class headless flags (14-headless-mode); restored to canonical template. GLM was right to reject *unverified invention*; the fix is **cite the user guide**, not demote the flags. |
| Important: `resume-argv` embeds `-p` (≠ agy) | **Fixed** — `["grok","--resume","{session_id}"]`; skill appends `-p` |
| Minor: version rationale vs CLAUDE.md patch rule | **Fixed** — new provider ⇒ minor; in-pack facts ⇒ patch |
| Minor: gotcha #7 readiness mislabel | **Fixed** — dispatch-time channel failure |
| (self) Sandbox treated as unknown | **Rev 3** — `sandbox: enforced` with documented profiles |
| (self) Session id via list only | **Rev 3** — prefer json `.sessionId` (`session-source: exec-output`) |

## Open items resolved in design

| Question | Resolution |
| --- | --- |
| Scope | Full pack + live verify |
| Branch seed | `main` |
| Permission posture | `--always-approve` (not acceptEdits+always-approve) |
| Quota | SuperGrok subscribed; full suite proceeds |
| Models | All tiers → `grok-4.5` until inventory grows |
| Controller harness | Out of scope |
| Resume argv shape | Match agy — no prompt flag in manifest; id from json `.sessionId` |
| Template completeness | User-guide headless pattern (`--cwd`, `--always-approve`/`--yolo`, sandbox per lane) |
| Docs authority | `~/.grok/docs/user-guide/` + `~/.grok/README.md` |
