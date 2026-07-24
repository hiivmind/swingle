# SDD Dispatch Verification Log — claude

Append-only. Never rewrite prior entries — a later contradiction dates a behavior change.
Format per [verification-protocol.md](../../core/verification-protocol.md).

---

## 2026-07-24 — claude 2.1.218 (trigger: new provider pack — initial verification)

Probed with `ANTHROPIC_API_KEY` set (nested `claude` authed via key; stderr banner noted).
Scratchpad dispatches, artifacts removed after. Authoring controller was itself Claude Code,
so the write/shell path (P6) and git-commit (P8) — which need `--dangerously-skip-permissions`
— were **blocked by the parent auto-mode classifier** and are stamped pending operator
confirmation (run via a shell the classifier does not gate).

| Probe | Assertion under test | Verdict | Evidence |
| --- | --- | --- | --- |
| P1 | Version + surface | New | `claude --version` = 2.1.218; headless surface = `-p`/`--print`, `--model`, `--session-id`, `--resume`, `--fork-session`, `--permission-mode {acceptEdits,auto,bypassPermissions,manual,dontAsk,plan}`, `--effort`, `--output-format {text,json,stream-json}`, `--add-dir`. No `--sandbox` flag. |
| P2 | `claude -p --model <alias> "<prompt>"` dispatches | Confirmed | PONG, exit 0; clean stdout, banner on **stderr** only |
| P2 (json) | `--output-format json` shape | New | returns `{session_id:<uuid>, result:"PONG", is_error:false, num_turns:1}`; `modelUsage` keys carry the resolved snapshot id |
| P3 | Bogus model error path | New | `--model this-model-does-not-exist-99` → exit **1**, clean local error "It may not exist or you may not have access. Run --model to pick" — fails fast, not remote-only |
| P4 | stdin protection mandatory | Not run | every probe ran without a stdin redirect and none hung; explicit unclosed-pipe backstop deferred |
| P5 | Read, no flags | Confirmed | returned `XYZZY42` from readtest.txt, exit 0 — reads run headless ungated |
| P6 (default/acceptEdits/auto/dontAsk) | Write/shell **silently no-op** without bypass | Confirmed | across all four modes: agent narrates "need permission", **exit 0, file MISSING** on disk — the silent-write footgun; controller on-disk gate mandatory |
| P6 (bypass write/shell) | `--dangerously-skip-permissions` enables headless write + shell | **Pending** | classifier-blocked from the authoring Claude Code session; operator to confirm on disk |
| P7 | Sandbox escape | N/A | `sandbox: none` — no built-in OS sandbox; `--dangerously-skip-permissions` docs point to external containers |
| P8 | Git commit inside workspace | **Pending** | write-dependent; bundled with the P6 bypass confirmation |
| P9 | `--effort` knob | New | valid `low` → exit 0; invalid `bogus` → `Warning: Unknown --effort value 'bogus' — ignoring it and using the default effort. Valid values: low, medium, high, xhigh, max` then proceeds (exit 0) — locally validated, warned not silently ignored |
| P10 | Output contract | New | clean final message on stdout; banner on stderr; `--output-format json` carries full transcript metadata. `report-transport: report-file` (agent writes report with Write tool, needs bypass) |
| P11 | Argument-parsing footguns | New | prompt is a **trailing positional**; `-p "<prompt>" --model haiku` (flags after prompt) parsed correctly — no `-p`-eats-next-arg (agy) and no `-p`=password (opencode). `-p`/`--print` REQUIRED for headless |
| Session | Controller-assigned id: create-or-resume | New | `--session-id <uuid>` (must be valid UUID) created; `--resume <uuid>` recalled `4242` — `session-source: conversation-id`, no recovery step |
| Session | Read-only lane via plan mode | New | `--permission-mode plan` refused a dispatched workspace write (nothing on disk); wrote a planning doc under `~/.claude/plans/` instead — enforced read-only, but blocks the review-file write, so a plan-mode reviewer returns a captured verdict |
| P12 | Tier models dispatch | Confirmed | `haiku`→claude-haiku-4-5, `sonnet`→claude-sonnet-5, `opus`→claude-opus-4-8 (machine `ANTHROPIC_DEFAULT_OPUS_MODEL` observed repointing opus→claude-opus-4-7[1m]) → all PONG, exit 0 |
| P13 | Reviewer known-defect benchmark | Not run | required before trusting any claude model for the review lane in anger; review rows stamped `verified` for dispatch, not review quality |

**verified-version stamped 2.1.218** on the live dispatch/read/session/model-validation
evidence above. The implement lane's headless write capability rests on standard documented
`--dangerously-skip-permissions` behavior; the P6-bypass/P8 rows convert from Pending to
Confirmed once the operator runs them outside the classifier.
