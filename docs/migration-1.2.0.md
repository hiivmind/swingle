# v1.2.0 reference migration manifest

Each row is one primary destination. Repeated source headings deliberately identify
separable material from that source section; `(mirror)` identifies a non-primary copy.
The v1.1 archive is a preservation artifact, not a migration destination.

| Source (file:heading) | Destination |
| --- | --- |
| references/dispatch-reference.md:# SDD Dispatch Reference — codex / opencode / agy (document identity and versioning note) | core/safety-doctrine.md |
| references/dispatch-reference.md:## Cross-CLI comparison (the one-glance table) (Safety doctrine rows) | core/safety-doctrine.md |
| references/dispatch-reference.md:## Cross-CLI comparison (the one-glance table) (codex column) | providers/codex/pack.md |
| references/dispatch-reference.md:## Cross-CLI comparison (the one-glance table) (opencode column) | providers/opencode/pack.md |
| references/dispatch-reference.md:## Cross-CLI comparison (the one-glance table) (agy column) | providers/agy/pack.md |
| references/dispatch-reference.md:## Background dispatch & liveness protocol (abstract and mandatory doctrine) | core/liveness.md |
| references/dispatch-reference.md:### Rule 1 — Observable launch, stall-based judgment, backstop cap (shared rule) | core/liveness.md |
| references/dispatch-reference.md:# opencode: same wrapper. agy: --print-timeout <backstop> serves the same role. | providers/agy/pack.md |
| references/dispatch-reference.md:### Resume — a kill is a checkpoint, not a restart (codex resume row) | providers/codex/pack.md |
| references/dispatch-reference.md:### Resume — a kill is a checkpoint, not a restart (opencode resume row) | providers/opencode/pack.md |
| references/dispatch-reference.md:### Resume — a kill is a checkpoint, not a restart (agy resume row) | providers/agy/pack.md |
| references/dispatch-reference.md:### Rule 2 — Evidence-first liveness check | core/liveness.md |
| references/dispatch-reference.md:# bracket the first letter: a plain pattern matches YOUR OWN check command (the shell's | core/liveness.md |
| references/dispatch-reference.md:# command string contains it) and long-lived `codex app-server` daemons — both false alives | core/liveness.md |
| references/dispatch-reference.md:### Operating rules | core/liveness.md |
| references/dispatch-reference.md:## codex (verified v0.144.3, 2026-07-22) | providers/codex/pack.md |
| references/dispatch-reference.md:### Dispatch (under codex) | providers/codex/pack.md |
| references/dispatch-reference.md:### Verified behavior (under codex) | providers/codex/pack.md |
| references/dispatch-reference.md:## opencode (verified v1.17.18, 2026-07-22) | providers/opencode/pack.md |
| references/dispatch-reference.md:### Dispatch (under opencode) | providers/opencode/pack.md |
| references/dispatch-reference.md:# prompt is POSITIONAL — `-p` is basic-auth password, not prompt | providers/opencode/pack.md |
| references/dispatch-reference.md:### Verified behavior (under opencode) | providers/opencode/pack.md |
| references/dispatch-reference.md:## agy — Antigravity CLI (verified v1.1.4, 2026-07-22) | providers/agy/pack.md |
| references/dispatch-reference.md:### Dispatch (under agy) | providers/agy/pack.md |
| references/dispatch-reference.md:# -p "<PROMPT>" must be the LAST argument | providers/agy/pack.md |
| references/dispatch-reference.md:### Verified behavior (under agy) | providers/agy/pack.md |
| references/dispatch-reference.md:## Change history | core/verification-log.md (pre-split change history entry) |
| references/model-catalog.md:# SDD Model Catalog & Tiering (document identity and policy preamble) | core/roles.md |
| references/model-catalog.md:## Role → tier → model (policy table, synced 2026-07-22) | core/roles.md (columns reduced) |
| references/model-catalog.md:## Provider inventories (codex inventory introduction) | providers/codex/models.md |
| references/model-catalog.md:### codex (ChatGPT account) — verified dispatching 2026-07-22 | providers/codex/models.md |
| references/model-catalog.md:### agy / Antigravity (v1.1.4) — `agy models`, 2026-07-22 | providers/agy/models.md |
| references/model-catalog.md:### opencode / Zen (v1.17.18) — `opencode models`, 2026-07-22 | providers/opencode/models.md |
| references/model-catalog.md:## Watch list (unevaluated arrivals) (agy arrivals) | providers/agy/models.md (documentary section) |
| references/model-catalog.md:## Watch list (unevaluated arrivals) (opencode arrivals) | providers/opencode/models.md (documentary section) |
| references/model-catalog.md:## Watch list (unevaluated arrivals) (Google restricted item) | providers/agy/models.md (documentary section) |
| references/model-catalog.md:## Watch list (unevaluated arrivals) (Google restricted item) | providers/opencode/models.md (mirror) History section |
| references/model-catalog.md:## Release history | core/verification-log.md (release history entry) |
| references/model-catalog.md:## Release history (Google 2026-07-21 item) | providers/agy/models.md (mirror) History section |
| references/model-catalog.md:## Release history (Google 2026-07-21 item) | providers/opencode/models.md (mirror) History section |
| references/sdd-external-dispatch.md:# Mapping superpowers:subagent-driven-development onto External CLIs | core/playbook.md |
| references/sdd-external-dispatch.md:## How the skill operates (compressed) | core/playbook.md |
| references/sdd-external-dispatch.md:## Role → dispatch mapping | core/playbook.md |
| references/sdd-external-dispatch.md:## Dispatch flavours & economics — say which one you mean | core/playbook.md |
| references/sdd-external-dispatch.md:## Token-efficiency playbook | core/playbook.md |
| references/sdd-external-dispatch.md:### What a task costs the controller under this playbook | core/playbook.md |
| references/sdd-external-dispatch.md:## Divergences from the stock skill (deliberate) | core/playbook.md |
| references/verification-log.md:# SDD Dispatch Verification Log (document identity and append-only preamble) | core/verification-log.md |
| references/verification-log.md:## 2026-07-22 — agy 1.1.4 (trigger: assertion review; prior notes from ~1.1.1) | providers/agy/verification-log.md |
| references/verification-log.md:## 2026-07-22 — opencode 1.17.18 (trigger: assertion review) | providers/opencode/verification-log.md |
| references/verification-log.md:## 2026-07-22 — codex 0.144.3 (trigger: assertion review) (provider findings) | providers/codex/verification-log.md |
| references/verification-log.md:## 2026-07-22 — codex 0.144.3 (trigger: assertion review) (Cross-CLI synthesis paragraph) | core/verification-log.md |
| references/verification-log.md:## 2026-07-22 — incident notes from first live /sdd run (smoke test) | core/verification-log.md |
| references/verification-log.md:## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (opencode findings 1 and 5) | providers/opencode/verification-log.md |
| references/verification-log.md:## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (nemotron addendum context) | providers/opencode/verification-log.md |
| references/verification-log.md:## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (harness/controller findings 2–4) | core/verification-log.md |
| references/verification-log.md:## 2026-07-22 — smoke run 2 (opencode all-lanes), cut short by user at Task 3 (cost note and What worked: stall-watcher bullet) | core/verification-log.md |
| references/verification-log.md:## 2026-07-22 — smoke run 2 (What worked: NEEDS_CONTEXT-resume and reviewer-quality bullets — name opencode models, excluded from core by purity) | providers/opencode/verification-log.md |
| references/verification-log.md:## 2026-07-22 — model evaluation: `opencode/nemotron-3-ultra-free` | providers/opencode/verification-log.md |
| references/verification-protocol.md:# SDD Dispatch Verification Protocol (document identity and introduction) | core/verification-protocol.md |
| references/verification-protocol.md:## Ground rules | core/verification-protocol.md |
| references/verification-protocol.md:## Probe suite | core/verification-protocol.md |
| references/verification-protocol.md:### P1 — Version & surface | core/verification-protocol.md |
| references/verification-protocol.md:### P2 — Trivial dispatch + exit code (success path) | core/verification-protocol.md |
| references/verification-protocol.md:### P3 — Bogus model (error path + validation) | core/verification-protocol.md |
| references/verification-protocol.md:### P4 — Stdin hang | core/verification-protocol.md |
| references/verification-protocol.md:### P5 — Read permission (no flags) | core/verification-protocol.md |
| references/verification-protocol.md:### P6 — Write permission (no flags, then with flags) | core/verification-protocol.md |
| references/verification-protocol.md:### P7 — Sandbox escape (only if a sandbox is claimed) | core/verification-protocol.md |
| references/verification-protocol.md:### P8 — Git commit inside sandbox | core/verification-protocol.md |
| references/verification-protocol.md:### P9 — Reasoning-effort knob | core/verification-protocol.md |
| references/verification-protocol.md:### P10 — Output contract / artifact diversion | core/verification-protocol.md |
| references/verification-protocol.md:### P11 — Argument-parsing footguns | core/verification-protocol.md |
| references/verification-protocol.md:### P12 — New-model dispatch check | core/verification-protocol.md |
| references/verification-protocol.md:## Recording | core/verification-protocol.md |
| references/verification-protocol.md:## YYYY-MM-DD — <cli> <version> (trigger: <version bump \| model release \| anomaly \| quarterly>) | core/verification-protocol.md |
| references/verification-protocol.md:## Cost note | core/verification-protocol.md |
