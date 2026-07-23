# Grok CLI Provider Pack — sdd-dispatch v1.6.0

Date: 2026-07-23  
Status: draft (design approved via session; awaiting user review of this file)  
Target version: **1.6.0**  
Branch: `feature/grok-provider` (seeded from `main` / v1.5.0)

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
- Pack-fact change ⇒ plugin **minor** bump (1.5.0 → 1.6.0) with
  `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and README
  `**Version:**` kept in sync.
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
| `--prompt-file` | Works for single-turn headless |
| `--reasoning-effort` | Accepted in smoke (full P9 still required for invalid/silent-ignore) |

**Permission ceiling decision (revised after evidence):**

Canonical implement flags are **`--always-approve` alone**, not
`acceptEdits + always-approve`. The latter was the initial design preference; live
shell probes refuted it. Document `bypassPermissions` as the fallback if
`--always-approve` regresses. Never treat exit 0 as proof of work — controller
diff-after / report-exists remains the gate (same doctrine as agy).

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
resume-argv: ["grok", "--resume", "{session_id}", "-p"]
fork-flag: "--fork-session"
session-source: session-list
session-list-argv: ["grok", "sessions", "list"]
stall-signal: log-age
report-transport: report-file   # provisional until P10; flip to captured-output if diversion
sandbox: none                   # provisional until P7; flip to enforced if workspace/read-only is real
readiness-argv: ["grok", "models"]
---
```

Notes:

- `resume-argv` ends with `-p` so the controller can append the continuation prompt as
  the next argv element (same pattern as other packs that take a prompt flag). If live
  resume shows a different shape is required, record it and adjust in the same PR.
- `fork-flag: "--fork-session"` matches CLI help; confirm with a resume+fork smoke.
- `stall-signal: log-age` — grok streams/prints progressively in smokes; re-evaluate
  only if verify shows print-mode buffering like agy.
- No new manifest fields are required for v1.6.0 unless a skill must branch and pack
  prose is insufficient.

### Canonical dispatch template

```bash
grok -p "<PROMPT>" \
  -m <model> \
  --cwd <repo> \
  --always-approve \
  --output-format plain
```

Optional insurance (not mandatory): `< /dev/null` at the end.

Review-lane intent today: same flags (sandbox not yet claimed as enforced). If P7
proves `--sandbox read-only` blocks writes while allowing reads, document a review
template variant and set `sandbox: enforced` only if the boundary is real and
documented.

Resume (after kill / fix loop):

```bash
grok --resume <session_id> -p "<continuation prompt>" --always-approve
# branch a new session id when needed:
grok --resume <session_id> --fork-session -p "<continuation>" --always-approve
```

Session id source: newest matching row from `grok sessions list` immediately after
dispatch (or id printed in any exec metadata if P1 finds a cleaner source).

### Gotchas to document in pack.md (seed list; verify may refine)

1. **Exit codes are not work evidence** — bogus model and permission-starved shell
   can still exit 0. Gate on stdout content + on-disk effects.
2. **`acceptEdits` is not a safe implement ceiling** — pairs poorly with shell tools
   (silent no-op). Use `--always-approve`.
3. **Prompt flag is `-p` / `--single`** — single user turn with multi-tool agency, not
   "one model reply without tools". Also: `--prompt-file` for large briefs.
4. **No mandatory stdin close** (unlike codex/agy) — still harmless to redirect.
5. **Sandbox unknown profile fails closed** — refuse to start rather than run
   unsandboxed.
6. **Model inventory is thin** — only `grok-4.5` as of 0.2.111; all tiers map to it.
7. **Free-tier quota** can hard-fail with a SuperGrok upsell message; treat as
   readiness/auth class failure, not task BLOCKED.

### models.md

| Tier | Lane | Priority | Model id | Status | Pricing | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| cheapest | any | 1 | grok-4.5 | experimental → verified | seat / SuperGrok | sole inventory row; transcription/explore |
| standard | any | 1 | grok-4.5 | experimental → verified | seat / SuperGrok | sole inventory row; default implement/review |
| most-capable | any | 1 | grok-4.5 | experimental → verified | seat / SuperGrok | sole inventory row; final review until inventory grows |

Status rules:

- Start as `experimental` if only smokes exist when the files are first committed.
- Promote to `verified` in the same PR once P2/P12 and an implement-shaped dispatch
  leave on-disk evidence (file write + shell if the task needs it, or report file).
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
| P3 | Bogus model error text; **exit 0 gotcha** |
| P4 | Confirm stdin protection optional |
| P5 | Flagless read |
| P6 | Flagless write + shell; then canonical flags |
| P7 | `--sandbox workspace` / `read-only` / outside-workspace writes |
| P8 | `git commit` inside sandbox / without — controller-commits rationale |
| P9 | Reasoning effort valid + invalid |
| P10 | Document-shaped task + report-file path; set `report-transport` |
| P11 | `-p` ordering, short flags, prompt-file |
| P12 | Only `grok-4.5` (or newly listed models) |
| P13 | Reviewer known-defect fixture if review lane is claimed |

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

## Implementation outline (for writing-plans)

1. Branch already: `feature/grok-provider` off `main`.
2. Author `providers/grok/` three files from this design + smoke evidence.
3. `python3 scripts/validate-packs --root .` green.
4. Run live P1–P13; append verification-log; update pack.md/models.md fields that
   probes settle (`report-transport`, `sandbox`, model Status, gotchas).
5. Surface version + naming updates.
6. `./scripts/codex-smoke` + `uv run --with pytest pytest tests/ -q`.
7. Commit; open PR to `main`.

## Success criteria

- `validate-packs` accepts `providers/grok/`.
- `via grok` is a valid provider directive when `grok` is on PATH (detection by `cli`).
- Canonical template is copy-pasteable from pack.md and matches verified flags.
- Verification log has a 2026-07-23 entry with real probe evidence.
- Version triad is 1.6.0 and in sync.
- No purity violations (no model ids / invocation strings in `core/` or skills body
  beyond existing provider-name lists in descriptions).

## Open items resolved in design

| Question | Resolution |
| --- | --- |
| Scope | Full pack + live verify |
| Branch seed | `main` |
| Permission posture | `--always-approve` (not acceptEdits+always-approve) |
| Quota | SuperGrok subscribed; full suite proceeds |
| Models | All tiers → `grok-4.5` until inventory grows |
| Controller harness | Out of scope |
